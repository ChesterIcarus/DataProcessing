
from icarus.analyze.exposure.centroid import Centroid


class Node:
    __slots__= ('id', 'maz', 'centroid', 'x', 'y')

    def __init__(self, node_id: str, maz: int, centroid: Centroid, 
            x: float, y:float):
        self.id = node_id
        self.maz = maz
        self.centroid = centroid
        self.x = x
        self.y = y

    def get_temperature(self, time: int) -> float:
        return self.centroid.get_temperature(time)


    def get_exposure(self, start: int, end: int) -> float:
        return self.centroid.get_exposure(start, end)
