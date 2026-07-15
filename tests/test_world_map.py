"""Тесты для world_map.py"""
import pytest
from core.world_map import WorldMap, Cell


class TestCell:
    """Cell unit tests"""

    def test_cell_init(self):
        """default energy=100, contains=None"""
        cell = Cell(5, 5)
        assert cell.x == 5
        assert cell.y == 5
        assert cell.contains is None
        assert cell._energy == 100

    def test_cell_set(self, bot):
        """set(bot) → cell.contains == bot, bot.x/cell.x совпадают"""
        cell = Cell(3, 7)
        cell.set(bot)
        assert cell.contains is bot
        assert bot.x == cell.x == 3
        assert bot.y == cell.y == 7

    def test_cell_add_energy(self):
        """+50 → 150, +200 → 255 (clamp), -300 → 0 (clamp)"""
        cell = Cell(0, 0, energy=100)

        cell.add_energy(50)
        assert cell._energy == 150

        cell.add_energy(200)
        assert cell._energy == 255

        cell.add_energy(-300)
        assert cell._energy == 0


class TestWorldMapGetCell:
    """WorldMap.get_cell tests"""

    def test_get_cell_valid(self, world_map):
        """(0,0) возвращает Cell"""
        cell = world_map.get_cell(0, 0)
        assert isinstance(cell, Cell)
        assert cell.x == 0
        assert cell.y == 0

    def test_get_cell_out_of_bounds(self, world_map):
        """(-1,0) возвращает None, (10,10) возвращает None"""
        assert world_map.get_cell(-1, 0) is None
        assert world_map.get_cell(10, 10) is None

    def test_get_cell_type(self, world_map):
        """возвращает Cell | None"""
        cell = world_map.get_cell(5, 5)
        assert isinstance(cell, (Cell, type(None)))
        assert world_map.get_cell(-1, 0) is None


class TestWorldMapMove:
    """WorldMap.move tests"""

    def test_move(self, world_map, bot):
        """переместить содержимое из (0,0) в (1,1), проверить что ячейки обменялись"""
        cell_a = world_map.get_cell(0, 0)
        cell_b = world_map.get_cell(1, 1)

        cell_a.set(bot)
        assert cell_a.contains is bot
        assert cell_b.contains is None

        world_map.move(0, 0, 1, 1)

        assert cell_a.contains is None, "source should be empty after move"
        assert cell_b.contains is bot, "target should contain the bot after move"
        assert bot.x == 1
        assert bot.y == 1

    def test_move_out_of_bounds(self, world_map, bot):
        """попытка move в (-1,0) — не падает"""
        cell = world_map.get_cell(0, 0)
        cell.set(bot)

        # должно отработать без исключения
        world_map.move(0, 0, -1, 0)

        # содержимое не изменилось
        assert cell.contains is bot


class TestWorldMapFreeCells:
    """WorldMap.free_cells tests"""

    def test_free_cells_init(self, world_map):
        """10×10 → 100 free cells"""
        assert len(world_map.free_cells) == 100

    def test_occupy_cell(self, world_map):
        """occupy → len(free_cells) == 99"""
        cell = world_map.get_cell(0, 0)
        world_map.occupy_cell(cell)
        assert len(world_map.free_cells) == 99

    def test_release_cell(self, world_map):
        """occupy+release → len(free_cells) == 100"""
        cell = world_map.get_cell(0, 0)
        world_map.occupy_cell(cell)
        world_map.release_cell(cell)
        assert len(world_map.free_cells) == 100

    def test_free_cells_after_move(self, world_map, bot):
        """move с ботом из одной ячейки в другую, free_cells консистентны"""
        cell_a = world_map.get_cell(0, 0)
        cell_b = world_map.get_cell(1, 1)

        cell_a.set(bot)
        world_map.occupy_cell(cell_a)
        assert len(world_map.free_cells) == 99

        world_map.move(0, 0, 1, 1)

        # После move: cell_a пуст (free), cell_b занят (не free)
        assert cell_a.contains is None
        assert cell_b.contains is bot
        assert cell_a in world_map.free_cells
        assert cell_b not in world_map.free_cells
        assert len(world_map.free_cells) == 99

    def test_get_free_cell_returns_free(self, world_map):
        """возвращает ячейку с contains == None"""
        cell = world_map.get_free_cell()
        assert cell is not None
        assert cell.contains is None

    def test_get_free_cell_empty(self, world_map):
        """занять все ячейки → return None"""
        for row in world_map.map:
            for cell in row:
                world_map.occupy_cell(cell)
        assert world_map.get_free_cell() is None

    def test_free_cells_consistency_after_move(self, world_map, bot):
        """сложный тест: поместить бота, проверить free_cells, move, проверить снова"""
        cell_a = world_map.get_cell(0, 0)
        cell_b = world_map.get_cell(5, 5)

        # поместить бота в (0,0)
        cell_a.set(bot)
        world_map.occupy_cell(cell_a)

        assert len(world_map.free_cells) == 99
        assert cell_a not in world_map.free_cells
        assert cell_b in world_map.free_cells

        # move: (0,0) -> (5,5)
        world_map.move(0, 0, 5, 5)

        assert cell_a.contains is None
        assert cell_b.contains is bot
        assert cell_a in world_map.free_cells
        assert cell_b not in world_map.free_cells
        assert len(world_map.free_cells) == 99
