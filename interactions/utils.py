"""Утилиты для взаимодействий"""


def get_estimated_coords(interaction) -> tuple[int, int]:
    """Получить целевые координаты на основе направления взаимодействия"""
    estimated_x, estimated_y = interaction.bot.x, interaction.bot.y
    
    match interaction.direction:
        case 0:  # left
            estimated_x, estimated_y = interaction.bot.x - 1, interaction.bot.y
        case 1:  # up
            estimated_x, estimated_y = interaction.bot.x, interaction.bot.y + 1
        case 2:  # right
            estimated_x, estimated_y = interaction.bot.x + 1, interaction.bot.y
        case 3:  # down
            estimated_x, estimated_y = interaction.bot.x, interaction.bot.y - 1
    
    return estimated_x, estimated_y
