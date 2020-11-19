import config as c
import globalVariables as g
from algoClass import Algo
from init_logs import init_algo_logs

from logging import Formatter
from os import mkdir

# NOTE: kwargs must be in correct order to generate correct name

# intraday
def mom(self): # kwargs: numUpBars, numDownBars
    indicator = str(2) + '_' + self.barFreq + '_mom'
    
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

# TODO: mom_MACD

def xo(self): # kwargs: fastNumBars, slowNumBars, stdevNumBars, numStdevs
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_EMA'
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_EMA'
    stdevInd = str(self.stdevNumBars) + '_' + self.barFreq + '_stdev'

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if bars[fastInd][-1] - bars[slowInd][-1] > self.numStdevs * bars[stdevInd][-1]: # trend up
                    self.queue_order(symbol, 'buy')
                elif bars[fastInd][-1] - bars[slowInd][-1] < self.numStdevs * bars[stdevInd][-1]: # trend down
                    self.queue_order(symbol, 'sell')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def bol(self): # kwargs: numBars, numStdevs
    pass

def bol_kama(self): # kwargs: numBars, numStdevs
    pass


def init_intraday_algos(loadData: bool) -> list:
    algos = []
    for longShort in ('long', 'short'):
        # moving average crossover
        for slowNumBars in (5, 10, 20):
            for fastNumBars in (3, 5, 10):
                if slowNumBars > fastNumBars:
                    for stdevNumBars in (10, 20, 30):
                        for numStdevs in (0.5, 1, 1.5):
                            algos.append(Algo('min', xo, longShort, loadData,
                                fastNumBars=fastNumBars, slowNumBars=slowNumBars,
                                stdevNumBars=stdevNumBars, numStdevs=numStdevs))
    return algos

# overnight
def mom_vol(self): # kwargs: numBars
    # sort symbols
    # TODO: move to global resource
    indicatorPrefix = str(self.numBars) + '_' + self.barFreq
    metrics = {}
    for symbol, bars in g.assets[self.barFreq].items():
        try:
            metrics[symbol] = \
                bars[indicatorPrefix + '_mom'][-1] * \
                bars[indicatorPrefix + '_vol_stdevs'][-1]
        except Exception as e:
            if (
                bars[indicatorPrefix + '_mom'][-1] == None or
                bars[indicatorPrefix + '_vol_stdevs'][-1] == None
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

def init_overnight_algos(loadData: bool) -> list:
    algos = []
    # for longShort in ('long', 'short'):
    #     for numBars in (3, 5, 10):
    #         algos.append(Algo('day', mom_vol, longShort, loadData, numBars=numBars))
    return algos


# all
def init_algos(loadData: bool, logFmtr: Formatter) -> dict:
    # loadData: whether to load algo data files
    # logFmtr: for custom log formatting

    # create algoPath if needed
    try: mkdir(c.algoPath)
    except: pass

    # create algos
    intradayAlgos = init_intraday_algos(loadData)
    overnightAlgos = init_overnight_algos(loadData)

    # populate dictionary
    algos = {
        'intraday': intradayAlgos,
        'overnight': overnightAlgos,
        'all': intradayAlgos + overnightAlgos}
    
    # init logs
    init_algo_logs(algos['all'], logFmtr)

    # exit
    return algos
