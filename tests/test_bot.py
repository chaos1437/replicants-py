"""Тесты для core/bot.py: Genome и Bot"""
import pytest
from core.bot import Bot, Genome
from core.interaction import Interaction
from config.settings import GenomeConfig


# ═══════════════════════════════════════════════════════════════
# Genome.parse_blocks
# ═══════════════════════════════════════════════════════════════

class TestParseBlocks:
    """Genome.parse_blocks — статический метод, тестируется без создания Genome"""

    def test_parse_blocks_valid(self):
        """Простые валидные скобки [+] → {0: 2, 2: 0}"""
        program = ["[", "+", "]"]
        assert Genome.parse_blocks(program) == {0: 2, 2: 0}

    def test_parse_blocks_unmatched_open(self):
        """Незакрытая скобка [[] → None"""
        program = ["[", "[", "]"]
        assert Genome.parse_blocks(program) is None

    def test_parse_blocks_unmatched_close(self):
        """Лишняя закрывающая [] → None"""
        program = ["[", "]", "]"]
        assert Genome.parse_blocks(program) is None

    def test_parse_blocks_empty(self):
        """Пустые скобки [] → {0: 1, 1: 0}"""
        program = ["[", "]"]
        assert Genome.parse_blocks(program) == {0: 1, 1: 0}

    def test_parse_blocks_nested(self):
        """Вложенные скобки [[]] → {0: 3, 3: 0, 1: 2, 2: 1}"""
        program = ["[", "[", "]", "]"]
        assert Genome.parse_blocks(program) == {0: 3, 3: 0, 1: 2, 2: 1}

    def test_parse_blocks_no_brackets(self):
        """Программа без скобок +++ → {}"""
        program = ["+", "+", "+"]
        assert Genome.parse_blocks(program) == {}


# ═══════════════════════════════════════════════════════════════
# Genome.check_program
# ═══════════════════════════════════════════════════════════════

class TestCheckProgram:
    """Genome.check_program — проверка баланса скобок"""

    def test_check_program_valid(self, genome):
        """Валидная программа → True"""
        genome.program = ["+", "[", "+", "]", "-"]
        assert genome.check_program(genome.program) is True

    def test_check_program_invalid_count(self, genome):
        """Несовпадающее количество скобок [[] → False"""
        genome.program = ["[", "[", "]"]   # 2 open, 1 close
        assert genome.check_program(genome.program) is False

    def test_check_program_invalid_order(self, genome):
        """Неправильный порядок скобок ][ → False"""
        genome.program = ["]", "["]
        assert genome.check_program(genome.program) is False


# ═══════════════════════════════════════════════════════════════
# Genome.execute
# ═══════════════════════════════════════════════════════════════

class TestExecute:
    """Genome.execute — выполнение brainfuck-подобной программы"""

    def test_execute_simple(self, genome):
        """+++ → registers[0] == 3"""
        result = genome.execute(["+", "+", "+"])
        assert result is True
        assert genome.registers[0] == 3

    def test_execute_loop(self, genome):
        """[>+<-] с registers[0]=3 → обнуляет reg[0], переносит значение в reg[1]"""
        genome.registers[0] = 3
        program = ["[", ">", "+", "<", "-", "]"]
        result = genome.execute(program)
        assert result is True
        assert genome.registers[0] == 0
        assert genome.registers[1] == 3

    def test_execute_max_ticks(self, genome_config):
        """Бесконечный цикл [] при registers[0]=1 → False (превышение max_ticks)"""
        genome = Genome(genome_config)  # max_ticks = 512
        genome.registers[0] = 1
        result = genome.execute(["[", "]"])
        assert result is False

    def test_execute_unchangable_registers(self, genome):
        """Попытка изменить unchangable регистр 5 → значение не меняется"""
        # 5 раз > (переход на регистр 5), затем +
        result = genome.execute([">", ">", ">", ">", ">", "+"])
        assert result is True
        assert genome.registers[5] == 0  # unchangable, не изменился

    def test_execute_wrap_around(self, genome):
        """< на регистре 0 → 23, затем > → 0, затем +++ (проверка wrap)"""
        # < (0→23), > (23→0), +, +, +
        result = genome.execute(["<", ">", "+", "+", "+"])
        assert result is True
        assert genome.registers[0] == 3

    def test_execute_register_overflow(self, genome):
        """256 раз + → переполнение: registers[0] == 0 (255→0)"""
        program = ["+"] * 256
        result = genome.execute(program)
        assert result is True
        assert genome.registers[0] == 0


# ═══════════════════════════════════════════════════════════════
# Genome.mutate_program
# ═══════════════════════════════════════════════════════════════

