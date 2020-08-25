
import logging as log
from typing import List

from icarus.analyze.exposure.types import LegMode
from icarus.analyze.exposure.event import Event
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel


class Leg:
    __slots__= ('id', 'mode', 'start', 'end', 'events', 'exposure', 'abort')

    def __init__(self, uuid: str, mode: LegMode, start: int, 
            end: int, abort: int):
        self.id = uuid
        self.mode = mode
        self.start = start
        self.end = end
        self.events: List[Event] = []
        self.abort = abort
        self.exposure = None


    def add_event(self, event: Event):
        self.events.append(event)

    
    def calculate_exposure(self) -> float:
        self.exposure = 0
        if self.end - self.start:
            if self.mode in (LegMode.BIKE, LegMode.WALK):
                if len(self.events):
                    self.exposure = 0
                    for event in self.events:
                        self.exposure += event.calculate_exposure()
                else:
                    log.error('Unexpected leg without any events.')
                    breakpoint()
            else:
                self.exposure = 25.5 * (self.end - self.start)

        return self.exposure

    
    def export(self, agent: int, idx: int) -> tuple:
        return self.exposure, self.id
