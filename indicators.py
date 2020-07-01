from algoClasses import Algo
import statistics as stats
import ta
from warn import warn

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
            val = self.func(self, asset)
            try: asset[self.name].append(val)
            except: asset[self.name] = [val]


## FUNCTIONS
def momentum(self, asset):
    openPrice = asset[self.barType].iloc[-self.numBars].open
    closePrice = asset[self.barType].iloc[-1].close
    return (closePrice - openPrice) / openPrice

def volume(self, asset):
    volume = 0
    for i_bar in range(-1, -self.numBars-1, -1):
        volume += asset[self.barType].iloc[i_bar].volume
    return volume

def volume_stdev(self, asset):
    volumes = asset[self.barType].iloc[-self.numBars:].loc['volume']
    return stats.stdev(volumes)

def volume_num_stdevs(self, asset):
    _volume = asset[Indicator(volume, 1, self.barFreq).name]
    volumeStdev = asset[Indicator(volume_stdev, self.numBars, self.barFreq).name]
    return  _volume / volumeStdev

def typical_price(self, asset):
    data = asset[self.barType].iloc[-1]
    high = data.high
    low = data.low
    close = data.close
    for i_bar in range(-2, -self.numBars-1, -1):
        data = asset[self.barType].iloc[i_bar]
        if data.high > high: high = data.high
        if data.low < low: low = data.low
    return (high + low + close) / 3

def SMA(self, asset):
    prices = asset[self.barType].iloc[-self.numBars:].close
    return ta.trend.sma_indicator(prices, self.numBars)

def EMA(self, asset):
    prices = asset[self.barType].iloc[-self.numBars:].close
    return ta.trend.ema_indicator(prices, self.numBars)

def KAMA(self, asset):
    # variable EMA from 2 to 30 bars (default)
    prices = asset[self.barType].iloc[-self.numBars:].close
    return ta.momentum.kama(prices, self.numBars)


## INSTANCES
indicators = []

# momentum and volume
for barFreq in ('min'):
    for numBars in (1, 2, 3, 5, 10, 20):
        indicators += [
            Indicator(momentum, numBars, barFreq),
            Indicator(volume, numBars, barFreq),
            Indicator(volume_stdev, numBars, barFreq),
            Indicator(volume_num_stdevs, numBars, barFreq)
        ]
    
# moving averages
barFreq = 'day'
for numBars in (3, 5, 10, 20):
    indicators += [
        Indicator(SMA, numBars, barFreq),
        Indicator(EMA, numBars, barFreq),
        Indicator(KAMA, numBars, barFreq)
    ]
