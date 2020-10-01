import globalVariables as g

import statistics as stats
import ta
from logging import getLogger

log = getLogger('indicators')

# TODO: confirm indices have correct timestamps

class Indicator: # NOTE: kwargs unused
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
        except Exception as e:
            if len(bars.index) > self.numBars: # bars[0] values may be None
                log.exception(f'{self.name}\n{e}\n{bars}')
            val = None
        return val


## FUNCTIONS

def momentum(self, bars):
    openPrice = bars.open[-self.numBars]
    closePrice = bars.close[-1]
    return (closePrice - openPrice) / openPrice

def volume(self, bars):
    volume = 0
    for i_bar in range(-1, -self.numBars-1, -1):
        volume += bars.volume[i_bar]
    return volume

def volume_stdevs(self, bars):
    volumes = bars.volume[-self.numBars:]
    mean = stats.mean(volumes)
    stdev = stats.stdev(volumes, mean)
    volume = volumes[-1]
    return  (volume - mean) / stdev

# NOTE: typical price unused
def typical_price(self, bars):
    data = bars[-self.numBars:]
    high = data.high.max()
    low = data.low.min()
    close = data.close[-1]
    return (high + low + close) / 3

def SMA(self, bars):
    prices = bars.close[-self.numBars:]
    return ta.trend.sma_indicator(prices, self.numBars)[-1]

def EMA(self, bars):
    prices = bars.close[-self.numBars:]
    return ta.trend.ema_indicator(prices, self.numBars)[-1]

def KAMA(self, bars):
    # variable EMA from 2 to 30 bars (default)
    prices = bars.close[-self.numBars:]
    return ta.momentum.kama(prices, self.numBars)[-1]


def init_indicators():
    indicators = {
        'sec': [],
        'min': [],
        'day': [],
        'all': []
    }


    ## SECOND
    barFreq = 'sec'


    ## MINUTE
    barFreq = 'min'

    # momentum and volume
    for numBars in (1, 3, 5, 10, 20):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, momentum),
            Indicator(numBars, barFreq, volume)]

    # volume stdevs
    for numBars in (3, 5, 10, 20):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, volume_stdevs)]

    ## DAY
    barFreq = 'day'

    # momentum and volume
    for numBars in (1, 3, 5, 10, 20):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, momentum),
            Indicator(numBars, barFreq, volume)]

    # volume stdevs
    for numBars in (3, 5, 10, 20):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, volume_stdevs)]

    # moving averages
    for numBars in (3, 5, 10, 20):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, SMA),
            Indicator(numBars, barFreq, EMA),
            Indicator(numBars, barFreq, KAMA)]


    ## ALL
    for barFreq in g.assets:
        indicators['all'] += indicators[barFreq]
    return indicators
