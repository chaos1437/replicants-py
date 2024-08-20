from collections import namedtuple
from replicant import Bot

Interaction = \
    namedtuple('Interaction',
               
               ['bot', 
                'direction', 
                'type', 
                'strength'])


class World:
    def __init__(self, width, height, tick=0):
        self.width = width
        self.height = height
        self.bots = []
        self.pending_interactions = []
        self.tick = tick


    def queue_interaction(self, interaction: Interaction):
        self.pending_interactions.append(interaction)


    def process_interactions(self):
        for interaction in self.pending_interactions:
            self.execute_interaction(interaction)

        self.pending_interactions.clear()
        self.tick += 1


    def execute_interaction(self, interaction: Interaction):

        pass


class WorldMap:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.map = [[Cell(x, y) for x in range(height)] for y in range(width)]
    
    def get_cell(self, x, y):

        try:
            return self.map[y][x]

        except IndexError:
            return False


#Ячейка пространства на карте
class Cell:
    def __init__(self, x, y, contains=None):
        self.x = x
        self.y = y
        self.contains=contains
    
    def __repr__(self):
        if type(self.contains) == Bot:
            return "#"
        
        else:
            return " "

    def move(self, another_cell):
        temp = self.contains
        self.contains = another_cell.contains
        another_cell.contains = temp
    
    def set(self, contains):
        self.contains = contains
