
from __future__ import annotations

from typing import Tuple


class Temperature:
    __slots__ = ('id', 'values', 'merged')

    def __init__(self, uuid: int, values: Tuple[float]):
        self.id = uuid
        self.values = values
        self.merged = None not in values

    
    def merge_null(self, temp: Temperature):
        for idx in range(len(self.values)):
            if self.values[idx] is None:
                self.values[idx] = temp.values[idx]
        self.merged = True

    
    def get_temperature(self, time: float):
        steps = len(self.values)
        step = int(time / 86400 * steps) % steps
        value = self.values[step]

        return value


    def get_exposure(self, start: float, end: float) -> float:
        step_num = len(self.values)
        step_size = int(86400 / step_num)
        step_first = int(start / 86400 * step_num)
        step_last = int(end / 86400 * step_num)

        try:
            exposure: float = None
            if self.merged:
                exposure = 0
                exposure -= (start - step_first * step_size) * self.values[step_first % step_num]
                exposure += sum(self.values[step_idx % step_num] * step_size 
                    for step_idx in range(step_first, step_last))
                exposure += (end - step_last * step_size) * self.values[step_last % step_num]
        except Exception as err:
            print(err)
            breakpoint()
        return exposure

        
