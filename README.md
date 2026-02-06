# replicants-py - Life Simulation

Artificial life simulation featuring evolving bots with genomes expressed as programs in a dialect of the Brainfuck language.

[![English](https://img.shields.io/badge/lang-English-blue.svg)](README.md)
[![Русский](https://img.shields.io/badge/lang-Русский-red.svg)](README_ru.md)

## Project Structure

```
replicants-py/
├── core/                  # Simulation core (domain logic)
│   ├── bot.py            # Bots and genomes
│   ├── world.py          # Simulation world
│   ├── world_map.py      # Map and cells
│   └── interaction.py    # Interaction types
├── interactions/          # Interaction handlers (strategy pattern)
│   ├── handlers.py       # 8 interaction types
│   └── utils.py          # Utilities
├── services/              # Application services
│   ├── simulation_service.py   # Simulation orchestrator
│   └── state_provider.py       # State query API
├── persistence/           # Save/load functionality
│   └── serializer.py     # JSON serialization
├── config/                # Configuration
│   └── settings.py       # Simulation parameters
├── renderers/             # Renderers (UI)
│   └── console_renderer.py     # ASCII terminal renderer
├── example_headless.py   # Headless simulation (no UI)
└── example_console.py    # Simulation with console renderer
```

## Installation

```bash
python3 -m pip install -r requirements.txt
```

**Dependencies:**
- configargparse - configuration parsing

## Usage

### Console Renderer

```bash
python3 example_console.py --width 20 --height 20
```

### Headless Mode (no UI)

```bash
python3 example_headless.py --width 40 --height 40
```

### Command-line Options

```bash
python3 example_console.py --help
```

**Key parameters:**

- `--width N`, `--height N` - world dimensions
- `--mutation_rate F` - mutation frequency (default: 0.01)
- `--program_length N` - bot genome length (default: 64)
- `--spawn_rate N` - world bot population percentage (default: 10)
- `--save_file PATH` - save/load file path (default: ./default.save)
- `--log_level LEVEL` - logging level (INFO, DEBUG, WARNING)
- `--config FILE` - path to INI configuration file

## Features

### Save/Load System

World state is automatically saved on exit and loaded on startup:

```bash
python3 example_console.py --save_file my_world.save
```

**Save format:**
- JSON
- Full state preservation: bots, map, energy levels, genomes

### Interaction System

Bots can perform 6+ interaction types:
- Movement
- Division (reproduction)
- Energy transfer
- Energy harvesting from cells
- Information sending to other bots
- Position swapping with another bot

Easily extensible by adding new handlers in `interactions/handlers.py`.

### Bot Genomes

Bots possess programs (genomes) in a Brainfuck-like language:
- `+`, `-` - increment/decrement register
- `>`, `<` - move between registers
- `[`, `]` - loops

Input/output commands (`.` and `,`) are omitted; instead, register values are read directly during simulation execution.

Mutations currently occur during reproduction, with evolution driven by natural selection.

### StateProvider API

Create custom renderers using the StateProvider interface:

```python
from services.state_provider import StateProvider

provider = StateProvider(world)
state = provider.get_world_state()  # Full world state
stats = provider.get_statistics()   # Aggregate statistics
bot_info = provider.get_bot_info(bot_id)  # Specific bot details
```

## Roadmap

### Implemented
- Headless architecture (simulation as a microservice)
- Console ASCII renderer
- StateProvider API for renderers
- Modular interaction handling system
- Compact serialization (single-line program representation)
- Multiprocessing preparation (phased tick execution)

### Planned
- WebSocket server for web-based rendering
- Multiprocessor bot processing
- Additional entity types
- Increased world variability
- Artificial evolution mechanisms (selective breeding)

## Development

### Adding a New Interaction Type

1. Create a handler in `interactions/handlers.py`:

```python
def handle_new_interaction(world, interaction):
    # Your logic here
    pass
```

2. Register it in the HANDLERS dictionary:

```python
HANDLERS = {
    ...
    9: handle_new_interaction,
}
```

### Creating a Custom Renderer

1. Implement a class in `renderers/`:

```python
class MyRenderer:
    def __init__(self, state_provider):
        self.state_provider = state_provider
    
    def render(self):
        state = self.state_provider.get_world_state()
        # Your rendering logic
```

2. Integrate in your main script:

```python
service = SimulationService(world, config)
provider = StateProvider(world)
renderer = MyRenderer(provider)

while True:
    service.tick()
    renderer.render()
```

## License

**GPLv3**