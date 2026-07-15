"""Tests for services/simulation_service.py"""
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.bot import Bot, Genome
from core.world import World
from core.world_map import WorldMap
from config.settings import GenomeConfig, WorldConfig, SimulationConfig
from services.simulation_service import SimulationService, _execute_chunk_shm


@pytest.fixture
def sim_service(world, genome_config):
    config = SimulationConfig(
        genome=genome_config,
        world=WorldConfig(),
        save_file=Path("/tmp/test_save.json"),
        max_ticks=10,
    )
    return SimulationService(world, config)


class TestSpawnBotsIfNeeded:
    """Tests for SimulationService._spawn_bots_if_needed"""

    def test_spawn_if_needed_below_threshold(self, sim_service):
        """Если ботов меньше min_bots, spawn происходит"""
        sim_service.world.bots = []

        with patch("services.simulation_service.Bot") as MockBot:
            mock_bot = MagicMock()
            mock_bot.alive = True
            mock_bot.energy = 100
            MockBot.return_value = mock_bot

            sim_service._spawn_bots_if_needed()

            assert len(sim_service.world.bots) > 0
            assert MockBot.called

    def test_spawn_if_needed_above_threshold(self, sim_service):
        """Если ботов достаточно, spawn не вызывается"""
        # min_bots = round(100/100*10) = 10; 20 ботов > threshold
        with patch("services.simulation_service.Bot") as MockBot:
            mock_bot = MagicMock()
            mock_bot.alive = True
            MockBot.return_value = mock_bot

            for _ in range(20):
                b = MagicMock()
                b.alive = True
                sim_service.world.bots.append(b)

            original_count = len(sim_service.world.bots)
            sim_service._spawn_bots_if_needed()

            assert len(sim_service.world.bots) == original_count
            assert not MockBot.called


class TestTick:
    """Tests for SimulationService.tick"""

    def test_tick_increments(self, sim_service):
        """Один tick увеличивает world.tick"""
        sim_service.world.bots = []

        with patch("services.simulation_service.Bot") as MockBot:
            mock_bot = MagicMock()
            mock_bot.alive = True
            mock_bot.energy = 100
            mock_bot.x = 0
            mock_bot.y = 0
            mock_bot.age = 0
            mock_bot.genome.registers = [0] * 24
            # get_interaction — используем тип 5 (нет обработчика в HANDLERS)
            mock_interaction = MagicMock()
            mock_interaction.type = 5
            mock_interaction.bot = mock_bot
            mock_bot.get_interaction.return_value = mock_interaction
            MockBot.return_value = mock_bot

            initial_tick = sim_service.world.tick
            sim_service.tick()

            assert sim_service.world.tick == initial_tick + 1

    def test_tick_spawns_bots(self, sim_service):
        """Если ботов нет, tick спавнит их (через spawn_if_needed)"""
        sim_service.world.bots = []

        with patch("services.simulation_service.Bot") as MockBot:
            mock_bot = MagicMock()
            mock_bot.alive = True
            mock_bot.energy = 100
            mock_bot.x = 0
            mock_bot.y = 0
            mock_bot.age = 0
            mock_bot.genome.registers = [0] * 24
            # get_interaction — используем тип 5 (нет обработчика в HANDLERS)
            mock_interaction = MagicMock()
            mock_interaction.type = 5
            mock_interaction.bot = mock_bot
            mock_bot.get_interaction.return_value = mock_interaction
            MockBot.return_value = mock_bot

            sim_service.tick()

            assert len(sim_service.world.bots) > 0
            assert MockBot.called


class TestRunBotsParallel:
    """Tests for SimulationService._run_bots_parallel"""

    def test_run_bots_parallel_no_bots(self, sim_service):
        """Пустой мир, не падает"""
        sim_service.world.bots = []
        # должен отработать без ошибок
        sim_service._run_bots_parallel()

    def test_run_bots_parallel_few_bots(self, sim_service):
        """< 50 ботов, sequential fallback (bot.run вызывается, age растёт)"""
        bots = []
        for _ in range(3):
            bot = Bot(config=sim_service.world.genome_config)
            bot.alive = True
            bot.energy = 100
            # Установить программу и перекомпилировать
            bot.genome.program = ["+", "+", "+"]
            compiled = Genome.compile_program(bot.genome.program)
            assert compiled is not None
            bot.genome.opcodes, bot.genome.jumps = compiled
            bot.genome.registers = [0] * 24
            bot.age = 0
            bots.append(bot)
        # Нужен спавн на карте для vision (или хотя бы x,y)
        for i, bot in enumerate(bots):
            bot.x = i
            bot.y = 0
            sim_service.world.bots = bots

        sim_service._run_bots_parallel()

        for bot in bots:
            assert bot.age == 1
            assert bot.genome.registers[0] == 3


