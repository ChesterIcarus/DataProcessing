
from typing import List

from icarus.parse.events.link import Link
from icarus.parse.events.event import Event
from icarus.parse.events.types import LegMode

class Route:
    __slots__= ('path', 'distance', 'mode')

    def __init__(self, path: List[Link], distance: float, mode: LegMode):
        self.path = path
        self.distance = distance
        self.mode = mode

    
    def extract_events(self, start: int, end: int) -> List[Event]:
        total = sum(link.length for link in self.path)
        duration = end - start
        events = []

        if duration > 0 and total > 0.0:
            time = start
            distance = 0
            for link in self.path:
                time = int(round(start + duration * distance / total ))
                distance += link.length
                next_time = int(round(start + duration * distance / total ))
                events.append(Event(link, time, next_time))

        return events
