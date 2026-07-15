"""Бенчмарки производительности симуляции

Запуск:
    python -m pytest tests/benchmark_simulation.py -v --benchmark-only
    python tests/benchmark_simulation.py  # прямой запуск
"""
import time
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.bot import Bot, Genome
from core.world_map import WorldMap
from core.world import World
from core.interaction import Interaction
from config.settings import GenomeConfig, WorldConfig, SimulationConfig
from services.simulation_service import SimulationService


def benchmark_bot_execution(bot_count: int, program_length: int = 128, ticks: int = 100):
    """Замерить время выполнения ticks тиков для N ботов"""
    config = GenomeConfig(
        mutation_rate=0.01,
        program_length=program_length,
        max_ticks=204800
    )
    world_map = WorldMap(100, 100)
    world = World(world_map)
    world.genome_config = config
    
    sim_config = SimulationConfig(
        genome=config,
        world=WorldConfig(width=100, height=100),
        save_file="/tmp/benchmark_save.json",
        max_ticks=ticks
    )
    
    # Создать ботов
    spawned = 0
    attempts = 0
    while spawned < bot_count and attempts < bot_count * 10:
        bot = Bot(config=config)
        if bot.alive and world.spawn(bot):
            spawned += 1
        attempts += 1
    
    service = SimulationService(world, sim_config)
    
    # Прогрев
    for _ in range(10):
        service.tick()
    
    # Замер
    start = time.perf_counter()
    for _ in range(ticks):
        service.tick()
    elapsed = time.perf_counter() - start
    
    return {
        'bot_count': len(world.bots),
        'ticks': ticks,
        'elapsed': elapsed,
        'ticks_per_sec': ticks / elapsed if elapsed > 0 else 0,
        'bots_per_sec': len(world.bots) * ticks / elapsed if elapsed > 0 else 0,
        'program_length': program_length,
    }


def benchmark_genome_execute():
    """Замерить время выполнения Genome.execute для разных программ"""
    config = GenomeConfig(program_length=64, max_ticks=204800)
    
    programs = {
        'arithmetic': ['+'] * 255 + ['-'] * 255,
        'loop_simple': ['[', '+', ']'],
        'loop_nested': ['[', '[', '+', ']', ']'],
        'mixed': ['+', '>', '+', '>', '+', '<', '<', '-'] * 32,
        'long_program': (['+'] * 100 + ['-'] * 100 + ['>', '<']) * 50,
    }
    
    results = {}
    for name, program in programs.items():
        genome = Genome(config)
        genome.program = program
        compiled = Genome.compile_program(genome.program)
        if compiled:
            genome.opcodes, genome.jumps = compiled
        
        # Прогрев
        for _ in range(100):
            Genome.execute(genome.opcodes, genome.jumps, genome.registers, genome.max_ticks)
        
        # Замер
        trials = 1000
        start = time.perf_counter()
        for _ in range(trials):
            genome.registers = bytearray(24)
            Genome.execute(genome.opcodes, genome.jumps, genome.registers, genome.max_ticks)
        elapsed = time.perf_counter() - start
        
        results[name] = {
            'program_length': len(program),
            'trials': trials,
            'elapsed': elapsed,
            'avg_ms': elapsed / trials * 1000,
            'exec_per_sec': trials / elapsed if elapsed > 0 else 0,
        }
    
    return results


