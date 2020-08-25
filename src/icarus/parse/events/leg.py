
from typing import Dict, List

from icarus.parse.events.types import LegMode
from icarus.parse.events.route import Route
from icarus.parse.events.link import Link
from icarus.parse.events.event import Event


class Leg:
    __slots__ = ('mode', 'start_time', 'start_link', 'end_time', 
            'end_link', 'events', 'travelled', 'abort')

    def __init__(self, leg_mode: LegMode):
        self.mode = leg_mode
        self.start_time: int = None
        self.start_link: Link = None
        self.end_time: int = None
        self.end_link: Link = None
        self.events: List[Event] = []
        self.travelled = False

        self.abort = False


    def travel(self):
        self.travelled = True

    
    def start(self, time: int, link: Link):
        self.start_time = time
        self.start_link = link


    def end(self, time: int, link: Link, route: Route):
        self.end_time = time
        self.end_link = link

        if self.travelled and route is not None:
            self.events = route.extract_events(self.start_time, time)

    
    def export_events(self, agent_id: str, leg_idx: int):
        events = tuple((
            event.id,
            int(agent_id),
            leg_idx,
            idx,
            event.link.id,
            event.start,
            event.end
        ) for idx, event in enumerate(self.events))
        self.events = []
        return events
