
import logging as log
from icarus.output.objects.types import ActivityType, LegMode


class Activity:
    __slots__ = ('activity_type', 'start_time', 'active_time',
            'end_time', 'exposure', 'link')
    
    def __init__(self, activity_type):
        self.activity_type = activity_type
        self.start_time = None
        self.active_time = None
        self.end_time = None
        self.link = None
        self.exposure = 0


    def start(self, time, link):
        self.start_time = time
        self.active_time = time
        self.link = link


    def wait(self, time, temperature):
        self.exposure += (time - self.active_time) * temperature
        self.active_time = time

    
    def end(self, time):
        self.end_time = time
        self.active_time = None


class Leg:
    __slots__ = ('mode', 'start_time', 'start_link', 'active_time', 'active_link',
            'end_time', 'end_link','exposure')

    def __init__(self, leg_mode):
        self.mode = leg_mode
        self.start_time = None
        self.start_link = None
        self.active_time = None
        self.active_link = None
        self.end_time = None
        self.end_link = None
        self.exposure = 0

    
    def start(self, time, link):
        self.start_time = time
        self.start_link = link
        self.active_time = time
        self.active_link = link

    
    def teleport(self, time, link):
        self.exposure += self.start_link.get_exposure(self.active_time, time)
        self.active_time = time
        self.active_link = link

    
    def wait(self, time, temperature):
        self.exposure += (time - self.active_time) * temperature
        self.active_time = time


    def travel(self, time, route):
        self.exposure += route.get_exposure(self.active_time, time)
        self.active_time = time
        self.active_link = route.end_link

    
    def end(self, time, link):
        self.end_time = time
        self.end_link = link
        self.active_time = None
        self.active_link = None



class Agent:
    def __init__(self, uuid):
        self.id = uuid
        self.activities = []
        self.legs = []
        self.routes = {}

        self.active_activity = None
        self.active_leg = None


    def exposure(self):
        return sum(leg.exposure for leg in self.legs) + \
            sum(act.exposure for act in self.activities)


    def size(self):
        return len(self.legs) + len(self.activities)

    
    def export_activities(self):
        activities = ((
            self.id,
            idx,
            activity.activity_type.name.lower(),
            activity.start_time,
            activity.end_time,
            activity.end_time - activity.start_time,
            activity.exposure
        ) for idx, activity in enumerate(self.activities))
        return activities

    
    def export_legs(self):
        legs =  ((
            self.id,
            idx,
            leg.mode.string(),
            leg.start_time,
            leg.end_time,
            leg.end_time - leg.start_time,
            leg.exposure
        ) for idx, leg in enumerate(self.legs))
        return legs


    def start_activity(self, time, activity_type, link):
        transit = self.active_leg is not None and self.active_leg.mode.transit()
        if not activity_type.transit():
            if transit:
                self.active_leg.end(time, link)
                self.legs.append(self.active_leg)
                self.active_leg = None
            self.active_activity = Activity(activity_type)
            self.active_activity.start(time, link)
        elif transit:
            self.active_leg.teleport(time, link)
    

    def end_activity(self, time, link=None):
        if self.active_leg is not None:
            if self.active_leg.mode.transit():
                self.active_leg.teleport(time, link)
        else:
            if self.active_activity is None:
                self.active_activity = Activity(ActivityType.HOME)
                self.active_activity.start(14400, link)
            self.active_activity.wait(time, 25.5)
            self.active_activity.end(time)
            self.activities.append(self.active_activity)
            self.active_activity = None

    
    def depart(self, time, mode, link):
        if self.active_leg is not None:
            if self.active_leg.mode.transit():
                self.active_leg.teleport(time, link)
        else:
            self.active_leg = Leg(mode)
            self.active_leg.start(time, link)


    def arrive(self, time, link):
        if self.active_leg.active_link != link:
            mode = self.active_leg.mode.value
            start = self.active_leg.active_link.id
            end = link.id
            uuid = f'{mode}-{start}-{end}'
            if uuid in self.routes:
                self.active_leg.travel(time, self.routes[uuid])
            else:
                self.active_leg.teleport(time, link)

        if not self.active_leg.mode.transit():
            self.active_leg.end(time, link)
            self.legs.append(self.active_leg)
            self.active_leg = None


    def expose(self, exposure):
        self.active_leg.exposure += exposure

