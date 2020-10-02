
import logging as log
from typing import List

from icarus.analyze.exposure.types import LegMode
from icarus.analyze.exposure.event import Event
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel


class Leg:
    __slots__= ('id', 'mode', 'start', 'end', 'events', 
                'air_exposure', 'mrt_exposure', 'abort')

    def __init__(self, uuid: str, mode: LegMode, start: int, 
            end: int, abort: int):
        self.id = uuid
        self.mode = mode
        self.start = start
        self.end = end
        self.events: List[Event] = []
        self.abort = abort
        self.air_exposure = None
        self.mrt_exposure = None


    def add_event(self, event: Event):
        self.events.append(event)

    
    def calculate_exposure(self) -> float:
        if self.end - self.start:
            if self.mode in (LegMode.BIKE, LegMode.WALK):
                if len(self.events):
                    self.air_exposure = 0
                    self.mrt_exposure = 0
                    for event in self.events:
                        air, mrt = event.calculate_exposure()
                        self.air_exposure += air
                        if mrt is None or self.mrt_exposure is None:
                            self.mrt_exposure = None
                        else:
                            self.mrt_exposure += mrt
                else:
                    log.error('Unexpected leg without any events.')
            else:
                self.air_exposure = 26.6667 * (self.end - self.start)
                self.mrt_exposure = None
        else:
            self.air_exposure = 0
            self.mrt_exposure = 0

        return self.air_exposure, self.mrt_exposure

    
    def export(self, agent: int, idx: int) -> tuple:
        return self.air_exposure, self.mrt_exposure, self.id
