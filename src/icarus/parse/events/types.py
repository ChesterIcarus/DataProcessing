
from enum import Enum


class NetworkMode(Enum):
    NONE = None
    BUS = 'bus'
    TRAM = 'tram'
    CAR = 'car'
    BIKE = 'bike'
    NETWALK = 'netwalk'
    PTWALK = 'ptwalk'
    ARTIFICIAL = 'artificial'
    RAIL = 'rail'
    WALK = 'walk'
    STOP_FACILITY_LINK = 'stopFacilityLink'



class LegMode(Enum):
    NONE = None
    BIKE = 'bike'
    CAR = 'car'
    NETWALK = 'netwalk'
    WALK = 'walk'
    PT = 'pt'

    FAKENETWALK = 'fakenetwalk'
    FAKECAR = 'fakecar'
    FAKEBIKE = 'fakebike'
    FAKEPT = 'fakept'
    FAKEMODE = 'fakemode'

    def transit(self):
        return self in (self.PT, self.WALK)

    def translate(self):
        trans = self
        if self == self.FAKENETWALK:
            trans = self.NETWALK
        elif self == self.FAKECAR:
            trans = self.CAR
        elif self == self.FAKEBIKE:
            trans = self.BIKE
        elif trans == self.FAKEPT:
            trans = self.PT
        return trans

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
    HOME = 'home'
    WORKPLACE = 'workplace'
    UNIVERSITY = 'university'
    SCHOOL = 'school'
    ESCORT = 'escort'
    SCHOOL_ESCORT = 'school_escort'
    PURE_ESCORT = 'pure_escort'
    RIDESHARE_ESCORT = 'rideshare_escort'
    OTHER_ESCORT = 'other_escort'
    SHOPPING = 'shopping'
    OTHER_MAINTENANCE = 'other_maintenance'
    EATING_OUT = 'eating_out'
    BREAKFAST = 'breakfast'
    LUNCH = 'lunch'
    DINNER = 'dinner'
    VISITING = 'visiting'
    OTHER_DISCRETIONARY = 'other_discretionary'
    SPECIAL_EVENT = 'special_events'
    WORK = 'work'
    WORK_BUSINESS = 'work_business'
    WORK_LUNCH = 'work_lunch'
    WORK_OTHER = 'work_other'
    WORK_RELATED = 'work_related'
    ASU = 'asu'

    PT_INTERACTION = 'pt interaction'
    
    FAKEACTIVITY = 'fakeactivity'

    def transit(self):
        return self == self.PT_INTERACTION

    def virtual(self):
        return self == self.FAKEACTIVITY