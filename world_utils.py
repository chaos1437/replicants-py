from collections import namedtuple
import json

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
    
    def _move(self, first_cell, another_cell):
        temp = first_cell.contains

        if another_cell.contains != None:
            another_cell.x = first_cell.x
            another_cell.y = first_cell.y

        self.contains = another_cell.contains
        
        if temp != None:
            temp.x = another_cell.x
            temp.y = another_cell.y

        another_cell.contains = temp
    
    def move(self, x, y, x1, y1):
        
        self._move(self.map[y][x], self.map[y1][x1])
    

    def get_json(self):
        json_map = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                cell = self.map[y][x]
                cell_data = {
                    "x": cell.x,
                    "y": cell.y,
                    "energy": cell.energy,
                    "contains": str(cell.contains) if cell.contains else None
                }
                row.append(cell_data)
            json_map.append(row)
        return json.dumps(json_map)




#Ячейка пространства на карте
class Cell:
    def __init__(self, x, y, contains=None, energy=100):
        self.x = x
        self.y = y
        self.contains=contains
        self.energy = energy
    
    def set(self, contains):
        self.contains = contains
        if contains != None:
            contains.x = self.x
            contains.y = self.y
