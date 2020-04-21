
from enum import IntEnum

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

    def escort(self):
        return self in (
            self.ESCORT,
            self.SCHOOL_ESCORT,
            self.PURE_ESCORT,
            self.RIDESHARE_ESCORT,
            self.OTHER_ESCORT   )