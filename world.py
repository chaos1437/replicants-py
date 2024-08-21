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
            self.bots.remove(bot)
        


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

    
    def remove_bot(self, bot):
        try:
            cell = self.map.get_cell(bot.x, bot.y)
            cell.contains = None
            cell.energy += bot.energy // 2
            self.bots.remove(bot)
            cell.set(None)
        
        except AttributeError:
            
            if bot in self.bots:
                self.bots.remove(bot)
        

    def bot_energy_draining(self, bot, cell):
        if bot.energy + cell.energy//5 > 255:
            cell.energy -= bot.energy + 255
            bot.energy = 255
        else:
            if cell.energy > 0:
                bot.energy += cell.energy//5
                cell.energy -= cell.energy//5


    def execute_interaction(self, interaction: Interaction):
        if interaction.type != -1: print("execute_interaction", interaction)

        match interaction.type:
            
            case -2: #Spawn
                self.spawn(interaction.bot)
                self.bots.append(interaction.bot)
            
            case -1: # Death
                self.remove_bot(interaction.bot)
            
            case 0: # Move

                if interaction.bot.direction == 4: #stay
                    cell = self.map.get_cell(interaction.bot.x, interaction.bot.y)
                    
                    self.bot_energy_draining(interaction.bot, cell)

                
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
            

            case 2: #Push energy
                if interaction.direction != 4: #stay
                    estimated_x, estimated_y = get_estimated_coords(interaction)

                    strength = max(interaction.strength, interaction.bot.energy)

                    cell = self.map.get_cell(estimated_x, estimated_y)
                    
                    if cell: #if cell exists
                        cell.energy += strength
                        interaction.bot.energy -= strength
            

            case 3: #Get energy from near cells
                estimated_x, estimated_y = get_estimated_coords(interaction)
                cell = self.map.get_cell(estimated_x, estimated_y)

                if cell: #if cell exists
                    self.bot_energy_draining(interaction.bot, cell)
            

            case 4: #Send info to another bot
                if interaction.direction != 4: #stay
                    estimated_x, estimated_y = get_estimated_coords(interaction)
                    
                    if 5 in self.pending_interactions:
                        for i in self.pending_interactions[5]: # 5 - recieve info; 4 - send info
                            if not(i is interaction):

                                if i.bot.x == estimated_x and i.bot.y == estimated_y:
                                    i.bot.genome.registers[9] = interaction.bot.genome.registers[13]
                                    break
            
            case 5: #Recieve info from another bot
                # The actual handling of received information likely occurs in the sending bot's logic (case 4)
                pass
                
        if interaction.type >= 6: #Divide (sex)
            if interaction.direction != 4: #stay
                estimated_x, estimated_y = get_estimated_coords(interaction)
                cell = self.map.get_cell(estimated_x, estimated_y)
                if cell and cell.contains == None:
                    bot = interaction.bot.divide()
                    cell.set(bot)
        
        
        interaction.bot.energy -= 1
        if interaction.bot.energy <= 0:
            self.remove_bot(interaction.bot)
            
                
