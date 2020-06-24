# functions to be used for enter and exit indications
# populate indicators list

from Algo import Algo
from warn import warn
import statistics as stats

# TODO: confirm indices have correct timestamps

# classes
class Indicator:
    def __init__(self, func, style, numBars, barType, **kwargs):
        self.func = func
        self.numBars = numBars # int
        self.barType = barType
        self.name = str(numBars) + barType.capitalize()
        for key, val in kwargs.items(): # e.g. moving average function
            self.__setattr__(key, val)
            self.name += str(val).capitalize()
        self.name += func.__name__

class ValIndicator(Indicator):
    def __init__(self, func, numBars, barType, **kwargs):
        super.__init__(func, numBars, barType, kwargs)
        self.name += 'Val'

    def tick(self):
        for asset in Algo.assets.values():
            val = self.func(asset)
            try: asset[self.name].append(val)
            except: asset[self.name] = [val]

class RankIndicator(Indicator):
    def __init__(self, func, numBars, barType, **kwargs):
        super.__init__(func, numBars, barType, kwargs)
        self.valName = Indicator(self.func, 'val', numBars, barType).name
        self.name += 'Rank'

    def tick(self):
        assets = sorted(Algo.assets, key=lambda asset: asset[self.valName][-1])
        for rank, asset in enumerate(assets):
            try: asset[self.name].append(rank)
            except: asset[self.name] = [rank]

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

def overnight_hold(self, asset):
    return momentum(self, asset) * volume_num_stdevs(self, asset)

# instances
indicators = []
for barType in ('secBars', 'minBars', 'dayBars'):
    for numBars in (1, 2, 3, 5, 10, 20):
        indicators.append(ValIndicator(momentum, numBars, barType))
        indicators.append(ValIndicator(overnight_hold, numBars, barType))
        indicators.append(RankIndicator(overnight_hold, numBars, barType))

# example
# conditions compare indicator values or ranks against other indicator values or ranks, algo variables, or constants
# it may need access to algo scope to get variables such as rank limits (e.g. top 25 if that's how many positions we can afford to enter)
# is there some other way to pass in extra variables? (while keeping it modular)
enterConditions = [
    lambda asset: asset['momentumVal5Day'] > asset['momentumVal1Day'],
    lambda asset: asset['momentumVal5Day'] > 0,
    lambda self, asset: asset['momentumVal5day'] < self.momentumLimit, # this has same args as val functions above...
    lambda self, asset: asset['momentumRank5day'] <= self.numTradesToPlace # but self refers to algo, not indicator
]
