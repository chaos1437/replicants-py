from world import World, WorldMap
from replicant import Bot
from time import sleep
import pygame


def render(world):
    for y in range(world.height):
        for x in range(world.width):
            cell = world.map.get_cell(x, world.height - 1 - y)
            if cell.contains != None:
                print("@", end='')
            else:
                print(' ', end='')
        print()


def pygame_frontend(world):
    global pygame
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit(0)
            return

    screen.fill((255, 255, 255))  # White background

    for y in range(world.height):
        for x in range(world.width):
            cell = world.map.get_cell(x, world.width - y -1)
            if cell.contains is not None:
                pygame.draw.rect(screen, (0, 0, 0), (x * cell_size, y * cell_size, cell_size, cell_size))
            else:
                pygame.draw.rect(screen, (200, 200, 200), (x * cell_size, y * cell_size, cell_size, cell_size), 1)

    pygame.display.flip()



def event_loop(world):
    while True:
        if world.tick < 2:
            bots = [Bot(world) for _ in range(10)]
            for bot in bots:
                if bot.alive:
                    world.bots.append(bot)

        for bot in world.bots:
            bot.update_vision()
            bot.run()
        
        world.process_interactions()
        sleep(0.01)
        pygame_frontend(world)


if __name__ == "__main__":
    world = World(WorldMap(20, 20))

    pygame.init()
    cell_size = 10
    screen_width = world.width * cell_size
    screen_height = world.height * cell_size
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Simulation")

    event_loop(world)