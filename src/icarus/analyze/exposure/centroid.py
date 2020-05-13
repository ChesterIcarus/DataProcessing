
from typing import List


class Centroid:
    __slots__ = ('id', 'temperatures', 'x', 'y')
        
    def __init__(self, centroid_id: int, temperatures: List[float], 
            x: int, y: int):
        self.id = centroid_id
        self.temperatures = temperatures
        self.x = x
        self.y = y


    def get_temperature(self, time: int) -> float:
        steps = len(self.temperatures)
        step = int(time / 86400 * steps) % steps
        return self.temperatures[step]


    def get_exposure(self, start: int, end: int) -> float:
        steps = len(self.temperatures)
        step_size = int(86400 / steps)
        start_step = int(start / 86400 * steps)
        end_step = int(end / 86400 * steps)
        exposure = 0
        if start_step == end_step:
            exposure = (end - start) * self.temperatures[start_step % steps]
        else:
            exposure = ((start_step + 1) * step_size - start) * \
                self.temperatures[start_step % steps]
            for step in range(start_step + 1, end_step):
                exposure += step_size * self.temperatures[step % steps]
            exposure += (end - end_step * step_size) * \
                self.temperatures[end_step % steps]
        return exposure
