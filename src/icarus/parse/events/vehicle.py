
from icarus.parse.events.link import Link
from icarus.parse.events.event import Event

class Vehicle:
    __slots__ = ('id', 'link', 'time', 'events')

    def __init__(self, uuid):
        self.id = uuid
        self.link = None
        self.time = None
        self.events = []
    

    def enter_link(self, time: int, link: Link):
        self.link = link
        self.time = time

    
    def leave_link(self, time: int, link: Link):
        event = Event(link, self.time, time)
        self.events.append(event)
        self.link = link
        self.time = time
