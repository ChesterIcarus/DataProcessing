
from icarus.parse.events.link import Link


class Event:
    uuid = 0
    __slots__= ('id', 'link', 'start', 'end')

    def __init__(self, link: Link, start: int, end: int):
        Event.uuid += 1
        self.id = Event.uuid
        self.link = link
        self.start = start
        self.end = end