
from icarus.analyze.exposure.types import ActivityType
from icarus.analyze.exposure.link import Link


class Activity:
    __slots__ = ('id', 'type', 'link', 'start', 'end', 'exposure')

    def __init__(self, uuid: int, kind: ActivityType, link: Link,
            start: int, end: int):
        self.id = uuid
        self.link = link
        self.type = kind
        self.start = start
        self.end = end
        self.exposure: float = None


    def calculate_exposure(self) -> float:
        self.exposure = 25.5 * (self.end - self.start)
        return self.exposure

    
    def export(self, agent: int, idx: int):
        return (
            self.id,
            agent,
            idx,
            self.type.value,
            self.link.id,
            self.start,
            self.end,
            self.end - self.start,
            self.exposure )
