
from typing import List

from icarus.analyze.exposure.leg import Leg
from icarus.analyze.exposure.activity import Activity
from icarus.analyze.exposure.event import Event


class Agent:
    __slots__= ('id', 'legs', 'activities', 'exposure')

    def __init__(self, uuid: int):
        self.id = uuid
        self.legs: List[Leg] = []
        self.activities: List[Activity] = []
        self.exposure: float = None

    
    def add_leg(self, leg: Leg):
        self.legs.append(leg)

    
    def add_activity(self, activity: Activity):
        self.activities.append(activity)

    
    def add_event(self, leg_idx: int, event: Event):
        self.legs[leg_idx].add_event(event)

    
    def calculate_exposure(self) -> float:
        self.exposure = 0
        for activity in self.activities:
            self.exposure += activity.calculate_exposure()
        for idx, leg in enumerate(self.legs):
            link = self.activities[idx].link
            self.exposure += leg.calculate_exposure(link)
        return self.exposure

    
    def export(self):
        return (
            self.id,
            len(self.activities) + len(self.legs),
            self.exposure
        )
