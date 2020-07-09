
from __future__ import annotations

from math import sqrt
from typing import Tuple, Iterable

from icarus.util.iter import pair


class Point:
    __slots__ = ('x', 'y')

    @staticmethod
    def unit():
        return Point(1, 1)

    @staticmethod
    def zero():
        return Point(0, 0)

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def copy(self) -> Point:
        return Point(self.x, self.y)

    def add(self, pt: Point) -> Point:
        return Point(self.x + pt.x, self.y + pt.y)
    
    def sub(self, pt: Point) -> Point:
        return Point(self.x - pt.x, self.y - pt.y)
    
    def dot(self, pt: Point) -> Point:
        return self.x * pt.x + self.y * pt.y

    def inv(self) -> Point:
        return Point(-self.x, -self.y)

    def scale(self, scalar: float) -> Point:
        return Point(self.x * scalar, self.y * scalar)

    def mag(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y)

    def proj(self, pt: Point):
        return pt.scale(self.dot(pt) / pt.dot(pt))

    def rejct(self, pt: Point):
        return self.sub(self.proj(pt))

    def __add__(self, pt: Point):
        if type(pt) == Point:
            return Point(self.x + pt.x, self.y + pt.y)
        else:
            raise TypeError

    def __sub__(self, pt: Point):
        if type(pt) == Point:
            return Point(self.x - pt.x, self.y - pt.y)
        else:
            raise TypeError


class Polygon:
    __slots__ = ('points')

    @staticmethod
    def load(wkt) -> Polygon:
        pts = wkt[10:-2].split(', ')
        points = tuple(Point(*map(float, pt.split(' '))) for pt in pts)
        return Polygon(points)


    def __init__(self, points: Tuple[Point]):
        self.points = points

    
    def centroid(self) -> Tuple[Point]:
        area = sum(p1.x * p2.y - p1.x * p2.y 
            for p1, p2 in pair(self.points)) / 2
        x = sum((p1[0] + p2[0]) * (p1[0] * p2[1] - p2[0] * p1[1]) 
            for p1, p2 in pair(self.points)) / 6 / area
        y = sum((p1[1] + p2[1]) * (p1[0] * p2[1] - p2[0] * p1[1]) 
            for p1, p2 in pair(self.points)) / 6 / area
        
        return Point(x, y)


