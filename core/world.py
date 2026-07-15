"""Мир симуляции"""
import logging
from core.world_map import WorldMap
from core.bot import Bot, Genome

logger = logging.getLogger(__name__)


class World:
    """Мир симуляции - содержит карту и ботов"""
    
    def __init__(self, world_map: WorldMap, tick: int = 0):
        self.width = world_map.width
        self.height = world_map.height
        self.pending_interactions = {}
        self.tick = tick
        self.bots = []
        self.map = world_map
        self.energy_boost = 50
        self.genome_config = None  # Будет установлено извне
        logger.info(f"World initialized with size {self.width}x{self.height}")
    
    def spawn(self, bot: Bot) -> bool:
        """Появление бота в случайной свободной ячейке"""
        free_cell = self.map.get_free_cell()
        if free_cell:
            bot.x, bot.y = free_cell.x, free_cell.y
            cell = self.map.get_cell(bot.x, bot.y)
            cell.set(bot)
            self.map.occupy_cell(cell)
            self.bots.append(bot)
            return True
        logger.warning("Failed to spawn bot: no free cells")
        return False
    
    def queue_interaction(self, interaction):
        """Добавить взаимодействие в очередь"""
        self.pending_interactions.setdefault(interaction.type, []).append(interaction)
    
    def process_interactions(self):
        """Обработать все взаимодействия (будет вызывать handlers)"""
        from interactions.handlers import execute_interaction
        
        for interaction_type in self.pending_interactions:
            for interaction in self.pending_interactions[interaction_type]:
                execute_interaction(self, interaction)
        
        self.pending_interactions.clear()
        self.tick += 1
        
        if self.tick % 100 == 0:
            logger.info(f"Tick {self.tick} completed, interactions processed")
    
    def remove_dead_bots(self):
        """Удалить мертвых ботов"""
        for bot in self.bots[:]:  # копия списка для безопасной итерации
            if bot.energy <= 0 or not bot.alive:
                self.remove_bot(bot)
    
    def remove_bot(self, bot: Bot):
        """Удалить бота из мира"""
        cell = self.map.get_cell(bot.x, bot.y)
        if cell and cell.contains == bot:
            cell.contains = None
            cell.add_energy(max(0, bot.energy) // 2)
            self.map.release_cell(cell)
        if bot in self.bots:
            self.bots.remove(bot)
    
    def bot_energy_draining(self, bot: Bot, cell):
        """Передать энергию от ячейки к боту"""
        energy_transfer = min(cell._energy // 5, 255 - bot.energy)
        bot.energy += energy_transfer
        cell.add_energy(-energy_transfer)
    
    def bot_push_energy(self, bot: Bot, cell, energy: int):
        """Передать энергию от бота к ячейке"""
        energy_transfer = min(energy, 255 - cell._energy)
        bot.energy -= energy_transfer
        cell.add_energy(energy_transfer)
    
    def update_vision_for_bot(self, bot: Bot):
        """Обновить регистры vision для бота"""
        # Направления: left, up, right, down -> регистры 5, 6, 7, 8
        for x, y, register in Genome.SENSOR_REGISTERS:
            cell = self.map.get_cell(bot.x + x, bot.y + y)
            
            if cell:
                if cell.contains:
                    bot.genome.registers[register] = 1  # replicant
                else:
                    bot.genome.registers[register] = 0  # empty
            else:
                bot.genome.registers[register] = 2  # world_border
    
    def update_cells_energy(self):
        """Добавить энергию всем ячейкам"""
        for y in self.map.map:
            for cell in y:
                cell.add_energy(self.energy_boost)
        
        logger.debug(f"Added {self.energy_boost} energy to all cells")
    
    def check_consistency(self):
        """Проверить консистентность: боты в списке = боты на карте"""
        map_bots = set()
        for y in range(self.height):
            for x in range(self.width):
                cell = self.map.get_cell(x, y)
                if cell.contains and isinstance(cell.contains, Bot):
                    map_bots.add(cell.contains)
        
        list_bots = set(self.bots)
        
        if map_bots != list_bots:
            self.bots = list(map_bots)
            logger.warning("Inconsistency detected and corrected in bot list")
