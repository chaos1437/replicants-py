"""Боты и их геномы"""
import random
import logging
from copy import deepcopy
from typing import Optional

random = random.SystemRandom()
logger = logging.getLogger(__name__)


class Genome:
    """Геном бота - программа и регистры"""
    
    unchangable_registers = [5, 6, 7, 8, 10]
    commands = ["+", "-", ">", "<", "[", "]"]
    
    def __init__(self, config, parent_genome=None):
        """
        Args:
            config: GenomeConfig с параметрами mutation_rate, program_length, max_ticks
            parent_genome: родительский геном для наследования (опционально)
        """
        self.config = config
        self.mutation_rate = config.mutation_rate
        self.program_length = config.program_length
        self.max_ticks = config.max_ticks
        
        self.registers = [0 for _ in range(24)]
        self.program = self.mutate_program(parent_genome)
        self.current_register = 0
    
    def mutate_program(self, parent_genome: Optional['Genome']) -> list:
        """Создает программу: новую случайную или с мутацией родительской"""
        if parent_genome is None:
            program = [random.choice(self.commands) for _ in range(self.program_length)]
        else:
            program = deepcopy(parent_genome.program)
            for i in range(self.program_length):
                if random.random() < self.mutation_rate:
                    program[i] = random.choice(self.commands)
        return program
    
    def check_program(self, program: list) -> bool:
        """Проверяет корректность программы (баланс скобок)"""
        if program.count("[") != program.count("]"):
            return False
        
        if self.parse_blocks(program) is False:
            return False
        
        return True
    
    @staticmethod
    def parse_blocks(code: list) -> dict | bool:
        """Парсит блоки [] и возвращает словарь соответствий индексов"""
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
    
    def execute(self, program: list) -> bool:
        """Выполняет программу (brainfuck-like язык)"""
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
                    if self.current_register not in self.unchangable_registers:
                        if self.registers[self.current_register] == 255:
                            self.registers[self.current_register] = 0
                        else:
                            self.registers[self.current_register] += 1
                
                case '-':
                    if self.current_register not in self.unchangable_registers:
                        if self.registers[self.current_register] == 0:
                            self.registers[self.current_register] = 255
                        else:
                            self.registers[self.current_register] -= 1
                
                case '[':
                    if not self.registers[self.current_register]:
                        i = blocks[i]
                
                case ']':
                    if self.registers[self.current_register]:
                        i = blocks[i]
            
            i += 1
            tick += 1
            
            if tick > self.max_ticks:
                return False
        
        return True


class Bot:
    """Бот с геномом, энергией и позицией"""
    
    def __init__(self, config=None, parent: Optional['Bot'] = None, energy: int = 255, age: int = 0):
        """
        Args:
            config: GenomeConfig для создания генома
            parent: родительский бот (для наследования генома)
            energy: начальная энергия
            age: начальный возраст
        """
        self.energy = energy
        self.genome = Genome(config, parent.genome if parent else None)
        self.alive = self.genome.check_program(self.genome.program)
        self.x = None
        self.y = None
        self.age = age
        self.id = id(self)
    
    def run(self):
        """Выполняет один тик работы бота"""
        if self.alive and self.energy > 0:
            self.genome.registers[10] = self.energy
            self.genome.execute(self.genome.program)
        elif self.energy <= 0:
            self.alive = False
        
        self.age += 1
    
    @property
    def direction(self) -> int:
        """Определяет направление взаимодействия на основе регистров 0-4"""
        if max(self.genome.registers[0:5]) > 0:
            return self.genome.registers.index(max(self.genome.registers[0:5]))
        else:
            return -1
    
    def get_interaction(self):
        """Возвращает взаимодействие, которое хочет выполнить бот"""
        from core.interaction import Interaction
        
        interaction_type = self.genome.registers[11] if self.alive else -1
        strength = self.genome.registers[12]
        direction = self.direction
        
        return Interaction(self, direction, interaction_type, strength)
    
    def divide(self) -> Optional['Bot']:
        """Деление бота (создание потомка)"""
        if self.energy >= 8:
            energy_for_child = self.energy // 3
            self.energy -= energy_for_child
            child = Bot(self.genome.config, self, energy_for_child)
            return child
        return None
