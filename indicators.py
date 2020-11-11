import globalVariables as g

import statistics as stats
import ta
from logging import getLogger

log = getLogger('indicators')

# TODO: confirm indices have correct timestamps

# class
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
        except Exception as e:
            if len(bars.index) > self.numBars: # bars[0] values may be None
                log.exception(f'{self.name}\n{e}\n{bars}')
            val = None
        return val


# functions
def momentum(self, bars):
    openPrice = bars.open[-self.numBars]
    closePrice = bars.close[-1]
    return (closePrice - openPrice) / openPrice

def vwap_mom(self, bars): # unused
    openPrice = bars.vwap[-self.numBars]
    closePrice = bars.vwap[-1]
    return (closePrice - openPrice) / openPrice

def volume_stdevs(self, bars):
    volumes = bars.volume[-self.numBars:]
    mean = stats.mean(volumes)
    stdev = stats.stdev(volumes, mean)
    volume = volumes[-1]
    return  (volume - mean) / stdev

def SMA(self, bars): # unused
    return ta.trend.sma_indicator(bars.vwap, self.numBars)[-1]

def EMA(self, bars):
    return ta.trend.ema_indicator(bars.vwap, self.numBars)[-1]

def KAMA(self, bars):
    # variable EMA from 2 to 30 bars (default)
    # numBars is volatility window controlling EMA window
    return ta.momentum.kama(bars.vwap, self.numBars)[-1]

def bollinger_high(self, bars):
    return ta.volatility.bollinger_hband(bars.close, self.numBars, self.numStdevs)

def bollinger_low(self, bars):
    return ta.volatility.bollinger_lband(bars.close, self.numBars, self.numStdevs)


# init
def init_indicators():
    indicators = {
        'sec': [],
        'min': [],
        'day': [],
        'all': []}


    ## SECOND
    barFreq = 'sec'


    ## MINUTE
    barFreq = 'min'

    # momentum
    numBars = 1
    indicators[barFreq] += [
        Indicator(numBars, barFreq, momentum)]

    # EMA
    for numBars in (3, 5, 10, 20):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, EMA)]


    ## DAY
    barFreq = 'day'

    # momentum
    for numBars in (3, 5, 10):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, momentum)]

    # volume stdevs
    for numBars in (3, 5, 10):
        indicators[barFreq] += [
            Indicator(numBars, barFreq, volume_stdevs)]


    ## ALL
    for barFreq in g.assets:
        indicators['all'] += indicators[barFreq]
    return indicators
