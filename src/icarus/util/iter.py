
from typing import Iterable, Callable
from itertools import islice


def pair(iterable: Iterable):
    head = iter(iterable)
    peek = iter(iterable)
    next(peek)
    for ahead in peek:
        yield (next(head), ahead)


def chunk(iterable: Iterable, size: int):
    i = iter(iterable)
    piece = list(islice(i, size))
    while piece:
        yield piece
        piece = list(islice(i, size))

