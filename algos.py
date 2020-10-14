import config as c
import globalVariables as g
from algoClass import Algo

# NOTE: kwargs must be in correct order to generate correct name

# day
def momentum(self): # kwargs: numUpBars, numDownBars, barFreq
    indicator = str(1) + '_' + self.barFreq + '_momentum'
    # NOTE: could use multibar momentum also
    
    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if all(bars[indicator][-self.numUpBars:] >= 0): # momentum up
                    self.queue_order(symbol, 'buy')
                elif all(bars[indicator][-self.numDownBars:] <= 0): # momentum down
                    self.queue_order(symbol, 'sell')
        except Exception as e:
            numBars = max(self.numUpBars, self.numDownBars)
            if any(bars[indicator][-numBars:] == None): # FIX: not working
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars.iloc[-numBars:]}')

# TODO: momentumMACD

def crossover(self): # kwargs: barFreq, fastNumBars, fastMovAvg, slowNumBars, slowMovAvg
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_' + self.fastMovAvg
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_' + self.slowMovAvg

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if bars[fastInd][-1] < bars[slowInd][-1]: # oversold
                    self.queue_order(symbol, 'buy')
                elif bars[fastInd][-1] > bars[slowInd][-1]: # overbought
                    self.queue_order(symbol, 'sell')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def init_day_algos() -> list:
    algos = []
    for longShort in ('long', 'short'):
        # momentum
        for numUpBars in (1, 2, 3):
            for numDownBars in (1, 2, 3):
                algos += [
                    Algo(momentum,
                        longShort,
                        numUpBars = numUpBars,
                        numDownBars = numDownBars,
                        barFreq = 'min')]
        
        # moving average crossover
        for movAvg in ('SMA', 'EMA', 'KAMA'): # TODO: try combos
            for slowNumBars in (5, 10, 20):
                for fastNumBars in (3, 5, 10):
                    if slowNumBars > fastNumBars:
                        algos += [
                            Algo(crossover,
                                longShort,
                                barFreq = 'min',
                                fastNumBars = fastNumBars,
                                fastMovAvg = movAvg,
                                slowNumBars = slowNumBars,
                                slowMovAvg = movAvg)]
    return algos

# night
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

    # enter positions
    if self.longShort == 'long':
        for symbol in reversed(sortedSymbols):
            if self.buyPow < c.minTradeBuyPow: break
            if metrics[symbol] <= 0: break
            self.queue_order(symbol, 'buy')
    else:
        for symbol in sortedSymbols:
            if self.buyPow < c.minTradeBuyPow: break
            if metrics[symbol] >= 0: break
            self.queue_order(symbol, 'sell')

def init_night_algos() -> list:
    algos = []
    for longShort in ('long', 'short'):
        for numBars in (3, 5, 10):
            algos.append(
                Algo(momentum_volume,
                    longShort,
                    numBars=numBars,
                    barFreq='day'))
    return algos


# all
def init_algos() -> dict:
    dayAlgos = init_day_algos()
    nightAlgos = init_night_algos()
    return {
        'day': dayAlgos,
        'night': nightAlgos,
        'all': dayAlgos + nightAlgos}
