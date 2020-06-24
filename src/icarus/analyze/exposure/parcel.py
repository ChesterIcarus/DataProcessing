
from icarus.analyze.exposure.temperature import Temperature

class Parcel:
    __slots__ = ('apn', 'temperature')

    def __init__(self, apn: str, temperature: Temperature):
        self.apn = apn
        self.temperature = temperature


    def get_temperature(self, time: int) -> float:
        return self.temperature.get_temperature(time)


    def get_exposure(self, start: int, end: int) -> float:
        return self.temperature.get_exposure(start, end)
