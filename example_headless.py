"""Headless симуляция - точка входа без UI

Это основной файл для запуска симуляции как микросервиса.
Симуляция работает без графического интерфейса и может
отдавать состояние через API в будущем.
"""
import logging
from pathlib import Path

from config.settings import load_config
from core.world import World
from core.world_map import WorldMap
from services.simulation_service import SimulationService
from persistence.serializer import WorldSerializer

logger = logging.getLogger(__name__)


def setup_logging(config):
    """Настройка логирования"""
    if config.log_file:
        logging.basicConfig(
            level=config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filemode='a',
            filename=config.log_file,
            datefmt='%d/%m/%y %H:%M'
        )
    else:
        logging.basicConfig(
            level=config.log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%d/%m/%y %H:%M'
        )


def create_world(config):
    """Создать новый мир"""
    world_map = WorldMap(config.world.width, config.world.height)
    world = World(world_map)
    world.genome_config = config.genome
    return world


def main():
    """Главная функция"""
    # Загрузка конфигурации
    config, args = load_config()
    
    # Настройка логирования
    setup_logging(config)
    
    logger.info("=" * 80)
    logger.info("HEADLESS SIMULATION STARTING")
    logger.info(f"Configuration: {config}")
    logger.info("=" * 80)
    
    # Создание или загрузка мира
    if config.save_file.exists():
        logger.info(f"Loading world from {config.save_file}")
        world = WorldSerializer.load(config.save_file, config.genome)
    else:
        logger.info("Creating new world")
        world = create_world(config)
    
    # Запуск симуляции
    service = SimulationService(world, config)
    
    try:
        service.run(max_ticks=config.max_ticks)
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    finally:
        # Сохранение состояния
        logger.info(f"Saving world to {config.save_file}")
        WorldSerializer.save(world, config.save_file)
        logger.info("Simulation ended")


if __name__ == "__main__":
    main()
