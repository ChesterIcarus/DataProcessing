
from __future__ import annotations

from typing import Tuple


class Temperature:
    __slots__ = ('id', 'values')

    def __init__(self, uuid: int, values: Tuple[float]):
        self.id = uuid
        self.values = values

    
    def get_temperature(self, time: float, fallback: Temperature = None):
        steps = len(self.values)
        step = int(time / 86400 * steps) % steps
        value = self.values[step]
        if fallback and not value:
            value = fallback.get_temperature(time)
        return value


    def get_exposure(self, start: float, end: float, 
            fallback: Temperature = None) -> float:
        steps = len(self.values)
        step_size = int(86400 / steps)
        start_step = int(start / 86400 * steps)
        end_step = int(end / 86400 * steps)
        exposure = 0

        def temp(x: int):
            value = self.values[x]
            if value is None and fallback:
                value = fallback.values[x]
            return value

        if start_step == end_step:
            exposure = (end - start) * temp(start_step % steps)
        else:
            exposure = ((start_step + 1) * step_size - start) * \
                temp(start_step % steps)
            for step in range(start_step + 1, end_step):
                exposure += step_size * temp(step % steps)
            exposure += (end - end_step * step_size) * temp(end_step % steps)
        return exposure


