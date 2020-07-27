
from typing import Set

from icarus.analyze.exposure.temperature import Temperature
from icarus.analyze.exposure.types import NetworkMode
from icarus.analyze.exposure.node import Node


class Link:
    __slots__ = ('length', 'freespeed', 'id', 'capacity',
            'modes', 'air_temperature', 'mrt_temperature', 'exposure')

    def __init__(self, link_id: str, length: float, freespeed: float,
            modes: Set[NetworkMode], air_temperature: Temperature, 
            mrt_temperature: Temperature):
        self.id = link_id
        self.length = length
        self.freespeed = freespeed
        self.modes = modes
        self.air_temperature = air_temperature
        self.mrt_temperature = mrt_temperature
        self.exposure = 0

    
    def get_temperature(self, time: int) -> float:
        temp = None
        if self.mrt_temperature:
            temp = self.mrt_temperature.get_temperature(
                time, self.air_temperature)
        else:
            temp = self.air_temperature.get_temperature(time)
        return temp


    def get_exposure(self, start: int, end: int, record: bool) -> float:
        exp = None
        if self.mrt_temperature:
            exp = self.mrt_temperature.get_exposure(
                start, end, self.air_temperature)
        else:
            exp = self.air_temperature.get_exposure(start, end)
        
        self.exposure += exp
        return exp
