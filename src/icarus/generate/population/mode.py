
from enum import IntEnum
from icarus.input.objects.route_mode import RouteMode

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

    def transit(self):
        return self in (
            self.CONV_TRANS_WALK,
            self.CONV_TRANS_KNR,
            self.CONV_TRANS_PNR,
            self.PREM_TRANS_WALK,
            self.PREM_TRANS_KNR,
            self.PREM_TRANS_PNR )

    def vehicle(self):
        return self in (
            self.SOV,
            self.HOV2,
            self.HOV3,
            self.PASSENGER,
            self.TAXI,
            self.SCHOOL_BUS )

    def route_mode(self):
        route_mode = None
        if self.transit():
            route_mode = RouteMode.PT
        elif self.vehicle():
            route_mode = RouteMode.CAR
        elif self == self.WALK:
            route_mode = RouteMode.NETWALK
        elif self == self.BIKE:
            route_mode = RouteMode.BIKE
        return route_mode