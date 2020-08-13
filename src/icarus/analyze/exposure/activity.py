
from icarus.analyze.exposure.types import ActivityType
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel


class Activity:
    __slots__ = ('id', 'type', 'parcel', 'start', 
        'end', 'link', 'exposure', 'abort')

    def __init__(self, uuid: int, kind: ActivityType, parcel: Parcel,
            start: int, end: int, link: Link, abort: int):
        self.id = uuid
        self.parcel = parcel
        self.type = kind
        self.start = start
        self.end = end
        self.link = link
        self.abort = abort
        self.exposure: float = None


    def calculate_exposure(self) -> float:
        self.exposure = 0
        if not self.abort:
            self.exposure = self.parcel.get_exposure(self.start, self.end)

        return self.exposure

    
    def export(self, agent: int, idx: int):
        duration = 0
        if not self.abort:
            duration = self.end - self.start

        return (
            self.id,
            agent,
            idx,
            self.type.value,
            self.link.id,
            self.start,
            self.end,
            duration,
            self.abort,
            self.exposure 
        )
