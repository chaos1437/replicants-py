import logging
logger = logging.getLogger(__name__)

import json
import os
import configargparse
from world import World, WorldMap
from replicant import Bot, Genome
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
            cell_energy_color = pygame.Color(255 - cell._energy, 255, 255 - cell._energy)
            pygame.draw.rect(screen, cell_energy_color, (x * cell_size, y * cell_size, cell_size, cell_size))
            pygame.draw.rect(screen, color, (x * cell_size, y * cell_size, cell_size, cell_size), int(cell_size//7.5))
            if cell.contains:
                pygame.draw.circle(screen, color, (x * cell_size + cell_size // 2, y * cell_size + cell_size // 2), cell_size//7.5)

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
                for _ in range(args.spawn_rate*100):
                    bot = Bot()
                    if bot.alive:
                        world.spawn(bot)

            for bot in world.bots:
                world.update_vision_for_bot(bot)
            
            for bot in world.bots:
                bot.run()
                world.queue_interaction(bot.get_interaction())

            world.process_interactions()
            world.remove_dead_bots()

            if world.tick % 1000 == 0:
                if top_bots != []:
                    top_bots = sorted(world.bots + top_bots, key=lambda b: b.age, reverse=True)[:20]

                else:
                    top_bots = sorted(world.bots, key=lambda b: b.age, reverse=True)[:20]

                
                text = ""
                for bot in top_bots:
                    text += f"Age:{bot.age} program:{bot.genome.program}\n"

                logger.info("Top 20 bots:\n" + text)
            
            elif world.tick % 250 == 0:
                world.update_cells_energy()

        running, paused, selected_bot = pygame_frontend(world, screen, cell_size, paused, selected_bot)
        if not running:
            logger.info("Exiting event loop")
            break
        
        if args.wait_time > 0:
            time.sleep(args.wait_time)
        

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

def wrapper_bot_run(bot):
    bot.run()
    return bot

if __name__ == "__main__":
    parser = configargparse.ArgParser(description="Simulation parameters", default_config_files=["simulation_settings.ini"])
    parser.add('-c', '--config', is_config_file=True, help='Path to the configuration file')
    parser.add('--width', type=int, default=40, help='Width of the world in cells')
    parser.add('--height', type=int, default=40, help='Height of the world in cells')
    parser.add('-cs', '--cell_size', type=int, default=10, help='Size of each cell in pixels')
    parser.add('-wt', '--wait_time', type=float, default=0, help='Time in seconds to wait between ticks')
    parser.add('-sr','--spawn_rate', type=int, default=10, help="Minimal %% of cells that should be filled with bots")
    parser.add('-mr', '--mutation_rate', type=float, default=0.01, help='Mutation rate for bot genomes')
    parser.add('-pl', '--program_length', type=int, default=64, help='Length of the bot program(genome)')
    parser.add('-mt', '--max_ticks', type=int, default=512, help='Maximum number of command executions for 1 bot run per world tick')
    parser.add('-log', '--log_level', type=str, default="INFO", choices=["INFO", "DEBUG", "WARNING", "CRITICAL"], help='Log level')
    parser.add("--log_file", type=str, default="", help='Path to the log file')
    parser.add('-s', '--save_file', type=str, default="./default.save", help='File to save and load the world state')
    args = parser.parse_args()


    if args.log_file != "":
        logging.basicConfig(level=args.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', filemode='a',filename=args.log_file, datefmt='%d/%m/%y %H:%M')
    
    else:
        logging.basicConfig(level=args.log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%d/%m/%y %H:%M')

    import pygame
    
    logger.info("Starting simulation")
    

    if os.path.exists(args.save_file):
        world = load_world_state(args.save_file)
        if world.bot_genome_data != None:
                Genome.mutation_rate = world.bot_genome_data["mutation_rate"]
                Genome.program_length = world.bot_genome_data["program_length"]
                Genome.max_ticks = world.bot_genome_data["max_ticks"]
        
        else:
            Genome.mutation_rate = args.mutation_rate
            Genome.program_length = args.program_length
            Genome.max_ticks = args.max_ticks
            world.bot_genome_data = {"mutation_rate": args.mutation_rate, "program_length": args.program_length, "max_ticks": args.max_ticks}

    else:
        world = World(WorldMap(args.width, args.height))
        Genome.mutation_rate = args.mutation_rate
        Genome.program_length = args.program_length
        Genome.max_ticks = args.max_ticks
        world.bot_genome_data = {"mutation_rate": args.mutation_rate, "program_length": args.program_length, "max_ticks": args.max_ticks}


    pygame.init()

    cell_size = args.cell_size
    screen_width = world.width * cell_size
    screen_height = world.height * cell_size
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Simulation")
    logger.info(f"Pygame window initialized with size {screen_width}x{screen_height}")
    logger.info(f"World genome parameters:{world.bot_genome_data}")

    event_loop(world, screen, cell_size, args)

    if args.save_file:
        save_world_state(world, args.save_file)

    pygame.quit()
    logger.info("Simulation ended")
