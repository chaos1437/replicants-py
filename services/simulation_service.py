"""Сервис симуляции - headless оркестратор"""
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
from multiprocessing import shared_memory

from core.bot import Bot, Genome
from core.interaction import Interaction

logger = logging.getLogger(__name__)


def _execute_chunk_shm(bot_meta: list[dict],
                        map_flat: bytes,
                        map_width: int,
                        map_height: int,
                        programs: dict[int, tuple],
                        shm_name: str) -> list[dict]:
    """Parallel проход через shared memory — zero-copy registers.

    bot_meta: [{idx, prog_id, max_ticks, x, y}, ...]
        idx — индекс бота в shared memory (offset = idx * 24)
    map_flat, map_width, map_height — карта для vision
    programs: {prog_id: (opcodes, jumps)}
    shm_name: имя SharedMemory-блока

    Returns: [{idx, alive, interaction|None}, ...]
        registers и energy не возвращаются — они уже в shm
    """
    REG_ENERGY = 10

    # Присоединиться к shared memory
    shm = shared_memory.SharedMemory(name=shm_name)
    buf = shm.buf  # memoryview

    results = []
    for bot in bot_meta:
        idx = bot['idx']
        offset = idx * 24
        regs = buf[offset:offset + 24]  # memoryview slice
        x, y = bot['x'], bot['y']
        opcodes, jumps = programs[bot['prog_id']]

        # ═══ VISION ═══
        for dx, dy, reg in Genome.SENSOR_REGISTERS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < map_width and 0 <= ny < map_height:
                state = map_flat[ny * map_width + nx]
            else:
                state = 2
            regs[reg] = state

        # ═══ EXECUTE ═══
        # regs[REG_ENERGY] уже установлен главным процессом перед отправкой
        Genome.execute(opcodes, jumps, regs, bot['max_ticks'])
        energy = regs[REG_ENERGY]
        alive = energy > 0

        # ═══ INTERACTION ═══
        interaction = None
        if alive:
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
            'idx': idx,
            'alive': alive,
            'interaction': interaction,
        })

    del regs
    buf.release()
    shm.close()
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

        # Shared memory для регистров ботов — zero-copy между процессами
        # Layout: 24 байта на бота (bot_idx * 24)
        # Максимум ботов = вся карта
        max_bots = world.width * world.height
        self._shm_regs = shared_memory.SharedMemory(
            create=True,
            size=max_bots * 24,
        )
        self._shm_name = self._shm_regs.name
    
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
        """Запустить ботов: vision + execute + сбор взаимодействий (параллельно).

        Использует shared memory для zero-copy регистров между процессами.
        """
        bots = [b for b in self.world.bots if b.alive and b.energy > 0]
        if not bots:
            return

        PARALLEL_THRESHOLD = 50
        if len(bots) < PARALLEL_THRESHOLD:
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

        # Дедупликация opcodes/jumps
        prog_to_pid = {}
        program_table = []
        for bot in bots:
            prog = bot.genome.opcodes
            if prog not in prog_to_pid:
                prog_to_pid[prog] = len(program_table)
                program_table.append((prog, bot.genome.jumps))

        # Запись регистров в shared memory + мета-данные ботов
        bot_meta = []
        for idx, bot in enumerate(bots):
            offset = idx * 24
            # Копируем текущие регистры в shm (24 байта)
            self._shm_regs.buf[offset:offset + 24] = bot.genome.registers
            # Устанавливаем энергию в регистр REG_ENERGY
            self._shm_regs.buf[offset + Genome.REG_ENERGY] = bot.energy

            bot_meta.append({
                'idx': idx,
                'prog_id': prog_to_pid[bot.genome.opcodes],
                'max_ticks': bot.genome.max_ticks,
                'x': bot.x,
                'y': bot.y,
            })

        # Чанкование и отправка
        chunk_size = max(1, len(bot_meta) // (num_workers * 2))
        chunks = [bot_meta[i:i+chunk_size] for i in range(0, len(bot_meta), chunk_size)]

        futures = []
        for ch in chunks:
            used_ids = set(b['prog_id'] for b in ch)
            chunk_progs = {pid: program_table[pid] for pid in used_ids}
            futures.append(self._executor.submit(
                _execute_chunk_shm, ch, bytes(map_flat), w, h, chunk_progs,
                self._shm_name))

        # Сбор результатов — registers уже в shm, читаем напрямую
        for future in as_completed(futures):
            for result in future.result():
                idx = result['idx']
                bot = bots[idx]
                offset = idx * 24
                # Читаем энергию из shared memory
                bot.energy = self._shm_regs.buf[offset + Genome.REG_ENERGY]
                # Копируем registers обратно в объект Bot
                bot.genome.registers[:] = self._shm_regs.buf[offset:offset + 24]
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
        self._cleanup_shm()
        logger.info("Simulation stop requested")

    def _cleanup_shm(self):
        """Освободить shared memory"""
        try:
            self._shm_regs.close()
            self._shm_regs.unlink()
        except Exception:
            pass

    def __del__(self):
        try:
            self._executor.shutdown(wait=False)
        except Exception:
            pass
        self._cleanup_shm()
