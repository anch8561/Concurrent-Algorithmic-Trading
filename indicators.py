# functions to be used for enter and exit indications
# populate indicators list

from Algo import Algo
from Ranking import Ranking
from warn import warn
import statistics as stats

# TODO: confirm indices have correct timestamps

class Indicator:
    def __init__(self, func, numBars, barType, **kwargs):
        self.func = func
        self.numBars = numBars # int
        self.barType = barType
        self.name = str(numBars) + barType[:-4]
        for key, val in kwargs.items(): # e.g. moving average function
            self.__setattr__(key, val)
            self.name += str(val).capitalize()
        self.name += func.__name__.capitalize()
    
    def tick(self):
        for asset in Algo.assets.values():
            val = self.func(asset)
            try: asset[self.name].append(val)
            except: asset[self.name] = [val]

# functions
def momentum(self, asset):
    openPrice = asset[self.barType].iloc[-self.numBars].open
    closePrice = asset[self.barType].iloc[-1].close
    return (closePrice - openPrice) / openPrice

def volume(self, asset, numBars=None, barType=None):
    if numBars == None: numBars = self.numBars
    if barType == None: barType = self.barType
    volume = 0
    for bar in range(numBars):
        volume += asset[barType].iloc[-bar].volume
    return volume

def volume_stdev(self, asset):
    volumes = asset[self.barType].iloc[-self.numBars:].volume
    return stats.stdev(volumes)

def volume_num_stdevs(self, asset):
    return volume(None, asset, 1, 'dayBars') / volume_stdev(self, asset)

def momentum_times_volume_num_stdevs(self, asset):
    return momentum(self, asset) * volume_num_stdevs(self, asset)

# instances
indicators = []
rankings = []
for barType in ('secBars', 'minBars', 'dayBars'):
    for numBars in (1, 2, 3, 5, 10, 20):
        # indicators.append(Indicator(momentum, numBars, barType))
        # indicators.append(Indicator(volume, numBars, barType))
        indicators.append(Indicator(momentum_times_volume_num_stdevs, numBars, barType))
        rankings.append(Ranking(indicators[-1]))
