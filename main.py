import random
from world import World, Interaction

# def interpreter(code, x=0, y=0):
#     registers = [0, 0, 0, 0]
#     current_register = 0

#     for command in code:
#         match command:
#             case "+":
#                 registers[current_register] += 1
            
#             case ">":
#                 current_register += 1
#                 if current_register > 3:
#                     current_register = 0
        
#             case "<":
#                 current_register -= 1
#                 if current_register < 0:
#                     current_register = 3
        
#         print(x, y, registers)
    
#     direction = registers.index(max(registers))

#     match direction:
#         case 0:
#             x -= 1
#         case 1:
#             y += 1
#         case 2:
#             x += 1
#         case 3:
#             y -= 1
    
#     return x, y

# x, y = interpreter("+>+>+>+>+")
# print(x, y)



class Genome:

    unchangable_registers = [5, 6, 7, 8, 9]

    registers = [0 for i in range(24)]

    commands = ["+", "-", ">", "<", "[", "]"]

    max_ticks = 1000

    program_length = 256


    def __init__(self, parent_program):
        self.program = self.mutate(parent_program)
        self.current_register = 0



    def mutate(self, parent_program):
        program = parent_program.copy()

        if parent_program == None:
            program = [random.choice(self.commands) for i in range(self.program_length)]

        for i in range(self.program_length):

            if random.randint(0, 100) < 10:
                program[i] = random.choice[self.commands]
            else:
                program[i] = parent_program[i]
        
        return program
    

    def check_program(self, program):
        if program.count("[") != program.count("]"):
            return False

        for i in range(24):
            if program[i] not in self.commands:
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
        bf = {0: 0}
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
                    bf.setdefault(self.current_register, 0)

                case '<':
                    if self.current_register == 0:
                        self.current_register = len(self.registers) - 1
                    else:
                        self.current_register -= 1

                case '+':
                    if not self.current_register in self.unchangable_registers:
                        bf[self.current_register] += 1

                case '-':
                    if not self.current_register in self.unchangable_registers:
                        bf[self.current_register] -= 1

                case '[':
                    if not bf[self.current_register]: i = blocks[i]

                case ']':
                    if bf[self.current_register]: i = blocks[i] 

            i += 1
            tick += 1

            if tick > self.max_ticks:
                return False

        return True


class Bot:
    
    def __init__(self, parent=False):
        
        if parent:
            self.genome = Genome(parent.genome)
            self.energy = parent.energy // 3
        
        else:
            self.genome = Genome(None)
            self.energy = 100 

        
        if self.genome.check_program(self.genome.program):
            self.alive = True
        else:
            self.alive = False

        self.x = 0
        self.y = 0
        
    
    def update(self):
        self.genome.execute(self.genome.program)


    @property
    def direction(self):
        return self.genome.registers.index(max(self.genome.registers[0:5]))
    
    def interact(self):
        interaction_type = self.genome.registers[11]
        strength = self.genome.registers[12]
        direction = self.direction
        interaction = Interaction(self, direction, interaction_type, strength)
        self.world.queue_interaction(interaction)


