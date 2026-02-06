"""Конфигурация симуляции"""
from dataclasses import dataclass
from pathlib import Path
import configargparse


@dataclass
class GenomeConfig:
    """Конфигурация генома ботов"""
    mutation_rate: float = 0.01
    program_length: int = 64
    max_ticks: int = 512


@dataclass
class WorldConfig:
    """Конфигурация мира"""
    width: int = 40
    height: int = 40
    spawn_rate: int = 10
    energy_boost: int = 50


@dataclass
class SimulationConfig:
    """Общая конфигурация симуляции"""
    genome: GenomeConfig
    world: WorldConfig
    save_file: Path
    log_level: str = "INFO"
    log_file: str = ""
    wait_time: float = 0.0
    max_ticks: int = None  # None = бесконечно


def load_config() -> SimulationConfig:
    """Загрузка конфигурации из командной строки и файла"""
    parser = configargparse.ArgParser(
        description="Simulation parameters",
        default_config_files=["simulation_settings.ini"]
    )
    
    parser.add('-c', '--config', is_config_file=True, help='Path to the configuration file')
    
    # World parameters
    parser.add('--width', type=int, default=40, help='Width of the world in cells')
    parser.add('--height', type=int, default=40, help='Height of the world in cells')
    parser.add('-sr', '--spawn_rate', type=int, default=10, 
               help="Minimal %% of cells that should be filled with bots")
    
    # Genome parameters
    parser.add('-mr', '--mutation_rate', type=float, default=0.01, 
               help='Mutation rate for bot genomes')
    parser.add('-pl', '--program_length', type=int, default=64, 
               help='Length of the bot program(genome)')
    parser.add('-mt', '--max_ticks', type=int, default=512, 
               help='Maximum number of command executions for 1 bot run per world tick')
    
    # Simulation parameters
    parser.add('-log', '--log_level', type=str, default="INFO", 
               choices=["INFO", "DEBUG", "WARNING", "CRITICAL"], help='Log level')
    parser.add("--log_file", type=str, default="", help='Path to the log file')
    parser.add('-s', '--save_file', type=str, default="./default.save", 
               help='File to save and load the world state')
    parser.add('-wt', '--wait_time', type=float, default=0, 
               help='Time in seconds to wait between ticks')
    
    # UI parameters (для pygame)
    parser.add('-cs', '--cell_size', type=int, default=10, help='Size of each cell in pixels')
    
    args = parser.parse_args()
    
    genome_config = GenomeConfig(
        mutation_rate=args.mutation_rate,
        program_length=args.program_length,
        max_ticks=args.max_ticks
    )
    
    world_config = WorldConfig(
        width=args.width,
        height=args.height,
        spawn_rate=args.spawn_rate
    )
    
    return SimulationConfig(
        genome=genome_config,
        world=world_config,
        save_file=Path(args.save_file),
        log_level=args.log_level,
        log_file=args.log_file,
        wait_time=args.wait_time
    ), args
