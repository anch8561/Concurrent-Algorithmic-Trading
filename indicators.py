import globalVariables as g

import statistics as stats
from logging import getLogger

log = getLogger('indicators')

# TODO: confirm indices have correct timestamps

# class
class Indicator:
    def __init__(self, numBars, barFreq, func, **kwargs):
        self.numBars = numBars # int
        self.barFreq = barFreq # 'sec', 'min', or 'day'
        self.func = func
        self.name = str(numBars) + '_'
        for key, val in kwargs.items(): # e.g. moving average function
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += barFreq + '_' + func.__name__
    
    def get(self, bars):
        # bars: DataFrame
        try: val = self.func(self, bars)
        except Exception as e:
            if len(bars.index) > self.numBars: # bars[0] values may be None
                log.exception(f'{self.name}\n{e}\n{bars}')
            val = None
        return val


# functions
def mom(self, bars):
    # needs at least 2 bars
    openPrice = bars.vwap[-self.numBars]
    closePrice = bars.vwap[-1]
    return closePrice / openPrice - 1

def stdev(self, bars):
    return bars.vwap[-self.numBars:].std()

def vol_stdevs(self, bars):
    volumes = bars.volume[-self.numBars:]
    mean = stats.mean(volumes)
    stdev = stats.stdev(volumes, mean)
    volume = volumes[-1]
    return  (volume - mean) / stdev

def EMA(self, bars):
    if bars[self.name][-2] == None:
        return bars.vwap[-1]
    prev = bars[self.name][-2]
    new = bars.vwap[-1]
    SC = 2/(1+self.numBars) # smoothing constant
    return prev + SC * (new - prev)

def KAMA(self, bars): # kwargs: fastNumBars, slowNumBars
    # numBars is volatility window controlling EMA constant
    if bars[self.name][-2] == None:
        return bars.vwap[-1]
    prev = bars[self.name][-2]
    new = bars.vwap[-1]
    fastSC = 2/(1+self.fastNumBars) # smoothing constants
    slowSC = 2/(1+self.slowNumBars)
    change = abs(new - bars.vwap[-self.numBars])
    volatility = bars.vwap[-self.numBars:].diff().abs().sum()
    ER = change / volatility # efficiency ratio
    SC = (ER * (fastSC - slowSC) + slowSC)**2
    return prev + SC * (new - prev)


# init
def init_indicators(allAlgos: list):
    indicators = {
        'sec': [],
        'min': [],
        'day': [],
        'all': []}

    for algo in allAlgos:
        for indicator in algo.indicators:
            if indicator not in indicators[algo.barFreq]:
                indicators[algo.barFreq].append(indicator)

    return indicators

