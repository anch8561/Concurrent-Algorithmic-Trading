# functions to be used for enter and exit indications
# populate indicators list

from Algo import Algo
from warn import warn

# TODO: confirm indices have correct timestamps

# class
class Indicator:
    def __init__(self, func, style, numBars, barType, **kwargs):
        self.func = func
        self.style = style
        if self.style == 'rank':
            self.valName = Indicator(self.func, 'val', numBars, barType).name
        self.numBars = numBars
        self.barType = barType
        self.name = func.__name__ + str(style).capitalize() + str(numBars) + barType.capitalize()
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val).capitalize()
        
    def tick(self):
        if self.style == 'bool' or 'val':
            for asset in Algo.assets.values():
                val = self.func(asset)
                try: asset[self.name].append(val)
                except: asset[self.name] = [val]
        elif self.style == 'rank':
            assets = sorted(Algo.assets, key=lambda asset: asset[self.valName][-1])
            for rank, asset in enumerate(assets):
                try: asset[self.name].append(rank)
                except: asset[self.name] = [rank]
        else:
            warn(f'unkown indicator style "{self.style}"')

# val functions
def momentum(self, asset):
    openPrice = asset[self.barType].iloc[-self.numBars].open
    closePrice = asset[self.barType].iloc[-1].close
    return (closePrice - openPrice) / openPrice

def volume(self, asset):
    volume = 0
    for day in range(self.days):
        volume += asset['dayBars'].iloc[-day].volume
    asset[self.name] = volume

# bool functions
def positiveMomentum(self, asset):
    valName = Indicator(momentum, 'val', self.numBars, self.barType).name
    return asset[valName] > 0

# instances
indicators = []
for barType in ('secBars', 'minBars', 'dayBars'):
    for numBars in (1, 2, 3, 5, 10, 20):
        indicators.append(Indicator(momentum, 'val', numBars, barType))
        indicators.append(Indicator(momentum, 'rank', numBars, barType))
        indicators.append(Indicator(volume, 'val', numBars, barType))
        indicators.append(Indicator(positiveMomentum, 'bool', numBars, barType))
