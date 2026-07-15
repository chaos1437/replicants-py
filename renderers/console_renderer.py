"""Простой консольный рендер для симуляции"""
import sys


class ConsoleRenderer:
    """Простой ASCII рендер для терминала"""
    
    def __init__(self, state_provider):
        """
        Args:
            state_provider: экземпляр StateProvider для получения состояния
        """
        self.state_provider = state_provider
    
    def clear_screen(self):
        """Очистить экран (ANSI escape — без форка процесса)"""
        sys.stdout.write('\033[2J\033[H')
        sys.stdout.flush()
    
    def render(self):
        """Отрисовать текущее состояние мира"""
        self.clear_screen()
        
        # Получаем состояние через StateProvider
        state = self.state_provider.get_world_state()
        stats = self.state_provider.get_statistics()
        
        width = state['width']
        height = state['height']
        
        # Статистика
        print(f"╔{'═' * (width * 2 + 2)}╗")
        print(f"║ Tick: {stats['tick']:<6} Bots: {stats['total_bots']:<4} Alive: {stats['alive_bots']:<4} ║")
        print(f"║ Avg Age: {stats['average_age']:<6.1f} Avg Energy: {stats['average_energy']:<6.1f}        ║")
        print(f"╠{'═' * (width * 2 + 2)}╣")
        
        # Создаем карту ботов для быстрого поиска
        bot_map = {}
        for bot in state['bots']:
            bot_map[(bot['x'], bot['y'])] = bot
        
        # Карта (отрисовываем сверху вниз)
        for y in range(height - 1, -1, -1):
            line = "║ "
            for x in range(width):
                if (x, y) in bot_map:
                    # Отображаем бота
                    energy = bot_map[(x, y)]['energy']
                    if energy > 200:
                        symbol = "█"  # Полная энергия
                    elif energy > 100:
                        symbol = "▓"  # Высокая энергия
                    elif energy > 50:
                        symbol = "▒"  # Средняя энергия
                    else:
                        symbol = "░"  # Низкая энергия
                else:
                    # Отображаем энергию ячейки
                    cell_energy = state['cells'][y][x]['energy']
                    if cell_energy > 150:
                        symbol = "·"  # Высокая энергия ячейки
                    elif cell_energy > 50:
                        symbol = "."  # Средняя энергия
                    else:
                        symbol = " "  # Низкая энергия
                
                line += symbol + " "
            line += "║"
            print(line)
        
        print(f"╚{'═' * (width * 2 + 2)}╝")
        print("Легенда: █▓▒░ = боты (энергия), · . = энергия ячеек")
        print("Ctrl+C для выхода")
        
        sys.stdout.flush()
