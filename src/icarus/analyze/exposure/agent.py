
import logging as log

from typing import List, Tuple

from icarus.analyze.exposure.leg import Leg
from icarus.analyze.exposure.activity import Activity
from icarus.analyze.exposure.event import Event


class Agent:
    __slots__= ('id', 'legs', 'activities', 'air_exposure', 'mrt_exposure', 'abort')

    def __init__(self, uuid: int, abort: int):
        self.id = uuid
        self.legs: List[Leg] = []
        self.activities: List[Activity] = []
        self.air_exposure: float = None
        self.mrt_exposure: float = None
        self.abort = abort

    
    def add_leg(self, leg: Leg):
        self.legs.append(leg)

    
    def add_activity(self, activity: Activity):
        self.activities.append(activity)

    
    def add_event(self, leg_idx: int, event: Event):
        self.legs[leg_idx].add_event(event)

    
    def calculate_exposure(self) -> Tuple[float]:
        evts = [ act.calculate_exposure() for act in self.activities ]
        evts += [ leg.calculate_exposure() for leg in self.legs ]

        if not self.abort:
            self.air_exposure = sum(map(lambda x: x[0], evts))

            if all(map(lambda x: (x[1] is not None), evts)):
                self.mrt_exposure = sum(map(lambda x: x[1], evts))
            else:
                pass
                # log.warn('Agent %s has a undefined MRT exposure.' % self.id)
        
        return self.air_exposure, self.mrt_exposure

    
    def export(self):
        return self.air_exposure, self.mrt_exposure, self.id
