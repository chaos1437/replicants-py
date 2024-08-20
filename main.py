from world import World, WorldMap
from replicant import Bot
from time import sleep

alive = []

def render(world):
    for y in range(world.height):
        for x in range(world.width):
            cell = world.map.get_cell(x, world.height - 1 - y)
            if cell.contains != None:
                print("@", end='')
            else:
                print(' ', end='')
        print()


def event_loop(world):
    while True:
        for bot in world.bots:
            bot.update_vision()
            bot.run()
        
        world.process_interactions()
        sleep(0.1)
        render(world)

        bots = [Bot(world) for _ in range(10)]
        for bot in bots:
            if bot.alive:
                alive.append(bot)
        
        for bot in alive:
            if not bot.alive:
                alive.remove(bot)

if __name__ == "__main__":
    world = World(WorldMap(20, 20))
    event_loop(world)