class TestExecuteChunk:
    """Tests for module-level _execute_chunk function"""

    def _make_programs(self, *programs_list):
        return {i: (op, jp) for i, (op, jp) in enumerate(programs_list)}

    def test_execute_chunk_simple(self):
        """Один бот, программа +++, registers[0] == 3, alive=True"""
        from multiprocessing import shared_memory

        opcodes, jumps = Genome.compile_program(["+", "+", "+"])
        shm = shared_memory.SharedMemory(create=True, size=24)
        try:
            # Записать начальное состояние регистров в shm
            shm.buf[0:24] = bytearray(24)
            shm.buf[Genome.REG_ENERGY] = 255

            bot_meta = [
                {"idx": 0, "prog_id": 0, "max_ticks": 512, "x": 5, "y": 5}
            ]
            programs = self._make_programs((opcodes, jumps))
            map_flat = bytes(10 * 10)

            results = _execute_chunk_shm(bot_meta, map_flat, 10, 10, programs, shm.name)

            assert len(results) == 1
            assert results[0]["alive"] is True
            # Прочитать registers из shm
            assert shm.buf[0] == 3
        finally:
            shm.close()
            shm.unlink()

    def test_execute_chunk_dead(self):
        """energy=0 → alive=False"""
        from multiprocessing import shared_memory

        opcodes, jumps = Genome.compile_program(["+", "+", "+"])
        shm = shared_memory.SharedMemory(create=True, size=24)
        try:
            shm.buf[0:24] = bytearray(24)
            shm.buf[Genome.REG_ENERGY] = 0  # energy=0 → dead

            bot_meta = [
                {"idx": 0, "prog_id": 0, "max_ticks": 512, "x": 0, "y": 0}
            ]
            programs = self._make_programs((opcodes, jumps))
            map_flat = bytes(10 * 10)

            results = _execute_chunk_shm(bot_meta, map_flat, 10, 10, programs, shm.name)

            assert len(results) == 1
            assert results[0]["alive"] is False
        finally:
            shm.close()
            shm.unlink()

    def test_execute_chunk_vision(self):
        """Vision: соседняя клетка с ботом → register[5]=1"""
        from multiprocessing import shared_memory

        opcodes, jumps = Genome.compile_program([])
        shm = shared_memory.SharedMemory(create=True, size=24)
        try:
            shm.buf[0:24] = bytearray(24)
            shm.buf[Genome.REG_ENERGY] = 255

            bot_meta = [
                {"idx": 0, "prog_id": 0, "max_ticks": 512, "x": 5, "y": 5}
            ]
            programs = self._make_programs((opcodes, jumps))
            map_flat = bytearray(10 * 10)
            map_flat[5 * 10 + 4] = 1  # клетка слева (4,5) занята

            results = _execute_chunk_shm(bot_meta, bytes(map_flat), 10, 10, programs, shm.name)

            # SENSOR_REGISTERS[0] = (-1, 0, 5) — левая клетка → репликант
            assert shm.buf[5] == 1
        finally:
            shm.close()
            shm.unlink()

    def test_execute_chunk_interaction(self):
        """Interaction: registers[11]=1, strength=50 → interaction в результате"""
        from multiprocessing import shared_memory

        opcodes, jumps = Genome.compile_program([])
        shm = shared_memory.SharedMemory(create=True, size=24)
        try:
            regs = bytearray(24)
            regs[11] = 1
            regs[12] = 50
            regs[0] = 5  # direction
            shm.buf[0:24] = regs
            shm.buf[Genome.REG_ENERGY] = 255

            bot_meta = [
                {"idx": 0, "prog_id": 0, "max_ticks": 512, "x": 0, "y": 0}
            ]
            programs = self._make_programs((opcodes, jumps))
            map_flat = bytes(10 * 10)

            results = _execute_chunk_shm(bot_meta, map_flat, 10, 10, programs, shm.name)

            assert results[0]["interaction"] is not None
            assert results[0]["interaction"]["type"] == 1
            assert results[0]["interaction"]["strength"] == 50
            assert results[0]["interaction"]["direction"] == 0
        finally:
            shm.close()
            shm.unlink()
