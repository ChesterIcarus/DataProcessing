
from icarus.analyze.exposure.link import Link


class Event:
    __slots__ = ('id', 'link', 'start', 'end', 'air_exposure', 'mrt_exposure')

    def __init__(self, uuid: int, link: Link, start: int, end: int):
        self.id = uuid
        self.link = link
        self.start = start
        self.end = end
        self.air_exposure = None
        self.mrt_exposure = None


    def calculate_exposure(self) -> float:
        self.air_exposure, self.mrt_exposure = \
            self.link.get_exposure(self.start, self.end, True)
        return self.air_exposure, self.mrt_exposure


    def export(self, leg: int, idx: int) -> tuple:
        return self.air_exposure, self.mrt_exposure, self.id
    