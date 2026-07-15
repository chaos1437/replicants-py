"""Боты и их геномы"""
import random
import logging
from typing import Optional

random = random.SystemRandom()
logger = logging.getLogger(__name__)

OP_INC, OP_DEC, OP_NEXT, OP_PREV, OP_JZ, OP_JNZ = range(6)


class Genome:
    """Геном бота - программа и регистры"""
    
    unchangable_registers = frozenset({5, 6, 7, 8, 10})
    SENSOR_REGISTERS = [(-1, 0, 5), (0, 1, 6), (1, 0, 7), (0, -1, 8)]
    REG_ENERGY = 10
    REG_INTERACTION_TYPE = 11
    REG_INTERACTION_STRENGTH = 12
    REG_SEND_DATA = 13
    REG_RECV_DATA = 9
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
        compiled = self.compile_program(self.program)
        if compiled is not None:
            self.opcodes, self.jumps = compiled
        else:
            self.opcodes, self.jumps = (), ()  # Invalid program
        self.current_register = 0
    
    def mutate_program(self, parent_genome: Optional['Genome']) -> list:
        """Создает программу: новую случайную или с мутацией родительской"""
        if parent_genome is None:
            program = [random.choice(self.commands) for _ in range(self.program_length)]
        else:
            program = parent_genome.program[:]
            for i in range(self.program_length):
                if random.random() < self.mutation_rate:
                    program[i] = random.choice(self.commands)
        return program
    
    @staticmethod
    def compile_program(program: list) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
        """Скомпилировать программу в (opcodes, jumps). opcodes: int 0-5, jumps: target index or -1"""
        CHAR_TO_OP = {'+': OP_INC, '-': OP_DEC, '>': OP_NEXT, '<': OP_PREV, '[': OP_JZ, ']': OP_JNZ}
        n = len(program)
        opcodes = [0] * n
        jumps = [-1] * n
        stack = []
        for i, sym in enumerate(program):
            op = CHAR_TO_OP.get(sym)
            if op is None:
                return None
            opcodes[i] = op
            if sym == '[':
                stack.append(i)
            elif sym == ']':
                if not stack:
                    return None
                start = stack.pop()
                jumps[start] = i
                jumps[i] = start
        if stack:
            return None
        return (tuple(opcodes), tuple(jumps))
    
    def check_program(self, program: list) -> bool:
        """Проверяет корректность программы (баланс скобок)"""
        return self.compile_program(program) is not None
    
    @staticmethod
    def parse_blocks(code: list) -> dict | None:
        """Парсит блоки [] и возвращает словарь соответствий индексов"""
        opened = []
        blocks = {}
        for i in range(len(code)):
            if code[i] == '[':
                opened.append(i)
            elif code[i] == ']':
                if not opened:
                    return None
                start = opened.pop()
                blocks[i] = start
                blocks[start] = i
        if opened:
            return None
        
        return blocks
    
    def execute(self) -> bool:
        """Выполняет скомпилированную программу. Использует self.opcodes, self.jumps."""
        opcodes = self.opcodes
        jumps = self.jumps
        if not opcodes:
            return True  # пустая/невалидная программа — ничего не делаем
        
        regs = self.registers
        unch = self.unchangable_registers  # frozenset
        max_t = self.max_ticks
        n = len(opcodes)
        cur = 0
        tick = 0
        i = 0
        
        while i < n:
            op = opcodes[i]
            if op == OP_INC:
                if cur not in unch:
                    v = regs[cur] + 1
                    regs[cur] = 0 if v > 255 else v
            elif op == OP_DEC:
                if cur not in unch:
                    v = regs[cur] - 1
                    regs[cur] = 255 if v < 0 else v
            elif op == OP_NEXT:
                cur = 0 if cur == 23 else cur + 1
            elif op == OP_PREV:
                cur = 23 if cur == 0 else cur - 1
            elif op == OP_JZ:
                if not regs[cur]:
                    i = jumps[i]
            elif op == OP_JNZ:
                if regs[cur]:
                    i = jumps[i]
            
            i += 1
            tick += 1
            if tick > max_t:
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
            self.genome.registers[Genome.REG_ENERGY] = self.energy
            self.genome.execute()  # больше не передаём program
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
        
        interaction_type = self.genome.registers[Genome.REG_INTERACTION_TYPE] if self.alive else -1
        strength = self.genome.registers[Genome.REG_INTERACTION_STRENGTH]
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
