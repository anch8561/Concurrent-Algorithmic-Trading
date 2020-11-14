import config as c
import globalVariables as g
from algoClass import Algo
from init_logs import init_algo_logs

from logging import Formatter
from os import mkdir

# NOTE: kwargs must be in correct order to generate correct name

# day
def momentum(self): # kwargs: numUpBars, numDownBars
    indicator = str(2) + '_' + self.barFreq + '_momentum'
    
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

def crossover(self): # kwargs: fastNumBars, slowNumBars
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_EMA'
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_EMA'

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if bars[fastInd][-1] > bars[slowInd][-1]: # trend up
                    self.queue_order(symbol, 'buy')
                elif bars[fastInd][-1] < bars[slowInd][-1]: # trend down
                    self.queue_order(symbol, 'sell')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def mom_xo(self): # kwargs: momNumBars, fastNumBars, slowNumBars
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_EMA'
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_EMA'
    momInd = str(2) + '_' + self.barFreq + '_momentum'

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if (
                    bars[fastInd][-1] > bars[slowInd][-1] and # trend up
                    all(bars[momInd][-self.momNumBars:] >= 0) # momentum up
                ):
                    self.queue_order(symbol, 'buy')
                elif (
                    bars[fastInd][-1] < bars[slowInd][-1] and # trend down
                    all(bars[momInd][-self.momNumBars:] <= 0) # momentum down
                ):
                    self.queue_order(symbol, 'sell')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None or
                any(bars[momInd][-self.momNumBars:] == None)
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-self.momNumBars:]}')


def init_day_algos(loadData: bool) -> list:
    algos = []
    # for longShort in ('long', 'short'):
    #     # momentum
    #     for numUpBars in (3, 5, 10):
    #         for numDownBars in (3, 5, 10):
    #             algos.append(Algo('min', momentum, longShort, loadData,
    #                 numUpBars = numUpBars, numDownBars = numDownBars))
        
    #     # moving average crossover
    #     for slowNumBars in (5, 10, 20):
    #         for fastNumBars in (3, 5, 10):
    #             if slowNumBars > fastNumBars:
    #                 algos.append(Algo('min', crossover, longShort, loadData,
    #                     fastNumBars = fastNumBars, slowNumBars = slowNumBars))
        
    #     # combo momentum and crossover
    #     for momNumBars in (2, 3, 4, 5):
    #         for slowNumBars in (5, 10, 20):
    #             for fastNumBars in (3, 5, 10):
    #                 if slowNumBars > fastNumBars:
    #                     algos.append(Algo('min', mom_xo, longShort, loadData,
    #                         momNumBars = momNumBars, fastNumBars = fastNumBars, slowNumBars = slowNumBars))
    algos.append(Algo('min', mom_xo, 'long', loadData,
        momNumBars = 3, fastNumBars = 3, slowNumBars = 10))
        
    return algos

# night
def momentum_volume(self): # kwargs: numBars
    # sort symbols
    # TODO: move to global resource
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

def init_night_algos(loadData: bool) -> list:
    algos = []
    # for longShort in ('long', 'short'):
    #     for numBars in (3, 5, 10):
    #         algos.append(Algo('day', momentum_volume, longShort, loadData, numBars=numBars))
    return algos


# all
def init_algos(loadData: bool, logFmtr: Formatter) -> dict:
    # loadData: whether to load algo data files
    # logFmtr: for custom log formatting

    # create algoPath if needed
    try: mkdir(c.algoPath)
    except: pass

    # create algos
    dayAlgos = init_day_algos(loadData)
    nightAlgos = init_night_algos(loadData)

    # populate dictionary
    algos = {
        'day': dayAlgos,
        'night': nightAlgos,
        'all': dayAlgos + nightAlgos}
    
    # init logs
    init_algo_logs(algos['all'], logFmtr)

    # exit
    return algos
