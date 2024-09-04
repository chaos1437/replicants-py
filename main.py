import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

from world import World, WorldMap
from replicant import Bot
import pygame
import time

def pygame_frontend(world, screen, cell_size, paused, selected_bot):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            logger.info("Pygame quit event received")
            return False, paused, selected_bot
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_p:
                paused = not paused
                logger.info(f"Simulation {'paused' if paused else 'resumed'}")
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            cell_x, cell_y = x // cell_size, world.height - (y // cell_size) - 1
            cell = world.map.get_cell(cell_x, cell_y)
            if cell and cell.contains:
                selected_bot = cell.contains
                logger.info(f"Selected bot {selected_bot.id} at ({cell_x}, {cell_y})")

    screen.fill((255, 255, 255))

    for y in range(world.height):
        for x in range(world.width):
            cell = world.map.get_cell(x, world.height - y - 1)
            color = (0, 0, 0) if cell.contains else (200, 200, 200)
            pygame.draw.rect(screen, color, (x * cell_size, y * cell_size, cell_size, cell_size), 1)

    if selected_bot:
        font = pygame.font.Font(None, 14)
        info_text = [
            f"Bot ID: {selected_bot.id}",
            f"Energy: {selected_bot.energy}",
            f"Position: ({selected_bot.x}, {selected_bot.y})",
            f"Program: {selected_bot.genome.program}",
            f"Registers: {selected_bot.genome.registers}"
        ]
        for i, line in enumerate(info_text):
            text_surface = font.render(line, True, (0, 0, 0))
            screen.blit(text_surface, (10, 10 + i * 15))

    pygame.display.flip()
    return True, paused, selected_bot

def event_loop(world, screen, cell_size):
    paused = False
    selected_bot = None

    while True:
        if not paused:
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

        running, paused, selected_bot = pygame_frontend(world, screen, cell_size, paused, selected_bot)
        if not running:
            logger.info("Exiting event loop")
            break

        time.sleep(0.01)

if __name__ == "__main__":
    logger.info("Starting simulation")
    world = World(WorldMap(40, 40))

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
