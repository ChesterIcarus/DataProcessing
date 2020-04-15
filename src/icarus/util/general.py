

def chunk(start, stop, chunk):
    bins = zip(range(start, stop, chunk), 
        range(start+chunk, stop+chunk, chunk))
    for low, high in bins:
        yield low, high


def bins(iterable, binsize):
    for idx in range(0, len(iterable), binsize):
        yield iterable[idx : idx + binsize]


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

