# functions to be used for enter and exit indications

from Algo import Algo
from warn import warn

# TODO: confirm indices have correct timestamps

class Indicator:
    def __init__(self, func, style, **kwargs):
        self.func = func
        self.style = style
        self.name = func.__name__ + style
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val) + key.capitalize()
    def tick(self):
        if self.style == 'bool' or 'val':
            for asset in Algo.assets.values():
                self.func(asset)
        elif self.style == 'rank':
            self.func()
        else:
            warn(f'unkown indicator style "{self.style}"')

indicators = []

def growth(self, asset):
    openPrice = asset['dayBars'].iloc[-self.days].open
    closePrice = asset['dayBars'].iloc[-1].close
    asset[self.name] = (closePrice - openPrice) / openPrice

indicators.append(Indicator(growth, 'val', days=5))

def volume(self, asset):
    volume = 0
    for day in range(self.days):
        volume += asset['dayBars'].iloc[-day].volume
    asset[self.name] = volume

indicators.append(Indicator(volume, 'val', days=5))
        
def growthRank(self):











