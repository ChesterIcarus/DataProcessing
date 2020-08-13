
from enum import IntEnum, Enum


class RouteMode(Enum):
    WALK = 'walk'
    BIKE = 'bike'
    CAR = 'car'
    PT = 'pt'

    def max_speed(self) -> float:
        speed = None
        if self == self.WALK:
            speed = 3.0
        elif self == self.BIKE:
            speed = 10.0
        elif self == self.CAR:
            speed = 35.0
        elif self == self.PT:
            speed = 30.0
        return speed


class ActivityType(IntEnum):
    HOME = 0
    WORKPLACE = 1
    UNIVERSITY = 2
    SCHOOL = 3
    ESCORT = 4
    SCHOOL_ESCORT = 41
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

    def escort(self) -> bool:
        return self in (
            self.ESCORT,
            self.SCHOOL_ESCORT,
            self.PURE_ESCORT,
            self.RIDESHARE_ESCORT,
            self.OTHER_ESCORT
        )


class Mode(IntEnum):
    SOV = 1
    HOV2 = 2
    HOV3 = 3
    PASSENGER = 4
    CONV_TRANS_WALK = 5
    CONV_TRANS_KNR = 6
    CONV_TRANS_PNR = 7
    PREM_TRANS_WALK = 8
    PREM_TRANS_KNR = 9
    PREM_TRANS_PNR = 10
    WALK = 11
    BIKE = 12
    TAXI = 13
    SCHOOL_BUS = 14

    def transit(self) -> bool:
        return self in (
            self.CONV_TRANS_WALK,
            self.CONV_TRANS_KNR,
            self.CONV_TRANS_PNR,
            self.PREM_TRANS_WALK,
            self.PREM_TRANS_KNR,
            self.PREM_TRANS_PNR
        )

    def vehicle(self) -> bool:
        return self in (
            self.SOV,
            self.HOV2,
            self.HOV3,
            self.PASSENGER,
            self.TAXI,
            self.SCHOOL_BUS 
        )

    def route_mode(self) -> RouteMode:
        route_mode = None
        if self.transit():
            route_mode = RouteMode.PT
        elif self.vehicle():
            route_mode = RouteMode.CAR
        elif self == self.WALK:
            route_mode = RouteMode.WALK
        elif self == self.BIKE:
            route_mode = RouteMode.BIKE
        return route_mode