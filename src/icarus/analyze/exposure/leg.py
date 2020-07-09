
from typing import List

from icarus.analyze.exposure.types import LegMode
from icarus.analyze.exposure.event import Event
from icarus.analyze.exposure.link import Link


class Leg:
    __slots__= ('id', 'mode', 'start', 'end', 'events', 'exposure')

    def __init__(self, uuid: str, mode: LegMode, start: int, end: int):
        self.id = uuid
        self.mode = mode
        self.start = start
        self.end = end
        self.events: List[Event] = []
        self.exposure = None


    def add_event(self, event: Event):
        self.events.append(event)

    
    def calculate_exposure(self, link: Link) -> float:
        if self.mode in (LegMode.BIKE, LegMode.WALK):
            if len(self.events):
                self.exposure = 0
                for event in self.events:
                    self.exposure += event.calculate_exposure()
            else:
                self.exposure = link.get_exposure(self.start, self.end)
        else:
            self.exposure = 25.5 * (self.end - self.start)
        return self.exposure

    
    def export(self, agent: int, idx: int) -> tuple:
        return (
            self.id,
            agent,
            idx,
            self.mode.value,
            self.start,
            self.end,
            self.end - self.start,
            self.exposure 
        )
