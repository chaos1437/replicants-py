import random
from world import World, Interaction


class Genome:

    unchangable_registers = [5, 6, 7, 8, 10]

    registers = [0 for i in range(24)]

    commands = ["+", "-", ">", "<", "[", "]"]

    max_ticks = 1024 #TTL

    program_length = 256


    def __init__(self, parent_genome=None):
        self.program = self.mutate_program(parent_genome.program)
        self.current_register = 0 



    def mutate_program(self, parent_program):
        program = parent_program.copy()

        if parent_program == None:
            program = [random.choice(self.commands) for i in range(self.program_length)]

        for i in range(self.program_length):

            if random.randint(0, 100) < 10: #todo 10% от всего генома имеет шанс мутировать, а не весь геном.
                program[i] = random.choice[self.commands]
            else:
                program[i] = parent_program[i]
        
        return program
    

    def check_program(self, program):
        if program.count("[") != program.count("]"):
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
                blocks[i] = opened[-1]
                blocks[opened.pop()] = i
        return blocks


    def execute(self, program):
        
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
    
    def __init__(self, world=None, parent=False):
        
        if parent:
            self.genome = Genome(parent.genome)
            self.energy = parent.energy // 3
            parent.energy -= self.energy
            self.world = world

        else:
            self.genome = Genome(None)
            self.energy = 255 

        
        if self.genome.check_program(self.genome.program):
            self.alive = True
        else:
            self.alive = False
        
    
    def run_genome(self):
        self.genome.execute(self.genome.program)


    def update_vision(self):
        self.genome.registers[5:9] = self.world.vision_for_bot(self)
        

    @property
    def direction(self):
        return self.genome.registers.index(max(self.genome.registers[0:5]))
    

    def queue_interaction(self):
        self.update_vision()

        interaction_type = self.genome.registers[11]
        strength = self.genome.registers[12]
        direction = self.direction
        interaction = Interaction(self, direction, interaction_type, strength)
        self.world.queue_interaction(interaction)

        