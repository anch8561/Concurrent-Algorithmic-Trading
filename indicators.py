import globalVariables as g

import statistics as stats
from logging import getLogger

log = getLogger('indicators')

# TODO: confirm indices have correct timestamps

# class
class Indicator:
    def __init__(self, barFreq, func, name=None, **kwargs):
        self.barFreq = barFreq # 'sec', 'min', or 'day'
        self.func = func
        self.name = ''
        for key, val in kwargs.items(): # e.g. moving average function
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += barFreq + '_' + func.__name__
        if name: self.name = name
    
    def get(self, bars):
        # bars: DataFrame
        try: return self.func(self, bars)
        except Exception as e:
            try: # may have numBars kwarg
                if len(bars.index) > self.numBars: # bars[0] values may be None
                    log.exception(f'{self.name}\n{e}\n{bars}')
            except:
                if len(bars.index) > 1: # bars[0] values may be None
                    log.exception(f'{self.name}\n{e}\n{bars}')
            return None


# plotting
def diff(self, bars): # kwargs: ind1, ind2
    try:
        val1 = self.ind1.get(bars)
        ii = bars.columns.get_loc(self.ind1.name)
        bars.iloc[-1, ii] = val1

        val2 = self.ind2.get(bars)
        ii = bars.columns.get_loc(self.ind2.name)
        bars.iloc[-1, ii] = val2

        return val1 - val2
    except: return None

def neg(self, bars): # kwargs: ind
    return -self.ind.get(bars)


# functions
def mom(self, bars): # kwargs: numBars
    # needs at least 2 bars
    openPrice = bars.vwap[-self.numBars]
    closePrice = bars.vwap[-1]
    return closePrice / openPrice - 1

def stdev(self, bars): # kwargs: numBars
    return bars.vwap[-self.numBars:].std()

def moving_stdev(self, bars): # kwargs: numBars, MAInd
    # NOTE: must add MA column

    # get EMA
    val = self.MAInd.get(bars)
    ii = bars.columns.get_loc(self.MAInd.name)
    bars.iloc[-1, ii] = val

    # get stdev
    vec = bars.vwap[-self.numBars:] - bars[self.MAInd.name][-self.numBars:]
    return vec.abs().sum() / (self.numBars - 1)**0.5

def vol_stdevs(self, bars): # kwargs: numBars
    volumes = bars.volume[-self.numBars:]
    mean = volumes.mean()
    stdev = volumes.std()
    volume = volumes[-1]
    return  (volume - mean) / stdev

def EMA(self, bars): # kwargs: numBars
    # 1st val
    if bars[self.name][-2] == None:
        return bars.vwap[-1]
    
    # prices
    prev = bars[self.name][-2]
    new = bars.vwap[-1]

    # smoothing constant
    SC = 2/(1+self.numBars)

    # typical val
    return prev + SC * (new - prev)

def KAMA(self, bars): # kwargs: effNumBars, fastNumBars, slowNumBars
    # numBars is volatility window controlling EMA constant
    try:
        # 1st val
        if bars[self.name][-2] == None:
            return bars.vwap[-1]
        
        # prices
        prev = bars[self.name][-2]
        new = bars.vwap[-1]

        # efficiency ratio
        change = abs(new - bars.vwap[-self.effNumBars])
        volatility = bars.vwap[-self.effNumBars:].diff().abs().sum()
        ER = change / volatility

        # smoothing constants
        fastSC = 2/(1+self.fastNumBars)
        slowSC = 2/(1+self.slowNumBars)
        SC = (ER * (fastSC - slowSC) + slowSC)**2

        # typical val
        return prev + SC * (new - prev)

    except Exception as e:
        numBars = max(self.effNumBars, self.fastNumBars, self.slowNumBars)
        if len(bars.index) > numBars:
            log.exception(f'{self.name}\n{e}\n{bars}')
        return None


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