class TestMutateProgram:
    """Genome.mutate_program — создание и мутация программ"""

    def test_mutate_no_parent(self, genome_config):
        """Без родителя: длина новой программы == program_length"""
        genome = Genome(genome_config)
        assert len(genome.program) == genome_config.program_length
        for cmd in genome.program:
            assert cmd in Genome.commands

    def test_mutate_with_parent(self):
        """С родителем и mutation_rate=1.0: программа наследуется и мутирует"""
        config = GenomeConfig(mutation_rate=1.0, program_length=64, max_ticks=512)
        parent = Genome(config)
        child = Genome(config, parent_genome=parent)
        assert len(child.program) == config.program_length
        assert child.program != parent.program  # мутации гарантированы rate=1.0


# ═══════════════════════════════════════════════════════════════
# Bot.direction
# ═══════════════════════════════════════════════════════════════

class TestBotDirection:
    """Bot.direction — направление по регистрам 0-4"""

    def test_direction_max_register(self, bot):
        """reg[1]=10 — максимальное значение среди 0-4 → direction == 1"""
        bot.genome.registers[0] = 0
        bot.genome.registers[1] = 10
        bot.genome.registers[2] = 0
        bot.genome.registers[3] = 0
        bot.genome.registers[4] = 0
        assert bot.direction == 1

    def test_direction_all_zero(self, bot):
        """Все регистры 0-4 равны 0 → direction == -1"""
        bot.genome.registers[0] = 0
        bot.genome.registers[1] = 0
        bot.genome.registers[2] = 0
        bot.genome.registers[3] = 0
        bot.genome.registers[4] = 0
        assert bot.direction == -1


# ═══════════════════════════════════════════════════════════════
# Bot.divide
# ═══════════════════════════════════════════════════════════════

class TestDivide:
    """Bot.divide — деление бота"""

    def test_divide_enough_energy(self, genome_config):
        """energy=255 → child создан, родитель теряет энергию"""
        bot = Bot(config=genome_config, energy=255)
        initial_energy = bot.energy
        child = bot.divide()
        assert child is not None
        assert isinstance(child, Bot)
        expected_child_energy = initial_energy // 3
        assert child.energy == expected_child_energy
        assert bot.energy == initial_energy - expected_child_energy

    def test_divide_not_enough_energy(self, genome_config):
        """energy=4 (< 8) → None"""
        bot = Bot(config=genome_config, energy=4)
        child = bot.divide()
        assert child is None
        assert bot.energy == 4  # энергия не изменилась


# ═══════════════════════════════════════════════════════════════
# Bot.run
# ═══════════════════════════════════════════════════════════════

class TestRun:
    """Bot.run — тик работы бота"""

    def test_run_alive(self, genome_config):
        """Живой бот с energy>0: registers[10] == energy, age += 1"""
        bot = Bot(config=genome_config, energy=100, age=5)
        # Контролируем программу и состояние
        bot.genome.program = ["+"]  # валидная программа
        bot.alive = True
        initial_age = bot.age

        bot.run()

        assert bot.genome.registers[Genome.REG_ENERGY] == 100
        assert bot.age == initial_age + 1
        assert bot.alive is True

    def test_run_dead(self, genome_config):
        """Мёртвый бот (alive=False): age += 1, registers[10] не меняется"""
        bot = Bot(config=genome_config, energy=100, age=10)
        bot.alive = False
        initial_age = bot.age

        bot.run()

        # age увеличивается даже для мёртвых (self.age += 1 вне условия)
        assert bot.age == initial_age + 1
        # register[10] не был установлен, т.к. alive=False
        assert bot.genome.registers[Genome.REG_ENERGY] == 0


# ═══════════════════════════════════════════════════════════════
# Bot.get_interaction
# ═══════════════════════════════════════════════════════════════

class TestGetInteraction:
    """Bot.get_interaction — создание Interaction"""

    def test_get_interaction_alive(self, bot):
        """Живой бот → Interaction с заданными type, strength, direction"""
        bot.alive = True
        bot.genome.registers[Genome.REG_INTERACTION_TYPE] = 2
        bot.genome.registers[Genome.REG_INTERACTION_STRENGTH] = 3
        bot.genome.registers[1] = 5  # максимальное среди 0-4 → direction = 1

        interaction = bot.get_interaction()

        assert isinstance(interaction, Interaction)
        assert interaction.bot is bot
        assert interaction.type == 2
        assert interaction.strength == 3
        assert interaction.direction == 1

    def test_get_interaction_dead(self, bot):
        """Мёртвый бот (alive=False) → interaction_type == -1"""
        bot.alive = False

        interaction = bot.get_interaction()

        assert isinstance(interaction, Interaction)
        assert interaction.type == -1
