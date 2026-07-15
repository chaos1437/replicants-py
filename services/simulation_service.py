"""Сервис симуляции - headless оркестратор"""
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

from core.bot import Bot, Genome
from core.interaction import Interaction

logger = logging.getLogger(__name__)


def _execute_chunk(bots_data: list[dict],
                   map_flat: bytes,
                   map_width: int,
                   map_height: int) -> list[dict]:
    """Один parallel проход: vision + execute + сбор взаимодействия.

    bots_data: list of dicts with id, opcodes, jumps, registers, energy, max_ticks, x, y
    map_flat: bytes length=width*height, 0=empty, 1=occupied
    map_width, map_height: размеры карты

    Returns: list of dicts с id, registers, energy, alive, interaction|None
    """
    REG_ENERGY = 10
    results = []

    for bot in bots_data:
        rid = bot['id']
        regs = bot['registers']
        x, y = bot['x'], bot['y']

        # ═══ VISION ═══
        for dx, dy, reg in Genome.SENSOR_REGISTERS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < map_width and 0 <= ny < map_height:
                state = map_flat[ny * map_width + nx]
            else:
                state = 2  # world_border
            regs[reg] = state

        # ═══ EXECUTE ═══
        regs[REG_ENERGY] = bot['energy']
        Genome.execute(bot['opcodes'], bot['jumps'], regs, bot['max_ticks'])
        energy = regs[REG_ENERGY]
        alive = energy > 0

        # ═══ INTERACTION ═══
        interaction = None
        if alive:
            # direction из registers[0:4]
            max_val = 0
            max_idx = -1
            for i in range(5):
                if regs[i] > max_val:
                    max_val = regs[i]
                    max_idx = i
            direction = max_idx if max_val > 0 else -1

            interaction = {
                'type': regs[Genome.REG_INTERACTION_TYPE],
                'strength': regs[Genome.REG_INTERACTION_STRENGTH],
                'direction': direction,
            }

        results.append({
            'id': rid,
            'registers': regs,
            'energy': energy,
            'alive': alive,
            'interaction': interaction,
        })

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
        self._executor = ProcessPoolExecutor(max_workers=multiprocessing.cpu_count())
    
    def tick(self):
        """Один шаг симуляции
        
        1. Спавн новых ботов
        2. Vision + execute + сбор взаимодействий (параллельно!)
        3. Применение взаимодействий (последовательно)
        """
        self._spawn_bots_if_needed()
        self._run_bots_parallel()
        self.world.process_interactions()
        self.world.remove_dead_bots()

        if self.world.tick % 250 == 0:
            self.world.update_cells_energy()

        if self.world.tick % 1000 == 0:
            self._update_statistics()
    
    def _run_bots_parallel(self):
        """Запустить ботов: vision + execute + сбор взаимодействий (параллельно)."""
        bots = [b for b in self.world.bots if b.alive and b.energy > 0]
        if not bots:
            return

        PARALLEL_THRESHOLD = 50
        if len(bots) < PARALLEL_THRESHOLD:
            # Sequential fallback — один проход вместо трёх
            for bot in bots:
                self.world.update_vision_for_bot(bot)
                bot.run()
                self.world.queue_interaction(bot.get_interaction())
            return

        num_workers = multiprocessing.cpu_count()
        w, h = self.world.width, self.world.height

        # Слепок карты для vision (0=empty, 1=occupied)
        map_flat = bytearray(w * h)
        for y in range(h):
            for x in range(w):
                cell = self.world.map.get_cell(x, y)
                map_flat[y * w + x] = 1 if cell.contains else 0

        # Сериализация ботов для воркеров (с x,y для vision)
        bot_dicts = [{
            'id': bot.id,
            'opcodes': bot.genome.opcodes,
            'jumps': bot.genome.jumps,
            'registers': bot.genome.registers[:],
            'energy': bot.energy,
            'max_ticks': bot.genome.max_ticks,
            'x': bot.x,
            'y': bot.y,
        } for bot in bots]

        chunk_size = max(1, len(bot_dicts) // (num_workers * 2))
        chunks = [bot_dicts[i:i+chunk_size] for i in range(0, len(bot_dicts), chunk_size)]

        futures = [self._executor.submit(
            _execute_chunk, ch, bytes(map_flat), w, h) for ch in chunks]

        # Собрать результаты
        id_to_bot = {bot.id: bot for bot in bots}
        for future in as_completed(futures):
            for result in future.result():
                bot = id_to_bot.get(result['id'])
                if bot:
                    bot.genome.registers[:] = result['registers']
                    bot.energy = result['energy']
                    bot.alive = result['alive']
                    bot.age += 1
                    if result['interaction']:
                        interaction = result['interaction']
                        self.world.queue_interaction(
                            Interaction(bot,
                                       interaction['direction'],
                                       interaction['type'],
                                       interaction['strength']))

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
        self._executor.shutdown(wait=False)
        logger.info("Simulation stop requested")

    def __del__(self):
        self._executor.shutdown(wait=False)
