import random
from world_utils import Interaction


class Genome:

    unchangable_registers = [5, 6, 7, 8, 10]

    registers = [0 for i in range(24)]

    commands = ["+", "-", ">", "<", "[", "]"]

    max_ticks = 1024 #TTL

    program_length = 256


    def __init__(self, parent_genome=None):
        self.program = self.mutate_program(parent_genome)
        self.current_register = 0 



    def mutate_program(self, parent_genome):
        genome = parent_genome

        if genome == None:
            program = [random.choice(self.commands) for i in range(self.program_length)]
        
            return program


        for i in range(self.program_length):

            if random.randint(0, 100) < 10: #todo 10% от всего генома имеет шанс мутировать, а не весь геном.
                program[i] = random.choice(self.commands)
            else:
                program[i] = genome.program[i]
        
        return program
    

    def check_program(self, program):
        if program.count("[") != program.count("]"):
            return False

        try:
            Genome.parse_blocks(program)
        
        except IndexError:
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
                    raise IndexError
                start = opened.pop()
                blocks[i] = start
                blocks[start] = i
        if opened:
            raise IndexError
        
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
        self.world = world
        self.world.bots.append(self)


        if parent:
            self.genome = Genome(parent.genome)
            self.energy = parent.energy // 3
            parent.energy -= self.energy
            

        else:
            self.genome = Genome(None)
            self.energy = 255
            self.world.spawn(self)

        
        if self.genome.check_program(self.genome.program):
            self.alive = True
        else:
            self.alive = False
        
    
    def run(self):
        if self.alive:
            self.genome.execute(self.genome.program)
        self.queue_interaction()


    def update_vision(self):
        # vision = self.world.vision_for_bot(self)
        # self.genome.registers[5] = vision[0]
        # self.genome.registers[6] = vision[1]
        # self.genome.registers[7] = vision[2]
        # self.genome.registers[8] = vision[3]
        # self.genome.registers[9] = vision[4]
        pass

        

    @property
    def direction(self):
        return self.genome.registers.index(max(self.genome.registers[0:5]))


    def __str__(self) -> str:
        return f"Bot( energy={self.energy} )"
    

    def queue_interaction(self):
        self.update_vision()

        if self.alive:
            interaction_type = self.genome.registers[11]
        
        else:
            interaction_type = -1

        strength = self.genome.registers[12]
        direction = self.direction
        interaction = Interaction(self, direction, interaction_type, strength)
        self.world.queue_interaction(interaction)

