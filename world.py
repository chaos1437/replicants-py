from world_utils import *



class World:
    def __init__(self, world_map, tick=0):
        self.width = world_map.width
        self.height = world_map.height
        self.pending_interactions = {} # {type: [interaction, interaction, ...]}
        self.tick = tick
        self.bots = []
        self.map = world_map
    

    def spawn(self, bot): # Find free cell and set bot coordinates in it
        
        free_cell = self.map.get_free_cell()
        
        if free_cell:
            bot.x, bot.y = free_cell.x, free_cell.y
            
            self.map.get_cell(bot.x, bot.y).set(bot)
            
        else:
            raise ValueError("No free cell available for spawning")
        


    def queue_interaction(self, interaction: Interaction):
        self.pending_interactions.setdefault(interaction.type, []).append(interaction)


    def process_interactions(self):
        for interaction_type in self.pending_interactions:
            for interaction in self.pending_interactions[interaction_type]:
                self.execute_interaction(interaction)

        self.pending_interactions.clear()
        self.tick += 1


    def vision_for_bot(self, bot):
        pass


    def execute_interaction(self, interaction: Interaction):
                    

        match interaction.type:

            
            case -1: # Death
                cell = self.map.get_cell(interaction.bot.x, interaction.bot.y)
                cell.contains = None
                cell.energy += interaction.bot.energy // 2
                self.bots.remove(interaction.bot)
                cell.set(None)
            
            case 0: # Move

                if interaction.bot.direction == 4: #stay
                    cell = self.map.get_cell(interaction.bot.x, interaction.bot.y)
                    interaction.bot.energy += cell.energy//5
                    cell.energy -= cell.energy//5
                
                else:
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    self.map.move(interaction.bot.x, interaction.bot.y,  estimated_x, estimated_y)
                    
            case 1: #Replace with another bot
                if interaction.direction == 4: #stay
                    self.pending_interactions[interaction.type].remove(interaction)
                    return

                for i in self.pending_interactions[interaction.type]:

                    if not(i is interaction):
                        estimated_x, estimated_y = get_estimated_coords(i)
                        if estimated_x == interaction.bot.x and estimated_y == interaction.bot.y:
                            self.map.move(interaction.bot.x, interaction.bot.y,  estimated_x, estimated_y)
                            return
            


                

            
        
        interaction.bot.energy -= 1
        if interaction.bot.energy <= 0:
            interaction.bot.alive = False
            
                
