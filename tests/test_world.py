"""Tests for World class"""
import pytest
from core.bot import Bot, Genome
from core.world import World
from core.world_map import WorldMap
from config.settings import GenomeConfig
from core.interaction import Interaction


class TestWorldSpawn:
    """World.spawn tests"""

    def test_spawn_success(self, world, bot):
        """Bot is placed in a random free cell"""
        assert world.spawn(bot) is True
        assert bot.x is not None
        assert bot.y is not None
        assert bot in world.bots
        cell = world.map.get_cell(bot.x, bot.y)
        assert cell.contains is bot

    def test_spawn_updates_free_cells(self, world, bot):
        """Free cell count decreases by 1 after spawn"""
        initial_free = len(world.map.free_cells)
        world.spawn(bot)
        assert len(world.map.free_cells) == initial_free - 1

    def test_spawn_all_occupied(self, world, genome_config):
        """spawn returns False when no free cells remain"""
        while world.map.free_cells:
            b = Bot(config=genome_config)
            assert world.spawn(b) is True
        extra_bot = Bot(config=genome_config)
        assert world.spawn(extra_bot) is False
        assert extra_bot not in world.bots


class TestWorldRemoveBot:
    """World.remove_bot tests"""

    def test_remove_bot(self, world, bot):
        """Bot is removed from world; cell released; free_cells restored"""
        world.spawn(bot)
        x, y = bot.x, bot.y
        world.remove_bot(bot)
        assert bot not in world.bots
        cell = world.map.get_cell(x, y)
        assert cell.contains is None
        assert cell in world.map.free_cells

    def test_remove_bot_energy_transfer(self, world, bot):
        """Half of bot's energy (rounded down) is transferred to cell on removal"""
        bot.energy = 100
        world.spawn(bot)
        cell = world.map.get_cell(bot.x, bot.y)
        initial_cell_energy = cell._energy
        world.remove_bot(bot)
        assert cell._energy == initial_cell_energy + 50  # max(0, 100) // 2


class TestWorldInteractions:
    """World.queue_interaction + process_interactions tests"""

    def test_queue_and_process(self, world, bot):
        """Tick increments after processing queued interactions"""
        world.spawn(bot)
        # Set direction registers to zero so bot.direction == -1 (no-op path)
        bot.genome.registers[0:5] = [0, 0, 0, 0, 0]
        interaction = Interaction(bot, direction=-1, type=0, strength=0)
        world.queue_interaction(interaction)
        initial_tick = world.tick
        world.process_interactions()
        assert world.tick == initial_tick + 1

    def test_process_interactions_decreases_energy(self, world, bot):
        """Bot loses exactly 1 energy per interaction (execute_interaction debit)"""
        world.spawn(bot)
        bot.genome.registers[0:5] = [0, 0, 0, 0, 0]
        initial_energy = bot.energy
        interaction = Interaction(bot, direction=-1, type=0, strength=0)
        world.queue_interaction(interaction)
        world.process_interactions()
        assert bot.energy == initial_energy - 1


class TestWorldVision:
    """World.update_vision_for_bot tests"""

    def test_vision_empty_cell(self, world, bot):
        """All four vision registers are 0 when neighbours are empty"""
        # Place bot in the centre so all neighbours are on-map and empty
        cell = world.map.get_cell(5, 5)
        cell.set(bot)
        world.map.occupy_cell(cell)
        world.bots.append(bot)
        bot.x, bot.y = 5, 5

        world.update_vision_for_bot(bot)
        for reg in (5, 6, 7, 8):
            assert bot.genome.registers[reg] == 0, f"Register {reg} should be 0"

    def test_vision_bot_adjacent(self, world, bot, genome_config):
        """Register 5 (left) is 1 when another bot is to the left"""
        # Place bot at (5, 5)
        cell = world.map.get_cell(5, 5)
        cell.set(bot)
        world.map.occupy_cell(cell)
        world.bots.append(bot)
        bot.x, bot.y = 5, 5

        # Place neighbour to the left at (4, 5)
        neighbour = Bot(config=genome_config)
        cell = world.map.get_cell(4, 5)
        cell.set(neighbour)
        world.map.occupy_cell(cell)
        world.bots.append(neighbour)

        world.update_vision_for_bot(bot)
        assert bot.genome.registers[5] == 1  # left → register 5

    def test_vision_border(self, world, bot):
        """Border cells (off-map) produce register value 2"""
        # Place bot at top-left corner (0, 0)
        cell = world.map.get_cell(0, 0)
        cell.set(bot)
        world.map.occupy_cell(cell)
        world.bots.append(bot)
        bot.x, bot.y = 0, 0

        world.update_vision_for_bot(bot)
        # left  (-1, 0) → None → register 5 = 2
        assert bot.genome.registers[5] == 2
        # down  (0, -1) → None → register 8 = 2
        assert bot.genome.registers[8] == 2
        # up    (0,  1) → cell (0, 1) exists → 0
        assert bot.genome.registers[6] == 0
        # right (1,  0) → cell (1, 0) exists → 0
        assert bot.genome.registers[7] == 0


class TestWorldEnergy:
    """World energy update, drain and push tests"""

    def test_update_cells_energy(self, world):
        """Every cell receives energy_boost"""
        initial = world.map.map[0][0]._energy
        world.update_cells_energy()
        for row in world.map.map:
            for cell in row:
                assert cell._energy == initial + world.energy_boost

    def test_bot_energy_draining(self, world, bot):
        """Bot absorbs energy from the cell (min of cell//5, 255-bot.energy)"""
        world.spawn(bot)
        cell = world.map.get_cell(bot.x, bot.y)
        # Set up so transfer is predictable: cell._energy // 5 = 40, bot needs 205
        bot.energy = 50
        cell._energy = 200
        world.bot_energy_draining(bot, cell)
        assert bot.energy == 50 + 40
        assert cell._energy == 200 - 40

    def test_bot_push_energy(self, world, bot):
        """Bot donates energy to the cell (capped at 255 - cell._energy)"""
        world.spawn(bot)
        cell = world.map.get_cell(bot.x, bot.y)
        bot.energy = 255
        cell._energy = 100
        world.bot_push_energy(bot, cell, energy=50)
        assert bot.energy == 255 - 50
        assert cell._energy == 100 + 50
