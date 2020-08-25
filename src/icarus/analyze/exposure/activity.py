
from icarus.analyze.exposure.types import ActivityType
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel


class Activity:
    __slots__ = ('id', 'parcel', 'start', 'end', 'exposure', 'abort')

    def __init__(self, uuid: int, parcel: Parcel,
            start: int, end: int, abort: int):
        self.id = uuid
        self.parcel = parcel
        self.start = start
        self.end = end
        self.abort = abort
        self.exposure: float = None


    def calculate_exposure(self) -> float:
        self.exposure = 0
        if not self.abort:
            self.exposure = self.parcel.get_exposure(self.start, self.end)
        return self.exposure

    
    def export(self, agent: int, idx: int):
        return self.exposure, self.id
