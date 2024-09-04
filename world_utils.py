from collections import namedtuple
import json
import logging

logger = logging.getLogger(__name__)

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
        self.map = [[Cell(x, y) for x in range(width)] for y in range(height)]
        logger.info(f"WorldMap initialized with width {width} and height {height}")
    
    def get_cell(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            #logger.debug(f"Getting cell at ({x}, {y})")
            return self.map[y][x]
        else:
            logger.debug(f"Attempted to get cell outside map bounds: ({x}, {y})")
            return False        
        
    def _move(self, first_cell, another_cell):
        logger.debug(f"Moving from cell ({first_cell.x}, {first_cell.y}) to ({another_cell.x}, {another_cell.y})")
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
            logger.info(f"Moving from ({x}, {y}) to ({x1}, {y1})")
            self._move(self.map[y][x], self.map[y1][x1])
        else:
            logger.debug(f"Attempted to move outside map bounds: from ({x}, {y}) to ({x1}, {y1})")
    

    def get_free_cell(self):
        for y in range(self.height):
            for x in range(self.width):
                if self.get_cell(x, y).contains == None:
                    logger.debug(f"Found free cell at ({x}, {y})")
                    return self.get_cell(x, y)
        
        logger.warning("No free cells found")
        return False
    

    def get_json(self):
        logger.debug("Generating JSON representation of the map")
        json_map = []
        for y in range(self.height):
            row = []
            for x in range(self.width):
                cell = self.map[y][x]
                cell_data = {
                    "x": cell.x,
                    "y": cell.y,
                    "energy": cell.energy,
                }
                row.append(cell_data)
            json_map.append(row)
        return json.dumps(json_map)

    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        world_map = cls(len(data[0]), len(data))
        for y, row in enumerate(data):
            for x, cell_data in enumerate(row):
                cell = world_map.get_cell(x, y)
                cell.energy = cell_data["energy"]
        return world_map


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
        logger.debug(f"Cell created at ({x}, {y}) with energy {energy}")
    
    def set(self, contains):
        logger.debug(f"Setting contents of cell ({self.x}, {self.y})")
        self.contains = contains
        if contains is not None:
            contains.x = self.x
            contains.y = self.y
            logger.debug(f"Contents set to {contains} at ({self.x}, {self.y})")