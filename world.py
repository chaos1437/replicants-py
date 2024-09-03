from world_utils import *
from replicant import Bot

class World:
    def __init__(self, world_map, tick=0):
        self.width = world_map.width
        self.height = world_map.height
        self.pending_interactions = {}
        self.tick = tick
        self.bots = []
        self.map = world_map

    def spawn(self, bot):
        free_cell = self.map.get_free_cell()
        if free_cell:
            bot.x, bot.y = free_cell.x, free_cell.y
            self.map.get_cell(bot.x, bot.y).set(bot)
            self.bots.append(bot)
            return True
        return False

    def queue_interaction(self, interaction):
        self.pending_interactions.setdefault(interaction.type, []).append(interaction)

    def process_interactions(self):
        for interaction_type in self.pending_interactions:
            for interaction in self.pending_interactions[interaction_type]:
                self.execute_interaction(interaction)
        self.pending_interactions.clear()
        self.tick += 1
        self.check_consistency()

    def remove_dead_bots(self):
        for bot in self.bots:
            if bot.energy <= 0 or not bot.alive:
                self.remove_bot(bot)

    def remove_bot(self, bot):
        cell = self.map.get_cell(bot.x, bot.y)
        if cell and cell.contains == bot:
            cell.contains = None
            cell.energy += max(0, bot.energy) // 2
        if bot in self.bots:
            self.bots.remove(bot)

    def bot_energy_draining(self, bot, cell):
        energy_transfer = min(cell.energy // 5, 255 - bot.energy)
        bot.energy += energy_transfer
        cell.energy -= energy_transfer

    def execute_interaction(self, interaction: Interaction):
        if interaction.bot.energy <= 0 or not interaction.bot.alive:
            self.remove_bot(interaction.bot)
            return

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
                else:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    if self.map.get_cell(estimated_x, estimated_y):
                        self.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)
            
            case 1:  # Replace with another bot
                if interaction.direction != 4:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    target_cell = self.map.get_cell(estimated_x, estimated_y)
                    if target_cell and target_cell.contains:
                        self.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)
            
            case 2:  # Push energy
                if interaction.direction != 4:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    cell = self.map.get_cell(estimated_x, estimated_y)
                    if cell:
                        energy_transfer = min(interaction.strength, interaction.bot.energy)
                        cell.energy += energy_transfer
                        interaction.bot.energy -= energy_transfer
            
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
                            self.spawn(new_bot)

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
            print("Inconsistency detected between map bots and bot list")
            self.bots = list(map_bots)
