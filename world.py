from replicant import Bot
from world_utils import *



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

        match interaction.type:
            case -1:
                pass

