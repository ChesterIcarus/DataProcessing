
from icarus.analyze.exposure.types import ActivityType
from icarus.analyze.exposure.link import Link
from icarus.analyze.exposure.parcel import Parcel


class Activity:
    __slots__ = ('id', 'parcel', 'start', 'end', 'air_exposure', 
                 'mrt_exposure', 'abort')

    def __init__(self, uuid: int, parcel: Parcel,
            start: int, end: int, abort: int):
        self.id = uuid
        self.parcel = parcel
        self.start = start
        self.end = end
        self.abort = abort
        self.air_exposure: float = None
        self.mrt_exposure: float = None


    def calculate_exposure(self) -> float:
        if not self.abort:
            self.air_exposure = self.parcel.get_exposure(self.start, self.end)
            self.mrt_exposure = self.air_exposure
        return self.air_exposure, self.mrt_exposure

    
    def export(self, agent: int, idx: int):
        return self.air_exposure, self.mrt_exposure, self.id
