
from typing import Set

from icarus.parse.events.node import Node
from icarus.parse.events.types import NetworkMode

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