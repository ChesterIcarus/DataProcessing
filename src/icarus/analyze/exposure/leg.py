
from typing import List

from icarus.analyze.exposure.types import LegMode
from icarus.analyze.exposure.event import Event
from icarus.analyze.exposure.link import Link


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

    
    def calculate_exposure(self, link: Link) -> float:
        self.exposure = 0
        if self.mode in (LegMode.BIKE, LegMode.WALK):
            if len(self.events):
                self.exposure = 0
                for event in self.events:
                    self.exposure += event.calculate_exposure()
            elif not self.abort:
                self.exposure = link.get_exposure(self.start, self.end, False)
        elif not self.abort:
            self.exposure = 25.5 * (self.end - self.start)

        return self.exposure

    
    def export(self, agent: int, idx: int) -> tuple:
        duration = None
        if not self.abort:
            duration = self.end - self.start

        return (
            self.id,
            agent,
            idx,
            self.mode.value,
            self.start,
            self.end,
            duration,
            self.abort,
            self.exposure 
        )
