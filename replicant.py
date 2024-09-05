import random
import logging
random = random.SystemRandom()
from world_utils import Interaction
from copy import deepcopy

logger = logging.getLogger(__name__)



class Genome:

    unchangable_registers = [5, 6, 7, 8, 10]

    

    commands = ["+", "-", ">", "<", "[", "]"]

    max_ticks = 512 #TTL

    program_length = 64

    mutation_rate = 0.01


    def __init__(self, parent_genome=None, program_length=128):
        self.registers = [0 for i in range(24)]
        self.program = self.mutate_program(parent_genome)
        self.current_register = 0
        logger.debug(f"Genome initialized: {self.program}")

    def mutate_program(self, parent_genome):
        if parent_genome is None:
            program = [random.choice(self.commands) for _ in range(self.program_length)]
        else:
            program = deepcopy(parent_genome.program)
            for i in range(self.program_length):
                if random.random() < self.mutation_rate:
                    program[i] = random.choice(self.commands)
        return program
    

    def check_program(self, program):
        if program.count("[") != program.count("]"):
            return False

        if self.parse_blocks(program) == False:
            return False

        return True

    @staticmethod
    def parse_blocks(code):
        opened = []
        blocks = {}
        for i in range(len(code)):
            if code[i] == '[':
                opened.append(i)
            elif code[i] == ']':
                if not opened:
                    return False
                start = opened.pop()
                blocks[i] = start
                blocks[start] = i
        if opened:
            return False
        
        return blocks


    def execute(self, program):

        program = deepcopy(program)
        blocks = Genome.parse_blocks(program)
        tick = 0
        self.current_register = 0


        i = 0
        while i < len(program):
            
            sym = program[i]

            match sym:

                case '>':
                    if self.current_register == len(self.registers) - 1:
                        self.current_register = 0
                    else:
                        self.current_register += 1

                case '<':
                    if self.current_register == 0:
                        self.current_register = len(self.registers) - 1
                    else:
                        self.current_register -= 1

                case '+':
                    if not self.current_register in self.unchangable_registers:
                        
                        if self.registers[self.current_register] == 255:
                            self.registers[self.current_register] = 0

                        else:
                            self.registers[self.current_register] += 1

                case '-':
                    if not self.current_register in self.unchangable_registers:
                        
                        if self.registers[self.current_register] == 0:
                            self.registers[self.current_register] = 255
                        
                        else:
                            self.registers[self.current_register] -= 1

                case '[':
                    if not self.registers[self.current_register]: i = blocks[i]

                case ']':
                    if self.registers[self.current_register]: i = blocks[i] 

            i += 1
            tick += 1

            if tick > self.max_ticks:
                return False

        return True


class Bot:
    def __init__(self, parent=None, energy=255, age=0):
        self.energy = energy
        self.genome = Genome(parent.genome if parent else None)
        self.alive = self.genome.check_program(self.genome.program)
        self.x = self.y = None
        self.age = age
        self.id = id(self)  # Use object id as a unique identifier
        logger.debug(f"Bot {self.id} created with energy {self.energy}")

    def run(self):
        if self.alive and self.energy > 0:
            self.genome.registers[10] = self.energy
            self.genome.execute(self.genome.program)
            logger.debug(f"Bot {self.id} ran with energy {self.energy}")
        elif self.energy <= 0:
            self.alive = False
            logger.debug(f"Bot {self.id} died due to lack of energy")
        
        self.age += 1




    @property
    def direction(self):
        if max(self.genome.registers[0:5]) > 0:
            return self.genome.registers.index(max(self.genome.registers[0:5]))
        else:
            return -1

    def get_interaction(self):
        interaction_type = self.genome.registers[11] if self.alive else -1
        strength = self.genome.registers[12]
        direction = self.direction
        interaction = Interaction(self, direction, interaction_type, strength)
        return interaction

    def divide(self):
        if self.energy >= 8:
            energy_for_child = self.energy // 3
            self.energy -= energy_for_child
            child = Bot(self, energy_for_child)
            return child
        return None
