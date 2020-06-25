# functions to be used for enter and exit indications
# populate indicators list

from algoClasses import Algo
from warn import warn
import statistics as stats

# TODO: confirm indices have correct timestamps

class Indicator:
    def __init__(self, func, numBars, barFreq, **kwargs):
        self.func = func
        self.numBars = numBars # int
        self.barFreq = barFreq # 'sec', 'min', or 'day'
        self.barType = barFreq + 'Bars'
        self.name = str(numBars) + barFreq
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

def volume(self, asset):
    volume = 0
    for bar in range(numBars):
        volume += asset[barType].iloc[-bar].volume
    return volume

def volume_stdev(self, asset):
    volumes = asset[self.barType].iloc[-self.numBars:].loc['volume']
    return stats.stdev(volumes)

def volume_num_stdevs(self, asset):
    _volume = asset[Indicator(volume, 1, self.barFreq).name]
    volumeStdev = asset[Indicator(volume_stdev, self.numBars, self.barFreq).name]
    return  _volume / volumeStdev

# instances
indicators = []
rankings = []
for barType in ('sec', 'min', 'day'):
    for numBars in (1, 2, 3, 5, 10, 20):
        indicators.append(Indicator(momentum, numBars, barType))
        indicators.append(Indicator(volume, numBars, barType))
        indicators.append(Indicator(volume_stdev, numBars, barType))
        indicators.append(Indicator(volume_num_stdevs, numBars, barType))
