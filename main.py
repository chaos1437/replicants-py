import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from world import World, WorldMap
from replicant import Bot
import pygame
import time

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def pygame_frontend(world, screen, cell_size):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            logger.info("Pygame quit event received")
            return False

    screen.fill((255, 255, 255))

    for y in range(world.height):
        for x in range(world.width):
            cell = world.map.get_cell(x, world.height - y - 1)
            color = (0, 0, 0) if cell.contains else (200, 200, 200)
            pygame.draw.rect(screen, color, (x * cell_size, y * cell_size, cell_size, cell_size), 1)

    pygame.display.flip()
    return True

def event_loop(world, screen, cell_size):
    while True:
        if world.tick < 20:
            for _ in range(10):
                bot = Bot(world)
                if bot.alive:
                    world.spawn(bot)
                    logger.debug(f"Spawned new bot at tick {world.tick}")

        for bot in world.bots.copy():
            bot.update_vision()
            bot.run()
        
        world.process_interactions()
        world.remove_dead_bots()
        
        if not pygame_frontend(world, screen, cell_size):
            logger.info("Exiting event loop")
            break

        time.sleep(0.01)

if __name__ == "__main__":
    logger.info("Starting simulation")
    world = World(WorldMap(20, 20))

    pygame.init()
    cell_size = 10
    screen_width = world.width * cell_size
    screen_height = world.height * cell_size
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Simulation")
    logger.info(f"Pygame window initialized with size {screen_width}x{screen_height}")

    event_loop(world, screen, cell_size)
    pygame.quit()
    logger.info("Simulation ended")
