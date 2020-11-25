import config as c
import globalVariables as g
import indicators as ind
from algoClass import Algo
from indicators import Indicator
from init_logs import init_algo_logs

from logging import Formatter
from os import mkdir

# NOTE: kwargs must be in correct order to generate correct name

# intraday
def mom(self): # kwargs: numUpBars, numDownBars
    indicator = '2_mom'
    
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
    fastInd = str(self.fastNumBars) + '_EMA'
    slowInd = str(self.slowNumBars) + '_EMA'
    stdevInd = str(self.stdevNumBars) + '_stdev'

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if bars[fastInd][-1] - bars[slowInd][-1] > self.numStdevs * bars[stdevInd][-1]: # trend up
                    self.queue_order(symbol, 'buy')
                elif bars[fastInd][-1] - bars[slowInd][-1] < -self.numStdevs * bars[stdevInd][-1]: # trend down
                    self.queue_order(symbol, 'sell')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None or
                bars[stdevInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def KAMA_trend(self): # kwargs: numBars
    fastInd = '10_2_' + str(self.numBars) + '_KAMA'
    slowInd = str(self.numBars) + '_EMA'

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if self.longShort == 'long':
                    if ( # trend up
                        bars[fastInd][-1] - bars[slowInd][-1] > 0.001 * bars.vwap[-1] and
                        bars[slowInd][-1] > bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'buy')
                    elif ( # trend down
                        bars[fastInd][-1] < bars[slowInd][-1] and
                        bars[slowInd][-1] < bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'sell')

                elif self.longShort == 'short':
                    if ( # trend down
                        bars[fastInd][-1] - bars[slowInd][-1] < 0.001 * bars.vwap[-1]  and
                        bars[slowInd][-1] < bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'sell')
                    elif ( # trend up
                        bars[fastInd][-1] > bars[slowInd][-1] and
                        bars[slowInd][-1] > bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'buy')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def KAMA_trend_stdev(self): # kwargs: numBars, numStdevs
    fastInd = '10_1_' + str(self.numBars) + '_KAMA'
    slowInd = str(self.numBars) + '_EMA'
    stdevInd = '20_10_1_5_KAMA_moving_stdev'

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if self.longShort == 'long':
                    if ( # trend up
                        bars[fastInd][-1] - bars[slowInd][-1] > self.numStdevs * bars[stdevInd][-1] and
                        bars[slowInd][-1] > bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'buy')
                    elif ( # trend down
                        bars[fastInd][-1] < bars[slowInd][-1] and
                        bars[slowInd][-1] < bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'sell')

                elif self.longShort == 'short':
                    if ( # trend down
                        bars[fastInd][-1] - bars[slowInd][-1] < -self.numStdevs * bars[stdevInd][-1] and
                        bars[slowInd][-1] < bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'sell')
                    elif ( # trend up
                        bars[fastInd][-1] > bars[slowInd][-1] and
                        bars[slowInd][-1] > bars[slowInd][-2] # filter KAMA slower than slowEMA
                    ):
                        self.queue_order(symbol, 'buy')
        except Exception as e:
            if (
                bars[fastInd][-1] == None or
                bars[slowInd][-1] == None or
                bars[stdevInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')


def KAMA_spread(self): # kwargs: effNumBars, fastNumBars, slowNumBars
    fastInd = str(self.effNumBars) + '_' + str(self.fastNumBars) + '_' + str(self.slowNumBars) + '_KAMA'
    slowInd = str(self.slowNumBars) + '_EMA'
    stdevInd = '20_10_1_5_KAMA_moving_stdev'

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
                bars[slowInd][-1] == None or
                bars[stdevInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')


def stdev_spread(self): # kwargs: numBars, numStdevsEnter, numStdevsExit
    MAInd = f'10_2_30_KAMA'
    stdevInd = f'{self.numBars}_stdev'
    # TODO: close instead of vwap?
    # TODO: do not enter after stop loss

    for symbol, bars in g.assets[self.barFreq].items():
        try:
            if not bars.ticked[-1]:
                if self.longShort == 'long':
                    if bars.vwap[-1] < bars[MAInd][-1] - self.numStdevsEnter * bars[stdevInd][-1]:
                        self.queue_order(symbol, 'buy')
                    elif bars.vwap[-1] > bars[MAInd][-1] + self.numStdevsExit * bars[stdevInd][-1]:
                        self.queue_order(symbol, 'sell')
                elif self.longShort == 'short':
                    if bars.vwap[-1] < bars[MAInd][-1] - self.numStdevsExit * bars[stdevInd][-1]:
                        self.queue_order(symbol, 'buy')
                    elif bars.vwap[-1] > bars[MAInd][-1] + self.numStdevsEnter * bars[stdevInd][-1]:
                        self.queue_order(symbol, 'sell')
        except Exception as e:
            if (
                bars[MAInd][-1] == None or
                bars[stdevInd][-1] == None
            ):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(f'{symbol}\t{e}\n{bars[-1]}')

def init_intraday_algos(loadData: bool) -> list:
    algos = []
    for longShort in ('long', 'short'):
        # KAMA trend
        # MAInd = Indicator(ind.KAMA, effNumBars=10, fastNumBars=1, slowNumBars=5)
        # for numBars in [20]:
        #     for numStdevs in [0.8]:
        #         indicators = [
        #             MAInd, # this must tick before moving_stdev
        #             Indicator(ind.KAMA, effNumBars=10, fastNumBars=1, slowNumBars=numBars),
        #             Indicator(ind.EMA, numBars=numBars),
        #             Indicator(ind.moving_stdev, numBars=20, MAInd=MAInd)]
        #         algos.append(Algo('min', KAMA_trend, indicators, longShort, loadData,
        #             numBars=numBars, numStdevs=numStdevs))

        # stdev spread
        for numBars in [10, 20, 30]:
            for numStdevsEnter in [1.0, 1.5, 2.0]:
                for numStdevsExit in [1.0, 1.5, 2.0]:
                    if numStdevsExit <= numStdevsEnter:
                        indicators = [
                            Indicator(ind.KAMA, effNumBars=10, fastNumBars=2, slowNumBars=30),
                            Indicator(ind.stdev, numBars=numBars)]
                        algos.append(Algo('min', stdev_spread, indicators, longShort, loadData,
                            numBars=numBars, numStdevsEnter=numStdevsEnter, numStdevsExit=numStdevsExit))
        # for numBars in [10, 20]:
        #     for numStdevsEnter in [1.0, 1.5]:
        #         for numStdevsExit in [1.0, 1.5]:
        #             if numStdevsExit <= numStdevsEnter:
        #                 indicators = [
        #                     Indicator(ind.KAMA, effNumBars=10, fastNumBars=2, slowNumBars=30),
        #                     Indicator(ind.stdev, numBars=numBars)]
        #                 algos.append(Algo('min', stdev_spread, indicators, longShort, loadData,
        #                     numBars=numBars, numStdevsEnter=numStdevsEnter, numStdevsExit=numStdevsExit))
        # for numBars in [30]:
        #     for numStdevsEnter in [1.0, 1.5, 2.0]:
        #         for numStdevsExit in [1.0, 1.5, 2.0]:
        #             if numStdevsExit <= numStdevsEnter:
        #                 indicators = [
        #                     Indicator(ind.KAMA, effNumBars=10, fastNumBars=2, slowNumBars=30),
        #                     Indicator(ind.stdev, numBars=numBars)]
        #                 algos.append(Algo('min', stdev_spread, indicators, longShort, loadData,
        #                     numBars=numBars, numStdevsEnter=numStdevsEnter, numStdevsExit=numStdevsExit))
        
        # KAMA spread
        # for slowNumBars in (5, 10, 20):
        #     for fastNumBars in (3, 5, 10):
        #         if slowNumBars > fastNumBars:
        #             for effNumBars in (10, 20, 30):
        #                 algos.append(Algo('min', KAMA_spread, longShort, loadData,
        #                     effNumBars=effNumBars, fastNumBars=fastNumBars, slowNumBars=slowNumBars))

    return algos

# overnight
def mom_vol(self): # kwargs: numBars
    # sort symbols
    # TODO: move to global resource
    indPrefix = str(self.numBars)
    metrics = {}
    for symbol, bars in g.assets[self.barFreq].items():
        try:
            metrics[symbol] = \
                bars[indPrefix + '_mom'][-1] * \
                bars[indPrefix + '_vol_stdevs'][-1]
        except Exception as e:
            if (
                bars[indPrefix + '_mom'][-1] == None or
                bars[indPrefix + '_vol_stdevs'][-1] == None
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
