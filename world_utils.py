from collections import namedtuple

Interaction = \
    namedtuple('Interaction',
               
               ['bot', 
                'direction', 
                'type', 
                'strength'])


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
    def __init__(self, x, y, contains=None, energy=100):
        self.x = x
        self.y = y
        self.contains=contains
        self.energy = energy
    

    def move(self, another_cell):
        temp = self.contains

        if another_cell.contains != None:
            another_cell.x = self.x
            another_cell.y = self.y

        self.contains = another_cell.contains
        
        if temp != None:
            temp.x = another_cell.x
            temp.y = another_cell.y

        another_cell.contains = temp
    
    def set(self, contains):
        self.contains = contains
        if contains != None:
            contains.x = self.x
            contains.y = self.y
