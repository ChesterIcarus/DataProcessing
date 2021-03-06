
import logging as log
from itertools import chain
from typing import Tuple, List

from icarus.parse.events.activity import Activity
from icarus.parse.events.leg import Leg
from icarus.parse.events.event import Event
from icarus.parse.events.link import Link
from icarus.parse.events.types import ActivityType, LegMode    


class Agent:
    __slots__ = ('id', 'activities', 'legs', 'routes', 'active_activity', 'act_count',
            'active_leg', 'active_transit', 'active_virtual', 'leg_count')
    
    def __init__(self, uuid):
        self.id = uuid
        self.activities: List[Activity] = []
        self.legs: List[Leg] = []
        self.routes = {}
        self.leg_count = 0
        self.act_count = 0

        self.active_activity = None
        self.active_leg = None
        self.active_transit = None
        self.active_virtual = None


    def size(self):
        return len(self.legs) + len(self.activities)

    
    def export_activities(self):
        activities = tuple((
            Activity.activities[self.id][idx],
            self.id,
            idx,
            activity.activity_type.name.lower(),
            activity.link.id,
            activity.start_time,
            activity.end_time,
            activity.end_time - activity.start_time,
            None
        ) for idx, activity in enumerate(self.activities, start=self.act_count))
        self.act_count += len(self.activities)
        self.activities = []
        return activities

    
    def export_legs(self):
        legs =  tuple((
            Leg.legs[self.id][idx],
            self.id,
            idx,
            leg.mode.string(),
            leg.start_time,
            leg.end_time,
            leg.end_time - leg.start_time,
            None
        ) for idx, leg in enumerate(self.legs, start=self.leg_count))
        self.leg_count += len(self.legs)
        self.legs = []
        return legs


    def export_events(self):
        events = chain(*(leg.export_events(self.id, idx) 
            for idx, leg in enumerate(self.legs, start=self.leg_count)))
        return events


    def start_activity(self, time: int, link: Link, activity_type: ActivityType):
        if self.active_activity is not None:
            raise RuntimeError('Agent attempted to start a new activity but '
                'still has an unfinished activity.')
        if self.active_leg is not None:
            raise RuntimeError('Agent attempted to start a new activity but '
                'still has an unfinished leg.')

        # if self.active_transit is not None and not activity_type.transit():
        #     self.legs.append(self.active_transit)
        #     self.active_transit = None
        
        self.active_activity = Activity(activity_type, link)
        self.active_activity.start_time = time

    
    def end_activity(self, time: int, link: Link = None, 
            activity_type: ActivityType = None):
        if self.act_count == 0 and len(self.activities) == 0:
            if link is None:
                breakpoint()
            self.active_activity = Activity(ActivityType.HOME, link)
            self.active_activity.start_time = 14400
            
        if self.active_activity is None:
            raise RuntimeError('Agent attempted to end an activity but agent '
                'has no active activity.')
        if self.active_leg is not None:
            raise RuntimeError('Agent attempted to end an activity but agent '
                'still has an active leg.')

        self.active_activity.end_time = time

        if activity_type.virtual():
            self.active_virtual.end_time = time
        # elif activity_type.transit():
        #     event = Event(link, self.active_activity.start_time, time)
        #     self.active_transit.end_time = time
        #     self.active_transit.events.append(event)
        else:
            self.activities.append(self.active_activity)

        self.active_activity = None


    def start_leg(self, time: int, link: Link, leg_mode: LegMode):
        leg = Leg(leg_mode)
        leg.start(time, link)

        self.active_leg = leg

    
    def travel(self, time: int):
        self.active_leg.travel()


    def end_leg(self, time: int, link: Link, leg_mode: LegMode):
        leg = self.active_leg
        route = None
        if leg.travelled:
            route = self.get_route(leg_mode, leg.start_link, link)
        leg.end(time, link, route)

        if leg_mode.virtual():
            if self.active_virtual is None:
                self.active_virtual = leg
            else:
                self.active_virtual.end_link = link
                self.active_virtual.end_time = time
                self.active_virtual.events.extend(leg.events)
        # elif leg_mode.transit():
        #     if self.active_transit is None:
        #         self.active_transit = leg
        #     else:
        #         self.active_transit.end_link = link
        #         self.active_transit.end_time = time
        #         self.active_transit.events.extend(leg.events)
        elif self.active_virtual is not None:
            self.active_virtual.end_link = link
            self.active_virtual.end_time = time
            self.active_virtual.mode = leg_mode
            self.active_virtual.events.extend(leg.events)
            self.legs.append(self.active_virtual)
            self.active_virtual = None
        else:
            self.legs.append(leg)

        self.active_leg = None
        

    def get_route(self, leg_mode: LegMode, start_link: Link, end_link: Link):
        route = None
        uuid = f'{leg_mode.value}-{start_link.id}-{end_link.id}'
        if uuid in self.routes:
            route = self.routes[uuid]
        return route