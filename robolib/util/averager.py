import numpy as np

class Averager:
    def add_value(self, value: float):
        pass

    def get_average(self) -> float:
        pass


class ArithmeticAverager(Averager):
    def __init__(self):
        self.sum = 0
        self.amount = 0

    def __add__(self, other: float):
        self.add_value(other)
        return self

    def __float__(self):
        return self.get_average()

    def add_value(self, value: float):
        self.sum += float(value)
        self.amount += 1

    def get_average(self) -> float:
        return self.sum / self.amount


class AdvancedAverager(Averager):
    def __init__(self):
        self.values = []
        self.sight = 6

    def __add__(self, other: float):
        self.add_value(other)
        return self

    def __float__(self):
        return self.get_average()

    def add_value(self, value: float):
        # index = int(np.searchsorted(self.values, value, side='right'))
        # self.values = np.insert(self.values, index, value)
        self.values = np.append(self.values, value)

    def get_average(self) -> float:
        return np.average([np.average(self.values), np.median(self.values)])
