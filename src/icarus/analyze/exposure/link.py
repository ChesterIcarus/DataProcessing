
from typing import Set

from icarus.analyze.exposure.types import NetworkMode
from icarus.analyze.exposure.node import Node


class Link:
    __slots__ = ('length', 'freespeed', 'src_node', 'term_node', 'id', 
            'capacity', 'modes')

    def __init__(self, link_id: str, src_node: Node, term_node: Node, 
            length: float, freespeed: float, modes: Set[NetworkMode]):
        self.id = link_id
        self.src_node = src_node
        self.term_node = term_node
        self.length = length
        self.freespeed = freespeed
        self.modes = modes

    
    def get_temperature(self, time: int) -> float:
        return self.src_node.get_temperature(time)


    def get_exposure(self, start: int, end: int) -> float:
        return self.src_node.get_exposure(start, end)
