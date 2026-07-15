"""Сервис симуляции - headless оркестратор"""
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from core.bot import Bot

logger = logging.getLogger(__name__)


def _execute_bot_chunk(bots_data: list[dict], phase: int) -> list[dict]:
    """Выполнить чанк ботов в воркере.

    phase=2: обновление vision (регистры 5-8)
    phase=3: выполнение программы

    Каждый dict: {id, program, registers, energy, max_ticks}
    Возвращает: {id, registers, energy}
    """
    UNCHANGABLE = {5, 6, 7, 8, 10}
    REG_ENERGY = 10

    results = []
    for bot in bots_data:
        rid = bot['id']
        program = bot['program']
        registers = bot['registers']  # уже копия
        energy = bot['energy']
        max_ticks = bot['max_ticks']

        if phase == 2:
            # Vision — обновление сенсорных регистров
            # В воркере нет доступа к карте, поэтому vision
            # остаётся sequential (на основной синхронизации).
            # Этот phase пока не используется.
            pass

        elif phase == 3:
            # Bot run: записать энергию в регистр и выполнить программу
            registers[REG_ENERGY] = energy
            alive = True

            # Парсинг блоков (упрощённая версия Genome.parse_blocks)
            opened = []
            blocks = {}
            valid = True
            for i, sym in enumerate(program):
                if sym == '[':
                    opened.append(i)
                elif sym == ']':
                    if not opened:
                        valid = False
                        break
                    start = opened.pop()
                    blocks[i] = start
                    blocks[start] = i
            if opened:
                valid = False

            if valid:
                cur_reg = 0
                tick = 0
                i = 0
                while i < len(program) and valid:
                    sym = program[i]
                    if sym == '>':
                        cur_reg = 0 if cur_reg == 23 else cur_reg + 1
                    elif sym == '<':
                        cur_reg = 23 if cur_reg == 0 else cur_reg - 1
                    elif sym == '+':
                        if cur_reg not in UNCHANGABLE:
                            registers[cur_reg] = 0 if registers[cur_reg] == 255 else registers[cur_reg] + 1
                    elif sym == '-':
                        if cur_reg not in UNCHANGABLE:
                            registers[cur_reg] = 255 if registers[cur_reg] == 0 else registers[cur_reg] - 1
                    elif sym == '[':
                        if not registers[cur_reg]:
                            i = blocks[i]
                    elif sym == ']':
                        if registers[cur_reg]:
                            i = blocks[i]
                    i += 1
                    tick += 1
                    if tick > max_ticks:
                        break

            energy = registers[REG_ENERGY]
            if energy <= 0:
                alive = False

        results.append({'id': rid, 'registers': registers, 'energy': energy, 'alive': alive})

    return results


class SimulationService:
    """Оркестратор симуляции (headless - без UI)
    
    Управляет жизненным циклом симуляции:
    - Спавн ботов
    - Обновление vision
    - Выполнение ботов
    - Обработка взаимодействий
    - Периодические обновления (энергия, статистика)
    """
    
    def __init__(self, world, config):
        """
        Args:
            world: экземпляр World
            config: SimulationConfig с параметрами симуляции
        """
        self.world = world
        self.config = config
        self.running = False
        self.top_bots = []  # Топ ботов по возрасту
    
    def tick(self):
        """Один шаг симуляции
        
        Разделено на фазы для будущего мультипроцессинга:
        1. Спавн новых ботов
        2. Обновление vision (READ-ONLY, параллелится)
        3. Выполнение ботов (параллелится!)
        4. Сбор взаимодействий (параллелится)
        5. Применение взаимодействий (последовательно)
        """
        # ФАЗА 1: Спавн новых ботов
        self._spawn_bots_if_needed()
        
        # ФАЗА 2: Обновление vision (можно параллелить)
        for bot in self.world.bots:
            self.world.update_vision_for_bot(bot)
        
        # ФАЗА 3: Выполнение ботов (многоядерно!)
        self._run_bots_parallel()
        
        # ФАЗА 4: Сбор взаимодействий (можно параллелить)
        for bot in self.world.bots:
            self.world.queue_interaction(bot.get_interaction())
        
        # ФАЗА 5: Применение взаимодействий (последовательно!)
        self.world.process_interactions()
        self.world.remove_dead_bots()
        
        # Периодические обновления
        if self.world.tick % 250 == 0:
            self.world.update_cells_energy()
        
        if self.world.tick % 1000 == 0:
            self._update_statistics()
    
    def _run_bots_parallel(self):
        """Запустить ботов через ProcessPoolExecutor"""
        bots = [b for b in self.world.bots if b.alive and b.energy > 0]
        if not bots:
            return

        # Порог: если ботов мало, параллельность не окупается
        PARALLEL_THRESHOLD = 50
        if len(bots) < PARALLEL_THRESHOLD:
            for bot in bots:
                bot.run()
            return

        num_workers = multiprocessing.cpu_count()

        # Сериализация состояния ботов для воркеров
        bot_dicts = [{
            'id': bot.id,
            'program': bot.genome.program,  # shared (read-only, строки иммутабельны)
            'registers': bot.genome.registers[:],  # копия
            'energy': bot.energy,
            'max_ticks': bot.genome.max_ticks,
        } for bot in bots]

        chunk_size = max(1, len(bot_dicts) // (num_workers * 2))  # 2x workers для лучшей загрузки
        chunks = [bot_dicts[i:i+chunk_size] for i in range(0, len(bot_dicts), chunk_size)]

        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(_execute_bot_chunk, chunk, 3) for chunk in chunks]

            # Собрать результаты
            id_to_bot = {bot.id: bot for bot in bots}
            for future in as_completed(futures):
                for result in future.result():
                    bot = id_to_bot.get(result['id'])
                    if bot:
                        bot.genome.registers[:] = result['registers']  # in-place update
                        bot.energy = result['energy']
                        bot.alive = result['alive']
                        bot.age += 1

    def _spawn_bots_if_needed(self):
        """Спавн новых ботов если их слишком мало"""
        min_bots = round(self.world.width * self.world.height / 100 * self.config.world.spawn_rate)
        current = len(self.world.bots)
        if current >= min_bots:
            return
        max_attempts = self.config.world.spawn_rate * 100
        for _ in range(max_attempts):
            if len(self.world.bots) >= min_bots:
                break
            bot = Bot(config=self.world.genome_config)
            if bot.alive:
                self.world.spawn(bot)
    
    def _update_statistics(self):
        """Обновить и залогировать статистику"""
        if self.top_bots:
            self.top_bots = sorted(self.world.bots + self.top_bots, key=lambda b: b.age, reverse=True)[:20]
        else:
            self.top_bots = sorted(self.world.bots, key=lambda b: b.age, reverse=True)[:20]
        
        text = ""
        for bot in self.top_bots:
            text += f"Age:{bot.age} program:{bot.genome.program}\n"
        
        logger.info("Top 20 bots:\n" + text)
    
    def run(self, max_ticks=None):
        """Запуск симуляции
        
        Args:
            max_ticks: максимальное количество тиков (None = бесконечно)
        """
        self.running = True
        ticks = 0
        
        logger.info("Starting simulation")
        
        while self.running:
            self.tick()
            ticks += 1
            
            if max_ticks and ticks >= max_ticks:
                break
        
        logger.info(f"Simulation ended after {ticks} ticks")
    
    def stop(self):
        """Остановка симуляции"""
        self.running = False
        logger.info("Simulation stop requested")
