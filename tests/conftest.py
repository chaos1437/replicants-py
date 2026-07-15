"""Общие фикстуры для тестов"""
import pytest
from core.bot import Bot, Genome
from core.world_map import WorldMap
from core.world import World
from config.settings import GenomeConfig, WorldConfig


@pytest.fixture
def genome_config():
    return GenomeConfig(mutation_rate=0.01, program_length=64, max_ticks=512)


@pytest.fixture
def genome(genome_config):
    return Genome(genome_config)


@pytest.fixture
def valid_program():
    return ["+", "+", "+", "-", ">", "<", "[", "+", "-", "]"]


@pytest.fixture
def bot(genome_config):
    return Bot(config=genome_config)


@pytest.fixture
def world_map():
    return WorldMap(10, 10)


@pytest.fixture
def world(world_map):
    w = World(world_map)
    w.genome_config = GenomeConfig()
    return w
