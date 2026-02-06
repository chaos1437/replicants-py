"""Обработчики взаимодействий ботов

Каждый тип взаимодействия обрабатывается отдельной функцией.
Это позволяет легко добавлять новые типы (OCP) и тестировать каждый отдельно.
"""
import logging
from interactions.utils import get_estimated_coords

logger = logging.getLogger(__name__)


def handle_spawn(world, interaction):
    """Тип -2: Появление бота"""
    world.spawn(interaction.bot)
    interaction.bot.genome.registers[11] = 0


def handle_death(world, interaction):
    """Тип -1: Смерть бота"""
    world.remove_bot(interaction.bot)


def handle_move(world, interaction):
    """Тип 0: Перемещение"""
    if interaction.bot.direction == 4:  # stay
        cell = world.map.get_cell(interaction.bot.x, interaction.bot.y)
        world.bot_energy_draining(interaction.bot, cell)
    
    elif interaction.direction == -1:
        pass  # нет направления
    
    else:
        estimated_x, estimated_y = get_estimated_coords(interaction)
        if world.map.get_cell(estimated_x, estimated_y):
            world.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)


def handle_replace(world, interaction):
    """Тип 1: Замена другого бота ИЛИ перемещение"""
    if interaction.direction == 4:
        cell = world.map.get_cell(interaction.bot.x, interaction.bot.y)
        world.bot_energy_draining(interaction.bot, cell)
    
    elif interaction.direction == -1:
        pass
    
    else:
        estimated_x, estimated_y = get_estimated_coords(interaction)
        target_cell = world.map.get_cell(estimated_x, estimated_y)
        
        if target_cell:
            # Заменить бота или переместиться в пустую ячейку
            world.map.move(interaction.bot.x, interaction.bot.y, estimated_x, estimated_y)


def handle_push_energy(world, interaction):
    """Тип 2: Отдать энергию в ячейку"""
    if interaction.direction != 4:
        estimated_x, estimated_y = get_estimated_coords(interaction)
        cell = world.map.get_cell(estimated_x, estimated_y)
        if cell:
            world.bot_push_energy(interaction.bot, cell, interaction.strength)


def handle_get_energy(world, interaction):
    """Тип 3: Получить энергию из соседней ячейки"""
    estimated_x, estimated_y = get_estimated_coords(interaction)
    cell = world.map.get_cell(estimated_x, estimated_y)
    if cell:
        world.bot_energy_draining(interaction.bot, cell)


def handle_send_info(world, interaction):
    """Тип 4: Отправить информацию другому боту"""
    if interaction.direction != 4:
        estimated_x, estimated_y = get_estimated_coords(interaction)
        target_cell = world.map.get_cell(estimated_x, estimated_y)
        if target_cell and target_cell.contains:
            # Отправить регистр 13 в регистр 9 целевого бота
            target_cell.contains.genome.registers[9] = interaction.bot.genome.registers[13]


def handle_divide(world, interaction):
    """Тип 6+: Деление (создание потомка)"""
    if interaction.direction != 4:
        estimated_x, estimated_y = get_estimated_coords(interaction)
        cell = world.map.get_cell(estimated_x, estimated_y)
        if cell and cell.contains is None:
            new_bot = interaction.bot.divide()
            if new_bot:
                cell.set(new_bot)
                world.bots.append(new_bot)


# Словарь обработчиков: тип взаимодействия -> функция
HANDLERS = {
    -2: handle_spawn,
    -1: handle_death,
    0: handle_move,
    1: handle_replace,
    2: handle_push_energy,
    3: handle_get_energy,
    4: handle_send_info,
    # 5 не нужен (обрабатывается в 4)
}


def get_handler(interaction_type: int):
    """Получить обработчик для типа взаимодействия"""
    if interaction_type >= 6:
        return handle_divide
    return HANDLERS.get(interaction_type)


def execute_interaction(world, interaction):
    """Выполнить взаимодействие через соответствующий обработчик
    
    Это главная функция диспетчеризации, которая заменяет
    большой match/case из старого кода.
    """
    handler = get_handler(interaction.type)
    if handler:
        handler(world, interaction)
    
    # Общая логика для всех взаимодействий
    interaction.bot.energy -= 1
    if interaction.bot.energy <= 0:
        world.remove_bot(interaction.bot)
