import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

import json
import os
import argparse
from world import World, WorldMap
from replicant import Bot
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
            
            
            
            elif event.key == pygame.K_s:
                import pdb; pdb.set_trace()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            cell_x, cell_y = x // cell_size, world.height - (y // cell_size) - 1
            cell = world.map.get_cell(cell_x, cell_y)
            if cell and cell.contains:
                selected_bot = cell.contains
                logger.info(f"Selected bot {selected_bot.id} at ({cell_x}, {cell_y})")

    screen.fill((255, 255, 255))

    for y in range(0, world.height):
        for x in range(0, world.width):
            cell = world.map.get_cell(x, world.height - y - 1)
            color = (0, 0, 0) if cell.contains else (200, 200, 200)
            cell_energy_color = (0, 255, cell.energy if 255 > cell.energy > 0 else 0)
            pygame.draw.rect(screen, cell_energy_color, (x * cell_size, y * cell_size, cell_size, cell_size))
            pygame.draw.rect(screen, color, (x * cell_size, y * cell_size, cell_size, cell_size), 1)

    if selected_bot:
        font = pygame.font.Font(None, 14)
        info_text = [
            f"Bot ID: {selected_bot.id}",
            f"Energy: {selected_bot.energy}",
            f"Age: {selected_bot.age}",
            f"Position: ({selected_bot.x}, {selected_bot.y})",
            f"Program: {selected_bot.genome.program}",
            f"Registers: {selected_bot.genome.registers}"
        ]
        for i, line in enumerate(info_text):
            text_surface = font.render(line, True, (0, 0, 0))
            screen.blit(text_surface, (10, 10 + i * 15))

    pygame.display.flip()
    return True, paused, selected_bot

def event_loop(world, screen, cell_size, args, top_bots=[]):
    paused = False
    selected_bot = None

    while True:
        if not paused:
            if len(world.bots) < round(world.width*world.height / 100 * args.spawn_rate):
                for _ in range(args.spawn_rate):
                    bot = Bot(world)
                    if bot.alive:
                        world.spawn(bot)
                        logger.debug(f"Spawned new bot at tick {world.tick}")

            for bot in world.bots:
                bot.update_vision()
            
            for bot in world.bots:
                bot.run()

            world.process_interactions()
            world.remove_dead_bots()

            if world.tick % 1000 == 0:
                if top_bots != []:
                    top_bots = sorted(world.bots + top_bots, key=lambda b: b.age, reverse=True)[:20]

                else:
                    top_bots = sorted(world.bots, key=lambda b: b.age, reverse=True)[:20]

                logger.info(f"Top 20 bots:\n { "\n".join( [f"Age:{bot.age} program:{bot.genome.program}" for bot in top_bots] )}")
            
            elif world.tick % 500 == 0:
                world.update_cells_energy()

        running, paused, selected_bot = pygame_frontend(world, screen, cell_size, paused, selected_bot)
        if not running:
            logger.info("Exiting event loop")
            break
        
        if args.wait_time > 0:
            time.sleep(wait_time)
    

    return top_bots


def save_world_state(world, filename):
    with open(filename, 'w') as f:
        json.dump(world.to_json(), f)
    logger.info(f"World state saved to {filename}")


def load_world_state(filename):
    with open(filename, 'r') as f:
        json_data = json.load(f)
    world = World.from_json(json_data)
    logger.info(f"World state loaded from {filename}")
    return world

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulation parameters")
    parser.add_argument('--width', type=int, default=40, help='Width of the world in cells')
    parser.add_argument('--height', type=int, default=40, help='Height of the world in cells')
    parser.add_argument('--cell_size', type=int, default=10, help='Size of each cell in pixels')
    parser.add_argument('--wait_time', type=float, default=0, help='Time in seconds to wait between ticks')
    parser.add_argument('--spawn_rate', type=int, default=10, help="Minimal \% of cells that should be filled with bots")
    parser.add_argument('--save_file', type=str, default="./default.save", help='File to save and load the world state')
    args = parser.parse_args()

    import pygame

    logger.info("Starting simulation")
    if args.save_file:
        if os.path.exists(args.save_file):
            world = load_world_state(args.save_file)
        else:
            world = World(WorldMap(args.width, args.height))
    else:
        world = World(WorldMap(args.width, args.height))

    pygame.init()
    cell_size = args.cell_size
    screen_width = world.width * cell_size
    screen_height = world.height * cell_size
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Simulation")
    logger.info(f"Pygame window initialized with size {screen_width}x{screen_height}")

    event_loop(world, screen, cell_size, args)

    if args.save_file:
        save_world_state(world, args.save_file)

    pygame.quit()
    logger.info("Simulation ended")
