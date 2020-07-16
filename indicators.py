import globalVariables as g
from warn import warn

import ta
import statistics as stats

# TODO: confirm indices have correct timestamps

class Indicator:
    def __init__(self, numBars, barFreq, func, **kwargs):
        self.numBars = numBars # int
        self.barFreq = barFreq # 'sec', 'min', or 'day'
        self.func = func
        self.name = str(numBars) + '_' + barFreq + '_'
        for key, val in kwargs.items(): # e.g. moving average function
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += func.__name__
    
    def get(self, bars):
        # bars: DataFrame
        try: val = self.func(self, bars)
        except: val = None
        return val


## FUNCTIONS
def momentum(self, bars):
    openPrice = bars.iloc[-self.numBars].open
    closePrice = bars.iloc[-1].close
    return (closePrice - openPrice) / openPrice

def volume(self, bars):
    volume = 0
    for i_bar in range(-1, -self.numBars-1, -1):
        volume += bars.iloc[i_bar].volume
    return volume

def volume_stdev(self, bars):
    volumes = bars.iloc[-self.numBars:].volume
    return stats.stdev(volumes)

def volume_num_stdevs(self, bars):
    _volume = bars[Indicator(volume, 1, self.barFreq).name][-1]
    volumeStdev = bars[Indicator(volume_stdev, self.numBars, self.barFreq).name][-1]
    return  _volume / volumeStdev

def typical_price(self, bars):
    data = bars.iloc[-1]
    high = data.high
    low = data.low
    close = data.close
    for i_bar in range(-2, -self.numBars-1, -1):
        data = bars.iloc[i_bar]
        if data.high > high: high = data.high
        if data.low < low: low = data.low
    return (high + low + close) / 3

def SMA(self, bars):
    prices = bars.iloc[-self.numBars:].close
    return ta.trend.sma_indicator(prices, self.numBars)[-1]

def EMA(self, bars):
    prices = bars.iloc[-self.numBars:].close
    return ta.trend.ema_indicator(prices, self.numBars)[-1]

def KAMA(self, bars):
    # variable EMA from 2 to 30 bars (default)
    prices = bars.iloc[-self.numBars:].close
    return ta.momentum.kama(prices, self.numBars)[-1]


## INDICATORS DICTIONARY
indicators = {
    'sec': [],
    'min': [],
    'day': [],
    'all': []
}


## SECOND INDICATORS
barFreq = 'sec'


## MINUTE INDICATORS
barFreq = 'min'

# momentum and volume
for numBars in (1, 3, 5, 10, 20):
    indicators[barFreq] += [
        Indicator(numBars, barFreq, momentum),
        Indicator(numBars, barFreq, volume),
        Indicator(numBars, barFreq, volume_stdev),
        Indicator(numBars, barFreq, volume_num_stdevs)
    ]


## DAY INDICATORS
barFreq = 'day'

# momentum and volume
for numBars in (1, 3, 5, 10, 20):
    indicators[barFreq] += [
        Indicator(numBars, barFreq, momentum),
        Indicator(numBars, barFreq, volume),
        Indicator(numBars, barFreq, volume_stdev),
        Indicator(numBars, barFreq, volume_num_stdevs)
    ]

# moving averages
for numBars in (3, 5, 10, 20):
    indicators[barFreq] += [
        Indicator(numBars, barFreq, SMA),
        Indicator(numBars, barFreq, EMA),
        Indicator(numBars, barFreq, KAMA)
    ]


## ALL INDICATORS
for barFreq in g.assets:
    indicators['all'] += indicators[barFreq]
