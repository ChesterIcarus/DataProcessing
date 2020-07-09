
from icarus.analyze.exposure.link import Link


class Event:
    __slots__ = ('id', 'link', 'start', 'end', 'exposure')

    def __init__(self, uuid: int, link: Link, start: int, end: int):
        self.id = uuid
        self.link = link
        self.start = start
        self.end = end
        self.exposure = None


    def calculate_exposure(self) -> float:
        self.exposure = self.link.get_exposure(self.start, self.end)
        return self.exposure


    def export(self, leg: int, idx: int) -> tuple:
        return (
            self.id,
            leg,
            idx,
            self.link.id,
            self.start,
            self.end,
            self.end - self.start,
            self.exposure 
        )
    