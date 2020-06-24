
from typing import Set

from icarus.analyze.exposure.temperature import Temperature
from icarus.analyze.exposure.types import NetworkMode
from icarus.analyze.exposure.node import Node


class Link:
    __slots__ = ('length', 'freespeed', 'id', 'capacity',
            'modes', 'temperature')

    def __init__(self, link_id: str, length: float, freespeed: float,
            modes: Set[NetworkMode], temperature: Temperature):
        self.id = link_id
        self.length = length
        self.freespeed = freespeed
        self.modes = modes
        self.temperature = temperature

    
    def get_temperature(self, time: int) -> float:
        return self.temperature.get_temperature(time)


    def get_exposure(self, start: int, end: int) -> float:
        return self.temperature.get_exposure(start, end)
