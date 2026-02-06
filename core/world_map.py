"""Карта мира и ячейки"""
import logging
import random

logger = logging.getLogger(__name__)


class Cell:
    """Ячейка пространства на карте"""
    
    def __init__(self, x: int, y: int, contains=None, energy: int = 100):
        self.x = x
        self.y = y
        self.contains = contains
        self._energy = energy
    
    def set(self, contains):
        """Установить содержимое ячейки (бота)"""
        self.contains = contains
        if contains is not None:
            contains.x = self.x
            contains.y = self.y
    
    def add_energy(self, amount: int):
        """Добавить энергию к ячейке (с ограничениями 0-255)"""
        if self._energy + amount > 255:
            self._energy = 255
        elif self._energy + amount < 0:
            self._energy = 0
        else:
            self._energy += amount


class WorldMap:
    """Карта мира - двумерная сетка ячеек"""
    
    def __init__(self, width: int, height: int):
        self.width = width
        self.height = height
        self.map = [[Cell(x, y) for x in range(width)] for y in range(height)]
        logger.info(f"WorldMap initialized with width {width} and height {height}")
    
    def get_cell(self, x: int, y: int):
        """Получить ячейку по координатам"""
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x]
        else:
            return False
    
    def _move(self, first_cell: Cell, another_cell: Cell):
        """Обменять содержимое двух ячеек"""
        temp = first_cell.contains
        
        if another_cell.contains is not None:
            another_cell.contains.x = first_cell.x
            another_cell.contains.y = first_cell.y
        
        first_cell.contains = another_cell.contains
        
        if temp is not None:
            temp.x = another_cell.x
            temp.y = another_cell.y
        
        another_cell.contains = temp
    
    def move(self, x: int, y: int, x1: int, y1: int):
        """Переместить содержимое из (x, y) в (x1, y1)"""
        if self.width > x1 >= 0 and self.height > y1 >= 0:
            self._move(self.map[y][x], self.map[y1][x1])
        else:
            logger.debug(f"Attempted to move to ({x1}, {y1}) but it's out of bounds")
    
    def get_free_cell(self):
        """Найти свободную ячейку"""
        # 20 попыток найти случайную свободную ячейку
        for _ in range(20):
            x = random.randint(0, self.width - 1)
            y = random.randint(0, self.height - 1)
            if self.get_cell(x, y).contains is None:
                return self.get_cell(x, y)
        
        # Если не нашли, перебираем все
        for y in range(self.height):
            for x in range(self.width):
                if self.get_cell(x, y).contains is None:
                    return self.get_cell(x, y)
        
        logger.warning("No free cells found")
        return False
