from world_utils import *



class World:
    def __init__(self, width, height, world_map, tick=0):
        self.width = width
        self.height = height
        self.bots = []
        self.pending_interactions = []
        self.tick = tick
        self.map = world_map


    def queue_interaction(self, interaction: Interaction):
        self.pending_interactions.append(interaction)


    def process_interactions(self):
        for interaction in self.pending_interactions:
            self.execute_interaction(interaction)

        self.pending_interactions.clear()
        self.tick += 1


    def execute_interaction(self, interaction: Interaction):
        
        match interaction.type:
            
            case -1: # Death
                cell = map[interaction.bot.x][interaction.bot.y]
                cell.contains = None
                cell.energy += interaction.bot.energy // 2
            
            case 0: # Move

                match interaction.direction:
                    case 0: #left
                        self.map.move(interaction.bot.x, interaction.bot.y,  interaction.bot.x - 1, interaction.bot.y)
                    
                    case 1: #up
                        self.map.move(interaction.bot.x, interaction.bot.y,  interaction.bot.x, interaction.bot.y + 1)
                    
                    case 2: #right
                        self.map.move(interaction.bot.x, interaction.bot.y,  interaction.bot.x + 1, interaction.bot.y)
                    
                    case 3: #down
                        self.map.move(interaction.bot.x, interaction.bot.y,  interaction.bot.x, interaction.bot.y - 1)

                