def benchmark_tick_phases(bot_count: int = 200):
    """Замерить время каждой фазы tick()"""
    config = GenomeConfig(mutation_rate=0.01, program_length=64, max_ticks=2048)
    world_map = WorldMap(50, 50)
    world = World(world_map)
    world.genome_config = config
    sim_config = SimulationConfig(
        genome=config, world=WorldConfig(width=50, height=50),
        save_file="/tmp/bench.json", max_ticks=50
    )
    
    spawned = 0
    while spawned < bot_count:
        bot = Bot(config=config)
        if bot.alive and world.spawn(bot):
            spawned += 1
    
    service = SimulationService(world, sim_config)
    
    # Прогрев
    for _ in range(5):
        service.tick()
    
    phases = {'spawn': 0, 'serialize': 0, 'parallel_run': 0,
               'apply_results': 0, 'process': 0, 'remove': 0}
    iterations = 20
    
    for _ in range(iterations):
        t0 = time.perf_counter()
        service._spawn_bots_if_needed()
        phases['spawn'] += time.perf_counter() - t0
        
        # Измеряем _run_bots_parallel детально (без доступа кнутри — через профилирование)
        t0 = time.perf_counter()
        service._run_bots_parallel()
        phases['parallel_run'] += time.perf_counter() - t0
        
        t0 = time.perf_counter()
        service.world.process_interactions()
        phases['process'] += time.perf_counter() - t0
        
        t0 = time.perf_counter()
        service.world.remove_dead_bots()
        phases['remove'] += time.perf_counter() - t0
    
    # Нормализовать
    for k in phases:
        phases[k] /= iterations
    
    total = sum(phases.values())
    phases['total'] = total
    phases['total_per_tick_ms'] = total * 1000
    
    return phases


def print_results(title, results):
    """Форматированный вывод результатов"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")
    
    if isinstance(results, dict):
        if 'bot_count' in results:
            r = results
            print(f"  Ботов: {r['bot_count']}, Тиков: {r['ticks']}")
            print(f"  Время: {r['elapsed']:.3f}s")
            print(f"  Тиков/сек: {r['ticks_per_sec']:.1f}")
            print(f"  Ботов*тиков/сек: {r['bots_per_sec']:.0f}")
        elif 'avg_ms' in results:
            for name, r in results.items():
                if isinstance(r, dict) and 'avg_ms' in r:
                    print(f"  {name:20s}  len={r['program_length']:<6d}  "
                          f"{r['avg_ms']:.4f}ms  ({r['exec_per_sec']:.0f} exec/s)")
        else:
            for k, v in results.items():
                if k == 'total':
                    continue
                pct = v / results.get('total', 1) * 100 if results.get('total', 0) > 0 else 0
                print(f"  {k:12s}  {v*1000:.3f}ms  ({pct:.1f}%)")
            if 'total' in results:
                print(f"  {'─'*35}")
                print(f"  {'total':12s}  {results['total']*1000:.3f}ms")


if __name__ == '__main__':
    print("=" * 60)
    print("  БЕНЧМАРКИ СИМУЛЯЦИИ REPLICANTS")
    print("=" * 60)
    
    # 1. Genome.execute
    print("\n>>> 1. Genome.execute по типам программ")
    exec_results = benchmark_genome_execute()
    for name, r in exec_results.items():
        print(f"  {name:20s}  len={r['program_length']:<6d}  "
              f"{r['avg_ms']:.4f}ms  ({r['exec_per_sec']:.0f} exec/s)")
    
    # 2. Tick по фазам
    print("\n>>> 2. Фазы tick() (200 ботов, 50x50)")
    phases = benchmark_tick_phases(200)
    total = phases.pop('total')
    for k, v in phases.items():
        pct = v / total * 100
        print(f"  {k:12s}  {v*1000:.3f}ms  ({pct:.1f}%)")
    print(f"  {'─'*35}")
    print(f"  {'total':12s}  {total*1000:.3f}ms")
    
    # 3. Масштабирование по числу ботов
    print("\n>>> 3. Масштабирование (100×100, 50 ticks, program_length=64)")
    print(f"  {'Ботов':>8s}  {'Тиков/с':>10s}  {'Бот*тик/с':>12s}  {'Время':>8s}")
    print(f"  {'─'*8}  {'─'*10}  {'─'*12}  {'─'*8}")
    for n in [50, 100, 200, 500, 1000]:
        r = benchmark_bot_execution(n, program_length=64, ticks=30)
        print(f"  {r['bot_count']:>8d}  {r['ticks_per_sec']:>10.1f}  "
              f"{r['bots_per_sec']:>12.0f}  {r['elapsed']:>8.3f}s")
