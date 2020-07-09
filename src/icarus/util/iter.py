
from typing import Iterable, Callable
from collections import deque
from itertools import islice

marker = object()


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


def peekable(iterable: Iterable):
    class Peekable:
        __slots__ = ('iterable', 'queue')

        def __init__(self, iterable: Iterable):
            self.iterable = iterable
            self.queue = deque()
        
        def peek(self, defualt=marker):
            value = None
            if not self.queue:
                value = next(self.iterable)
                self.queue.append(value)
            else:
                value = self.queue[0]
            return value

        def __bool__(self):
            try:
                self.peek()
            except StopIteration:
                return False
            return True

        def __iter__(self):
            return self

        def __next__(self):
            value = None
            if self.queue:
                value = self.queue.popleft()
            else:
                value = next(self.iterable)
            return value

    return Peekable(iterable)