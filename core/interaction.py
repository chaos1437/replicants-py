"""Взаимодействия ботов"""
from collections import namedtuple

Interaction = namedtuple('Interaction', ['bot', 'direction', 'type', 'strength'])
