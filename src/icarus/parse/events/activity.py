
from typing import Dict, List

from icarus.parse.events.types import ActivityType


class Activity:
    activities: Dict[str, List]

    __slots__ = ('activity_type', 'start_time', 'end_time')
    
    def __init__(self, activity_type: ActivityType):
        self.activity_type = activity_type
        self.start_time = None
        self.end_time = None