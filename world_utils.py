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
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.map[y][x]
        else:
            return False        
        
    def _move(self, first_cell, another_cell):
        temp = first_cell.contains

        if another_cell.contains is not None:
            another_cell.contains.x = first_cell.x
            another_cell.contains.y = first_cell.y

        first_cell.contains = another_cell.contains
        
        if temp is not None:
            temp.x = another_cell.x
            temp.y = another_cell.y

        another_cell.contains = temp
    

    def move(self, x, y, x1, y1):
        
        if self.width - 1 > x1 > 0 and self.height - 1 > y1 > 0:

            self._move(self.map[y][x], self.map[y1][x1])
    

    def get_free_cell(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.get_cell(x, y).contains == None:
                    return self.get_cell(x, y)
                
        return False
    

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



def get_estimated_coords(interaction):

    estimated_x, estimated_y = interaction.bot.x, interaction.bot.y

    match interaction.direction:
        case 0: #left
            estimated_x, estimated_y = interaction.bot.x - 1, interaction.bot.y
        
        case 1: #up
            estimated_x, estimated_y = interaction.bot.x, interaction.bot.y + 1
        
        case 2: #right
            estimated_x, estimated_y = interaction.bot.x + 1, interaction.bot.y
        
        case 3: #down
            estimated_x, estimated_y =  interaction.bot.x, interaction.bot.y - 1
    
    return estimated_x, estimated_y


#Ячейка пространства на карте
class Cell:
    def __init__(self, x, y, contains=None, energy=100):
        self.x = x
        self.y = y
        self.contains = contains
        self.energy = energy
    
    def set(self, contains):
        self.contains = contains
        if contains is not None:
            contains.x = self.x
            contains.y = self.y