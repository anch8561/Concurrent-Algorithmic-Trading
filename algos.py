import config as c
import globalVariables as g
from algoClass import Algo

# NOTE: kwargs must be in correct order to generate correct name

# intraday
def momentum(self): # kwargs: numBars, barFreq
    indicator = str(1) + '_' + self.barFreq + '_momentum'
    # NOTE: could use multibar momentum also
    
    for symbol, bars in g.assets[self.barFreq].items(): # TODO: parallel
        try:
            if not bars.ticked[-1]:
                if all(ii >= 0 for ii in bars[indicator][-self.numUpBars:]): # momentum up
                    self.queue_order(symbol, 'long')
                elif all(ii <= 0 for ii in bars[indicator][-self.numDownBars:]): # momentum down
                    self.queue_order(symbol, 'short')
        except Exception as e:
            if any(bars[indicator][-self.enterNumBars:] == None):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                numBars = max(self.numUpBars, self.numDownBars)
                self.log.exception(f'{symbol}\t{e}\n{bars.iloc[-numBars:]}')

def init_intraday_algos():
    intradayAlgos = []
    for longShort in ('long', 'short'):
        for numUpBars in (1, 2, 3):
            for numDownBars in (1, 2, 3):
                intradayAlgos += [
                    Algo(momentum,
                        longShort,
                        numUpBars = numUpBars,
                        numDownBars = numDownBars,
                        barFreq = 'min')]
    return intradayAlgos

# TODO: momentumMACD

# overnight
def momentum_volume(self): # kwargs: numBars, barFreq
    # sort symbols
    indicatorPrefix = str(self.numBars) + '_' + self.barFreq
    metrics = {}
    for symbol, bars in g.assets[self.barFreq].items():
        try:
            metrics[symbol] = \
                bars[indicatorPrefix + '_momentum'][-1] * \
                bars[indicatorPrefix + '_volume_stdevs'][-1]
        except Exception as e:
            if (
                bars[indicatorPrefix + '_momentum'][-1] == None or
                bars[indicatorPrefix + '_volume_stdevs'][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(e)
    sortedSymbols = sorted(metrics, key=lambda symbol: metrics[symbol])

    # enter long
    for symbol in reversed(sortedSymbols):
        if self.buyPow['long'] < c.minTradeBuyPow: break
        if metrics[symbol] <= 0: break
        self.queue_order(symbol, 'long')

    # enter short
    for symbol in sortedSymbols:
        if self.buyPow['short'] < c.minTradeBuyPow: break
        if metrics[symbol] >= 0: break
        self.queue_order(symbol, 'short')

def init_overnight_algos():
    overnightAlgos = []
    for longShort in ('long', 'short'):
        for numBars in (3, 5, 10):
            overnightAlgos.append(
                Algo(momentum_volume,
                    longShort,
                    numBars=numBars,
                    barFreq='day'))
    return overnightAlgos

# multiday
def crossover(self): # kwargs: barFreq, fastNumBars, fastMovAvg, slowNumBars, slowMovAvg
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_' + self.fastMovAvg
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_' + self.slowMovAvg

    for symbol, bars in g.assets[self.barFreq].items(): # TODO: parallel
        try:
            if not bars.ticked[-1]:
                if bars[fastInd][-1] < bars[slowInd][-1]: # oversold
                    self.queue_order(symbol, 'long')
                elif bars[fastInd][-1] > bars[slowInd][-1]: # overbought
                    self.queue_order(symbol, 'short')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def init_multiday_algos():
    multidayAlgos = []
    for longShort in ('long', 'short'):
        for movAvg in ('SMA', 'EMA', 'KAMA'):
            for slowNumBars in (5, 10, 20):
                for fastNumBars in (3, 5, 10):
                    if slowNumBars > fastNumBars:
                        multidayAlgos += [
                            Algo(crossover,
                                longShort,
                                barFreq = 'day',
                                fastNumBars = fastNumBars,
                                fastMovAvg = movAvg,
                                slowNumBars = slowNumBars,
                                slowMovAvg = movAvg)]
    return multidayAlgos

# all
def init_algos():
    intraday = init_intraday_algos()
    overnight = init_overnight_algos()
    multiday = init_multiday_algos()
    return {
        'intraday': intraday,
        'overnight': overnight,
        'multiday': multiday,
        'all': intraday + overnight + multiday}
