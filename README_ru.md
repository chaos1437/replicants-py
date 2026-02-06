# replicants-py - Life Simulation

Симуляция искусственной жизни с эволюционирующими ботами, обладающими геномами в виде программ на диалекте языка brainfuck.

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md)
[![Русский](https://img.shields.io/badge/lang-Русский-red.svg)](README_ru.md)

## Структура проекта

```
replicants-py/
├── core/                  # Ядро симуляции (domain logic)
│   ├── bot.py            # Боты и геномы
│   ├── world.py          # Мир симуляции
│   ├── world_map.py      # Карта и ячейки
│   └── interaction.py    # Типы взаимодействий
├── interactions/          # Обработчики взаимодействий (стратегии)
│   ├── handlers.py       # 8 типов взаимодействий
│   └── utils.py          # Утилиты
├── services/              # Сервисы приложения
│   ├── simulation_service.py   # Оркестратор симуляции
│   └── state_provider.py       # API для получения состояния
├── persistence/           # Сохранение/загрузка
│   └── serializer.py     # JSON сериализация
├── config/                # Конфигурация
│   └── settings.py       # Параметры симуляции
├── renderers/             # Рендеры (UI)
│   └── console_renderer.py     # ASCII рендер для терминала
├── example_headless.py   # Headless симуляция (без UI)
└── example_console.py    # Симуляция с консольным рендером
```

## Установка

```bash
python3 -m pip install -r requirements.txt
```

**Зависимости:**
- configargparse - парсинг конфигурации

## Запуск

### Консольный рендер

```bash
python3 example_console.py --width 20 --height 20
```

### Headless режим (без UI)

```bash
python3 example_headless.py --width 40 --height 40
```

### Параметры командной строки

```bash
python3 example_console.py --help
```

**Основные параметры:**

- `--width N`, `--height N` - размер мира
- `--mutation_rate F` - частота мутаций (по умолчанию 0.01)
- `--program_length N` - длина генома бота (по умолчанию 64)
- `--spawn_rate N` - процент заполнения мира ботами (по умолчанию 10)
- `--save_file PATH` - файл для сохранения/загрузки (по умолчанию ./default.save)
- `--log_level LEVEL` - уровень логирования (INFO, DEBUG, WARNING)
- `--config FILE` - путь к INI файлу конфигурации

## Особенности

### Сохранение/загрузка

Состояние мира автоматически сохраняется при выходе и загружается при запуске:

```bash
python3 example_console.py --save_file my_world.save
```

**Формат сохранения:**
- JSON
- Сохраняется полное состояние: боты, карта, энергия, геномы

### Система взаимодействий

Боты могут выполнять 6+ типов взаимодействий:
- Перемещение
- Деление (размножение)
- Передача энергии
- Получение энергии из ячеек
- Отправка информации другим ботам
- Замена позиции с другим ботом

Легко расширяется добавлением новых handlers в `interactions/handlers.py`

### Геномы ботов

Боты имеют программы (геномы) на языке, похожем на brainfuck:
- `+`, `-` - инкремент/декремент регистра
- `>`, `<` - переход между регистрами
- `[`, `]` - циклы
Отсутствуют только команды ввода и вывода (. и ,) , вместо них в данном случае происходит прямое чтение значений из регистров во время симуляции.

На данный момент в реализации мутации происходят при размножении, эволюция происходит естественным отбором.

### StateProvider API

Для создания собственных рендеров используйте StateProvider:

```python
from services.state_provider import StateProvider

provider = StateProvider(world)
state = provider.get_world_state()  # Полное состояние
stats = provider.get_statistics()   # Статистика
bot_info = provider.get_bot_info(bot_id)  # Инфо о конкретном боте
```

## Roadmap

### Реализовано
- Headless архитектура (симуляция как микросервис)
- Консольный ASCII рендер
- StateProvider API для рендеров
- Модульная система обработки взаимодействий
- Компактное сохранение (program в одну строку)
- Подготовка к мультипроцессингу (фазы в tick)

### В планах
- WebSocket сервер для веб-рендера
- Мультипроцессорная обработка ботов
- Дополнительные типы сущностей
- Больше вариативности в мире
- Искусственная эволюция ботов (селекция)

## Разработка

### Добавление нового типа взаимодействия

1. Создать handler в `interactions/handlers.py`:

```python
def handle_new_interaction(world, interaction):
    # Ваша логика
    pass
```

2. Добавить в словарь HANDLERS:

```python
HANDLERS = {
    ...
    9: handle_new_interaction,
}
```

### Создание нового рендера

1. Создать класс в `renderers/`:

```python
class MyRenderer:
    def __init__(self, state_provider):
        self.state_provider = state_provider
    
    def render(self):
        state = self.state_provider.get_world_state()
        # Ваша отрисовка
```

2. Использовать в main файле:

```python
service = SimulationService(world, config)
provider = StateProvider(world)
renderer = MyRenderer(provider)

while True:
    service.tick()
    renderer.render()
```

## Лицензия

 **GPLv3**
