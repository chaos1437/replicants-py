"""Симуляция с консольным рендером"""
import logging
from pathlib import Path

from config.settings import load_config
from core.world import World
from core.world_map import WorldMap
from services.simulation_service import SimulationService
from services.state_provider import StateProvider
from persistence.serializer import WorldSerializer
from renderers.console_renderer import ConsoleRenderer

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
    logger.info("CONSOLE SIMULATION STARTING")
    logger.info(f"Configuration: {config}")
    logger.info("=" * 80)
    
    # Создание или загрузка мира
    if config.save_file.exists():
        logger.info(f"Loading world from {config.save_file}")
        world = WorldSerializer.load(config.save_file, config.genome)
    else:
        logger.info("Creating new world")
        world = create_world(config)
    
    # Создание сервисов
    service = SimulationService(world, config)
    state_provider = StateProvider(world)
    renderer = ConsoleRenderer(state_provider)
    
    # Основной цикл с рендерингом
    try:
        while True:
            service.tick()
            renderer.render()
    except KeyboardInterrupt:
        logger.info("Simulation interrupted by user")
    finally:
        service.stop()
        logger.info(f"Saving world to {config.save_file}")
        WorldSerializer.save(world, config.save_file)
        print("\nСимуляция завершена. Мир сохранен.")


if __name__ == "__main__":
    main()
