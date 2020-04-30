
import logging as log
from enum import Enum


class VehicleMode(Enum):
    NONE = None
    BUS = 'bus'
    TRAM = 'tram'
    CAR = 'car'
    BIKE = 'bike'
    NETWALK = 'netwalk'

    @staticmethod
    def parse(vehicle_id):
        mode = None
        flag = vehicle_id.split('_')[-1].lower()
        if flag.isdigit():
            mode = VehicleMode.CAR
        else:
            try:
                mode = VehicleMode(flag)
            except:
                raise RuntimeError(f'Unexpected vehicle id format in "{vehicle_id};'
                    'could not identify vehicle mode as bus, tram or car.')
        return mode

    def outdoors(self):
        return self in (self.BIKE, self.NETWALK)
        


class LegMode(Enum):
    NONE = None
    BUS = 'bus'
    BIKE = 'bike'
    CAR = 'car'
    NETWALK = 'netwalk'
    WALK = 'walk'
    PT = 'pt'
    FAKEMODE = 'fakemode'

    def transit(self):
        return self in (self.PT, self.WALK)

    def artificial(self):
        return self == self.FAKEMODE

    def string(self):
        string = None
        if self.transit():
            string = 'pt'
        elif self == self.NETWALK:
            string = 'walk'
        else:
            string = self.value
        return string
            


class ActivityType(Enum):
    NONE = None
    HOME = 0
    WORKPLACE = 1
    UNIVERSITY = 2
    SCHOOL = 3
    ESCORT = 4
    SCHOOL_ESCPORT = 41
    PURE_ESCORT = 411
    RIDESHARE_ESCORT = 412
    OTHER_ESCORT = 42
    SHOPPING = 5
    OTHER_MAINTENANCE = 6
    EATING_OUT = 7
    BREAKFAST = 71
    LUNCH = 72
    DINNER = 73
    VISITING = 8
    OTHER_DISCRETIONARY = 9
    SPECIAL_EVENT = 10
    WORK = 11
    WORK_BUSINESS = 12
    WORK_LUNCH = 13
    WORK_OTHER = 14
    WORK_RELATED = 15
    ASU = 16

    PT_INTERACTION = 100
    FAKEACTIVITY = 101

    @classmethod
    def parse(self, name):
        name = name.upper().replace(' ', '_')
        return getattr(self, name)


    def transit(self):
        return self == self.PT_INTERACTION

    def artificial(self):
        return self == self.FAKEACTIVITY