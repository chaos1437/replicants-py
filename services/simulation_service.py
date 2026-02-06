"""Сервис симуляции - headless оркестратор"""
import logging
from core.bot import Bot

logger = logging.getLogger(__name__)


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
        
        # ФАЗА 3: Выполнение ботов (можно параллелить!)
        # Каждый бот работает только со своим состоянием
        for bot in self.world.bots:
            bot.run()
        
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
    
    def _spawn_bots_if_needed(self):
        """Спавн новых ботов если их слишком мало"""
        min_bots = round(self.world.width * self.world.height / 100 * self.config.world.spawn_rate)
        
        if len(self.world.bots) < min_bots:
            for _ in range(self.config.world.spawn_rate * 100):
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
