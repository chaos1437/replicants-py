import logging
from world_utils import *
from replicant import Bot

logger = logging.getLogger(__name__)

class World:
    
    def __init__(self, world_map, tick=0,):
        self.width = world_map.width
        self.height = world_map.height
        self.pending_interactions = {}
        self.tick = tick
        self.bots = []
        self.map = world_map
        self.energy_boost = 50
        self.bot_genome_data = None #using when saving the world state
        logger.info(f"World initialized with size {self.width}x{self.height}")

    def to_json(self):
        world_state = {
            "width": self.width,
            "height": self.height,
            "tick": self.tick,
            "bot_genome_data": self.bot_genome_data,
            "energy_boost": self.energy_boost,
            "bots": [],
            "map": self.map.get_json()
        }
        for bot in self.bots:
            if bot.alive: 
                world_state["bots"].append({
                        "id": bot.id,
                        "x": bot.x,
                        "y": bot.y,
                        "energy": bot.energy,
                        "age": bot.age,
                        "genome": {
                            "program": bot.genome.program,
                            "registers": bot.genome.registers
                        }
                    } )
        return json.dumps(world_state)
    
    def update_cells_energy(self):
        for y in self.map.map:
            for cell in y:
                cell.add_energy(self.energy_boost)
        
        logger.debug(f"Added {self.energy_boost} energy to all cells")


    @classmethod
    def from_json(cls, json_data):
        data = json.loads(json_data)
        world_map = WorldMap.from_json(data["map"])
        world = cls(world_map, data["tick"])
        world.energy_boost = data["energy_boost"]
        
        
        for bot_data in data["bots"]:
            bot = Bot(energy=bot_data["energy"])
            bot.id = bot_data["id"]
            bot.x = bot_data["x"]
            bot.y = bot_data["y"]
            bot.genome.program = bot_data["genome"]["program"]
            bot.genome.registers = bot_data["genome"]["registers"]
            bot.age = bot_data["age"]
            bot.alive = True
            world.map.get_cell(bot.x, bot.y).set(bot)
            world.bots.append(bot)
        
        return world

    def spawn(self, bot):
        free_cell = self.map.get_free_cell()
        if free_cell:
            bot.x, bot.y = free_cell.x, free_cell.y
            self.map.get_cell(bot.x, bot.y).set(bot)
            self.bots.append(bot)
            return True
        logger.warning("Failed to spawn bot: no free cells")
        return False

    def queue_interaction(self, interaction):
        self.pending_interactions.setdefault(interaction.type, []).append(interaction)

    def process_interactions(self):
        for interaction_type in self.pending_interactions:
            for interaction in self.pending_interactions[interaction_type]:
                self.execute_interaction(interaction)
        self.pending_interactions.clear()
        self.tick += 1

        if self.tick % 100 == 0:
            logger.info(f"Tick {self.tick} completed, interactions processed")


        self.check_consistency()

    def remove_dead_bots(self):
        for bot in self.bots:
            if bot.energy <= 0 or not bot.alive:
                self.remove_bot(bot)

    def remove_bot(self, bot):
        cell = self.map.get_cell(bot.x, bot.y)
        if cell and cell.contains == bot:
            cell.contains = None
            cell.add_energy(max(0, bot.energy) // 2)
        if bot in self.bots:
            self.bots.remove(bot)

    def bot_energy_draining(self, bot, cell):
        energy_transfer = min(cell._energy // 5, 255 - bot.energy)
        bot.energy += energy_transfer
        cell.add_energy(-energy_transfer)

    def bot_push_energy(self, bot, cell, energy):
        energy_transfer = min(energy, 255 - cell._energy)
        bot.energy -= energy_transfer
        cell.add_energy(energy_transfer)

    def update_vision_for_bot(self, bot):

        for x, y, register in [(-1, 0, 5), (0, 1, 6), (1, 0, 7), (0, -1, 8)]:
            
            if self.map.get_cell(bot.x + x, bot.y + y):
                if self.map.get_cell(bot.x + x, bot.y + y).contains:
                    bot.genome.registers[register] = 1 #replicant
                else:
                    bot.genome.registers[register] = 0 #empty
            else:
                bot.genome.registers[register] = 2 #world_border or

    def execute_interaction(self, interaction: Interaction):
        # if interaction.bot.energy <= 0 or not interaction.bot.alive:
        #     self.remove_bot(interaction.bot)
        #     logger.info(f"Bot {interaction.bot.id} removed before interaction due to death or lack of energy")
        #     return

        match interaction.type:
            case -2:  # Spawn
                self.spawn(interaction.bot)
                interaction.bot.genome.registers[11] = 0
            
            case -1:  # Death
                self.remove_bot(interaction.bot)
            
            case 0:  # Move
                if interaction.bot.direction == 4:  # stay
                    cell = self.map.get_cell(interaction.bot.x, interaction.bot.y)
                    self.bot_energy_draining(interaction.bot, cell)
                
                elif interaction.direction == -1:
                    pass
                
                else:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    if self.map.get_cell(estimated_x, estimated_y):
                        self.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)
            
            case 1:  # Replace with another bot OR move
                if interaction.direction == 4:
                    cell = self.map.get_cell(interaction.bot.x, interaction.bot.y)
                    self.bot_energy_draining(interaction.bot, cell)
                
                elif interaction.direction == -1:
                    pass

                else:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    target_cell = self.map.get_cell(estimated_x, estimated_y)
                    if target_cell and target_cell.contains:
                        self.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)

                    elif target_cell and target_cell.contains == None:
                        estimated_x, estimated_y = get_estimated_coords(interaction)

                        if self.map.get_cell(estimated_x, estimated_y):
                            self.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)

            
            case 2:  # Push energy
                if interaction.direction != 4:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    cell = self.map.get_cell(estimated_x, estimated_y)
                    if cell:
                        self.bot_push_energy(interaction.bot, cell, interaction.strength)
            
            case 3:  # Get energy from near cells
                estimated_x, estimated_y = get_estimated_coords(interaction)
                cell = self.map.get_cell(estimated_x, estimated_y)
                if cell:
                    self.bot_energy_draining(interaction.bot, cell)
            
            case 4:  # Send info to another bot
                if interaction.direction != 4:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    target_cell = self.map.get_cell(estimated_x, estimated_y)
                    if target_cell and target_cell.contains:
                        target_cell.contains.genome.registers[9] = interaction.bot.genome.registers[13]
                    
            
            case 5:  # Receive info from another bot
                pass  # Handled in case 4
            
            case _:  # Divide (sex)
                if interaction.direction != 4:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    cell = self.map.get_cell(estimated_x, estimated_y)
                    if cell and cell.contains is None:
                        new_bot = interaction.bot.divide()
                        if new_bot:
                            cell.set(new_bot)
                            self.bots.append(new_bot)

        interaction.bot.energy -= 1
        if interaction.bot.energy <= 0:
            self.remove_bot(interaction.bot)


    def check_consistency(self):
        map_bots = set()
        for y in range(self.height):
            for x in range(self.width):
                cell = self.map.get_cell(x, y)
                if cell.contains and isinstance(cell.contains, Bot):
                    map_bots.add(cell.contains)
        
        list_bots = set(self.bots)
        
        if map_bots != list_bots:
            self.bots = list(map_bots)
            logger.warning("Inconsistency detected and corrected in bot list")

