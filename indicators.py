# functions to be used for enter and exit indications
# populate indicators list

from Algo import Algo
from warn import warn

# TODO: confirm indices have correct timestamps

# class
class Indicator:
    def __init__(self, func, style, numBars, barType, **kwargs):
        self.func = func
        self.style = style # 'val' or 'rank'
        if self.style == 'rank': # val indicator must be ticked first
            self.valName = Indicator(self.func, 'val', numBars, barType).name
        self.numBars = numBars
        self.barType = barType
        self.name = func.__name__ + str(style).capitalize() + str(numBars) + barType.capitalize()
        for key, val in kwargs.items(): # e.g. moving average function
            self.__setattr__(key, val)
            self.name += str(val).capitalize()
        
    def tick(self):
        if self.style == 'val':
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
    for bar in range(self.numBars):
        volume += asset[self.barType].iloc[-bar].volume
    asset[self.name] = volume

# instances
indicators = []
for barType in ('secBars', 'minBars', 'dayBars'):
    for numBars in (1, 2, 3, 5, 10, 20):
        indicators.append(Indicator(momentum, 'val', numBars, barType))
        indicators.append(Indicator(momentum, 'rank', numBars, barType))
        # indicators.append(Indicator(momentum, '>', numBars, barType, val=0))
        indicators.append(Indicator(volume, 'val', numBars, barType))

# class Condition:
#     def __init__(self, left, comparitor, right):
#         self.left = left
#         self.comparitor = comparitor
#         self.right = right
    
#     def check(self):
#         if self.comparitor == '<': return self.left() < self.right()

# example
# conditions compare indicator values or ranks against other indicator values or ranks, algo variables, or constants
# it may need access to algo scope to get variables such as rank limits (e.g. top 25 if that's how many positions we can afford to enter)
# is there some other way to pass in extra variables? (while keeping it modular)
algo.enterConditions = [
    lambda asset: asset['momentumVal5Day'] > asset['momentumVal1Day'],
    lambda asset: asset['momentumVal5Day'] > 0,
    lambda self, asset: asset['momentumVal5day'] < self.momentumLimit, # this has same args as val functions above...
    lambda self, asset: asset['momentumRank5day'] <= self.numTradesToPlace # but self refers to algo, not indicator
]
