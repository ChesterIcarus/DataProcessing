
from typing import Tuple, Set

from icarus.analyze.exposure.temperature import Temperature
from icarus.analyze.exposure.types import NetworkMode
from icarus.analyze.exposure.node import Node


class Link:
    __slots__ = ('length', 'freespeed', 'id', 'capacity','modes', 
                 'air_temperature', 'mrt_temperature', 'air_exposure', 
                 'mrt_exposure')

    def __init__(self, link_id: str, length: float, freespeed: float,
            modes: Set[NetworkMode], air_temperature: Temperature, 
            mrt_temperature: Temperature):
        self.id = link_id
        self.length = length
        self.freespeed = freespeed
        self.modes = modes
        self.air_temperature = air_temperature
        self.mrt_temperature = mrt_temperature
        self.air_exposure = 0
        self.mrt_exposure = 0

    
    def get_temperature(self, time: int) -> float:
        air = self.air_temperature.get_temperature(time)

        mrt = None
        if self.mrt_temperature and time >= 18000 and time <= 74700:
            mrt = self.mrt_temperature.get_temperature(time)
        
        return air, mrt


    def get_exposure(self, start: int, end: int, record: bool) -> Tuple[float]:
        air = self.air_temperature.get_exposure(start, end)

        mrt = None
        if self.mrt_temperature is not None:
            mrt = self.mrt_temperature.get_exposure(start, end)
        
        if record:
            self.air_exposure += air or 0
            self.mrt_exposure += mrt or 0
        
        return air, mrt

    
    def export(self):
        mrt = self.mrt_exposure if self.mrt_temperature else None
        return self.air_exposure, mrt, self.id
