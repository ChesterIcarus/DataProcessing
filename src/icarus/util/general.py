
import logging as log


def chunk(start, stop, chunk):
    bins = zip(range(start, stop, chunk), 
        range(start+chunk, stop+chunk, chunk))
    for low, high in bins:
        yield low, high


def bins(iterable, binsize):
    for idx in range(0, len(iterable), binsize):
        yield iterable[idx : idx + binsize]


def counter(iterable, message, start=1, end=True):
    n = 1
    count = 0
    for count, item in enumerate(iterable, start):
        if count == n:
            log.info(message % count)
            n <<= 1
        yield item
    if count != n >> 1 and end:
        log.info(message % count)


class defaultdict(dict):
    def __init__(self, function):
        self.function = function
        self.locked = False

    def __getitem__(self, item):
        if item in self:
            return super().__getitem__(item)
        elif not self.locked:
            value = self.function(item)
            self[item] = value
            return value
        else:
            raise KeyError
    
    def lock(self):
        self.locked = True

    def unlock(self):
        self.locked = False

