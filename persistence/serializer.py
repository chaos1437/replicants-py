"""Сериализация и десериализация мира"""
import json
import logging
from pathlib import Path
from core.world import World
from core.world_map import WorldMap
from core.bot import Bot

logger = logging.getLogger(__name__)


class WorldSerializer:
    """Сохранение и загрузка состояния мира в JSON"""
    
    @staticmethod
    def save(world: World, filename: Path):
        """Сохранить мир в файл"""
        world_state = WorldSerializer._world_to_dict(world)
        
        with open(filename, 'w') as f:
            json.dump(world_state, f, indent=2)
        
        logger.info(f"World state saved to {filename}")
    
    @staticmethod
    def load(filename: Path, genome_config) -> World:
        """Загрузить мир из файла"""
        with open(filename, 'r') as f:
            data = json.load(f)
        
        world = WorldSerializer._dict_to_world(data, genome_config)
        logger.info(f"World state loaded from {filename}")
        return world
    
    @staticmethod
    def _world_to_dict(world: World) -> dict:
        """Преобразовать World в словарь"""
        world_state = {
            "width": world.width,
            "height": world.height,
            "tick": world.tick,
            "energy_boost": world.energy_boost,
            "genome_config": WorldSerializer._genome_config_to_dict(world.genome_config),
            "bots": [],
            "map": WorldSerializer._map_to_dict(world.map)
        }
        
        for bot in world.bots:
            if bot.alive:
                world_state["bots"].append({
                    "id": bot.id,
                    "x": bot.x,
                    "y": bot.y,
                    "energy": bot.energy,
                    "age": bot.age,
                    "genome": {
                        "program": "".join(bot.genome.program),  # В одну строку
                        "registers": list(bot.genome.registers)
                    }
                })
        
        return world_state
    
    @staticmethod
    def _genome_config_to_dict(genome_config) -> dict:
        """Преобразовать GenomeConfig в словарь"""
        if genome_config is None:
            return None
        
        return {
            "mutation_rate": genome_config.mutation_rate,
            "program_length": genome_config.program_length,
            "max_ticks": genome_config.max_ticks
        }
    
    @staticmethod
    def _map_to_dict(world_map: WorldMap) -> list:
        """Преобразовать WorldMap в список"""
        json_map = []
        for y in range(world_map.height):
            row = []
            for x in range(world_map.width):
                cell = world_map.map[y][x]
                cell_data = {
                    "x": cell.x,
                    "y": cell.y,
                    "energy": cell._energy,
                }
                row.append(cell_data)
            json_map.append(row)
        return json_map
    
    @staticmethod
    def _dict_to_world(data: dict, genome_config) -> World:
        """Преобразовать словарь в World"""
        # Создать карту
        world_map = WorldSerializer._dict_to_map(data["map"])
        
        # Создать мир
        world = World(world_map, data["tick"])
        world.energy_boost = data.get("energy_boost", 50)
        world.genome_config = genome_config
        
        # Восстановить ботов
        for bot_data in data["bots"]:
            bot = Bot(config=genome_config, energy=bot_data["energy"])
            bot.id = bot_data["id"]
            bot.x = bot_data["x"]
            bot.y = bot_data["y"]
            # Конвертировать строку обратно в список или использовать как есть если уже список
            program = bot_data["genome"]["program"]
            bot.genome.program = list(program) if isinstance(program, str) else program
            bot.genome.registers = bytearray(bot_data["genome"]["registers"])
            bot.age = bot_data["age"]
            bot.alive = True
            
            world.map.get_cell(bot.x, bot.y).set(bot)
            world.bots.append(bot)
        
        return world
    
    @staticmethod
    def _dict_to_map(map_data: list) -> WorldMap:
        """Преобразовать список в WorldMap"""
        height = len(map_data)
        width = len(map_data[0])
        
        world_map = WorldMap(width, height)
        
        for y, row in enumerate(map_data):
            for x, cell_data in enumerate(row):
                cell = world_map.get_cell(x, y)
                cell._energy = cell_data["energy"]
        
        return world_map
