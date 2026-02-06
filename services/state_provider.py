"""Провайдер состояния мира для рендеров и API"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StateProvider:
    """Предоставляет состояние мира для рендеров/API
    
    Это интерфейс между симуляцией и UI/API.
    Рендеры вызывают методы get_* для получения данных для отрисовки.
    """
    
    def __init__(self, world):
        self.world = world
    
    def get_world_state(self) -> dict:
        """Полное состояние мира для отрисовки"""
        return {
            'tick': self.world.tick,
            'width': self.world.width,
            'height': self.world.height,
            'bots': self._get_bots_state(),
            'cells': self._get_cells_state()
        }
    
    def _get_bots_state(self) -> list:
        """Состояние всех ботов"""
        bots_state = []
        for bot in self.world.bots:
            bots_state.append({
                'id': bot.id,
                'x': bot.x,
                'y': bot.y,
                'energy': bot.energy,
                'age': bot.age,
                'alive': bot.alive
            })
        return bots_state
    
    def _get_cells_state(self) -> list:
        """Состояние всех ячеек"""
        cells_state = []
        for y in range(self.world.height):
            row = []
            for x in range(self.world.width):
                cell = self.world.map.get_cell(x, y)
                row.append({
                    'x': x,
                    'y': y,
                    'energy': cell._energy,
                    'occupied': cell.contains is not None,
                    'bot_id': cell.contains.id if cell.contains else None
                })
            cells_state.append(row)
        return cells_state
    
    def get_bot_info(self, bot_id: int) -> Optional[dict]:
        """Детальная информация о конкретном боте"""
        bot = self._find_bot_by_id(bot_id)
        if not bot:
            return None
        
        return {
            'id': bot.id,
            'x': bot.x,
            'y': bot.y,
            'energy': bot.energy,
            'age': bot.age,
            'alive': bot.alive,
            'genome': {
                'program': bot.genome.program,
                'registers': bot.genome.registers,
                'mutation_rate': bot.genome.mutation_rate,
                'program_length': bot.genome.program_length
            }
        }
    
    def get_cell_state(self, x: int, y: int) -> Optional[dict]:
        """Состояние конкретной ячейки"""
        cell = self.world.map.get_cell(x, y)
        if not cell:
            return None
        
        return {
            'x': x,
            'y': y,
            'energy': cell._energy,
            'occupied': cell.contains is not None,
            'bot_id': cell.contains.id if cell.contains else None
        }
    
    def get_statistics(self) -> dict:
        """Статистика симуляции"""
        total_bots = len(self.world.bots)
        alive_bots = sum(1 for b in self.world.bots if b.alive)
        average_age = sum(b.age for b in self.world.bots) / total_bots if total_bots > 0 else 0
        average_energy = sum(b.energy for b in self.world.bots) / total_bots if total_bots > 0 else 0
        
        return {
            'tick': self.world.tick,
            'total_bots': total_bots,
            'alive_bots': alive_bots,
            'average_age': average_age,
            'average_energy': average_energy
        }
    
    def _find_bot_by_id(self, bot_id: int):
        """Найти бота по ID"""
        for bot in self.world.bots:
            if bot.id == bot_id:
                return bot
        return None
