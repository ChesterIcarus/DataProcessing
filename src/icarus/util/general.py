
import logging as log

from typing import Callable, Hashable, Iterable, TypeVar
from inspect import signature


def chunk(start:int, stop:int, chunk:int):
    bins = zip(range(start, stop, chunk), 
        range(start+chunk, stop+chunk, chunk))
    for low, high in bins:
        yield low, high


def bins(iterable: Iterable, binsize: int):
    for idx in range(0, len(iterable), binsize):
        yield iterable[idx : idx + binsize]


def counter(iterable: Iterable, message: str, 
        start: int = 1, end: bool = True):
    n = 1
    count = 0
    for count, item in enumerate(iterable, start):
        if count == n:
            log.info(message % count)
            n <<= 1
        yield item
    if count != n >> 1 and end:
        log.info(message % count)


T = TypeVar('T')

class defaultdict(dict):
    def __init__(self, function: Callable[[Hashable], T]):
        self.function = function
        try:
            self.parameters = len(signature(function).parameters)
        except:
            self.parameters = 0
        self.locked = False

    def __getitem__(self, item: Hashable) -> T:
        if item in self:
            return super().__getitem__(item)
        elif not self.locked:
            if self.parameters:
                value = self.function(item)
            else:
                value = self.function()
            self[item] = value
            return value
        else:
            raise KeyError
    
    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

