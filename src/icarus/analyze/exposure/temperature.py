
from typing import Tuple


class Temperature:
    __slots__ = ('id', 'values')

    def __init__(self, uuid: int, values: Tuple[float]):
        self.id = uuid
        self.values = values

    
    def get_temperature(self, time: float):
        steps = len(self.values)
        step = int(time / 86400 * steps) % steps
        return self.values[step]


    def get_exposure(self, start: float, end: float) -> float:
        steps = len(self.values)
        step_size = int(86400 / steps)
        start_step = int(start / 86400 * steps)
        end_step = int(end / 86400 * steps)
        exposure = 0
        if start_step == end_step:
            exposure = (end - start) * self.values[start_step % steps]
        else:
            exposure = ((start_step + 1) * step_size - start) * \
                self.values[start_step % steps]
            for step in range(start_step + 1, end_step):
                exposure += step_size * self.values[step % steps]
            exposure += (end - end_step * step_size) * \
                self.values[end_step % steps]
        return exposure


