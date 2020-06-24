
from icarus.analyze.exposure.centroid import Centroid


class Node:
    __slots__= ('id', 'maz', 'centroid', 'x', 'y')

    def __init__(self, node_id: str, maz: int, x: float, y:float):
        self.id = node_id
        self.maz = maz
        self.x = x
        self.y = y
