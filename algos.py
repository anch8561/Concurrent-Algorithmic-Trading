import config as c
import globalVariables as g
from algoClasses import DayAlgo, NightAlgo

# NOTE: kwargs must be in correct order to generate correct name

# intraday
def momentum(self): # kwargs: enterNumBars, exitNumBars, barFreq
    indicator = str(1) + '_' + self.barFreq + '_momentum'
    # NOTE: could use multibar momentum also
    
    for symbol, bars in g.assets[self.barFreq].items(): # TODO: parallel
        try: # check for new bar
            if not bars.ticked[-1]:
                # enter position
                if self.positions[symbol]['qty'] == 0: # no position
                    if all(ii >= 0 for ii in bars[indicator][-self.enterNumBars:]): # momentum up
                        self.enter_position(symbol, 'buy')
                    elif all(ii <= 0 for ii in bars[indicator][-self.enterNumBars:]): # momentum down
                        self.enter_position(symbol, 'sell')
                
                # exit position
                if (
                    (
                        self.positions[symbol]['qty'] > 0 and # long
                        all(ii <= 0 for ii in bars[indicator][-self.exitNumBars:]) # momentum down
                    ) or (
                        self.positions[symbol]['qty'] < 0 and # short
                        all(ii >= 0 for ii in bars[indicator][-self.exitNumBars:]) # momentum up
                    )
                ):
                    self.exit_position(symbol)

        except Exception as e:
            if any(bars[indicator][-self.enterNumBars:] == None):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                numBars = max(self.enterNumBars, self.exitNumBars)
                self.log.exception(f'{symbol}\t{e}\n{bars.iloc[-numBars:]}')

def init_intraday_algos():
    intradayAlgos = []
    for exitNumBars in (1, 2, 3):
        for enterNumBars in (1, 2, 3):
            if enterNumBars >= exitNumBars:
                intradayAlgos += [
                    DayAlgo(momentum,
                        enterNumBars = enterNumBars,
                        exitNumBars = exitNumBars,
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
            if (bars[indicatorPrefix + '_momentum'][-1] == None or
                bars[indicatorPrefix + '_volume_stdevs'][-1] == None):
                self.log.debug(f'{symbol}\tMissing indicator (None)')
            else:
                self.log.exception(e)
    sortedSymbols = sorted(metrics, key=lambda symbol: metrics[symbol])

    # enter long
    for symbol in reversed(sortedSymbols):
        if self.buyPow['long'] < c.minTradeBuyPow: break
        if metrics[symbol] <= 0: break
        self.enter_position(symbol, 'buy')

    # enter short
    for symbol in sortedSymbols:
        if self.buyPow['short'] < c.minTradeBuyPow: break
        if metrics[symbol] >= 0: break
        self.enter_position(symbol, 'sell')

def init_overnight_algos():
    overnightAlgos = []
    for numBars in (3, 5, 10):
        overnightAlgos.append(
            NightAlgo(momentum_volume,
                numBars=numBars,
                barFreq='day'))
    return overnightAlgos

# multiday
def crossover(self): # kwargs: barFreq, fastNumBars, fastMovAvg, slowNumBars, slowMovAvg
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_' + self.fastMovAvg
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_' + self.slowMovAvg

    for symbol, bars in g.assets[self.barFreq].items(): # TODO: parallel
        try: # check for new bar
            if not bars.ticked[-1]:
                # enter position
                if self.positions[symbol]['qty'] == 0: # no position
                    if bars[fastInd][-1] < bars[slowInd][-1]: # oversold
                        self.enter_position(symbol, 'buy')
                    elif bars[fastInd][-1] > bars[slowInd][-1]: # overbought
                        self.enter_position(symbol, 'sell')
                
                # exit position
                if (
                    (
                        self.positions[symbol]['qty'] > 0 and # long
                        bars[fastInd][-1] > bars[slowInd][-1] # overbought
                    ) or (
                        self.positions[symbol]['qty'] < 0 and # short
                        bars[fastInd][-1] < bars[slowInd][-1] # oversold
                    )
                ):
                    self.exit_position(symbol)

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
    for movAvg in ('SMA', 'EMA', 'KAMA'):
        for slowNumBars in (5, 10, 20):
            for fastNumBars in (3, 5, 10):
                if slowNumBars > fastNumBars:
                    multidayAlgos += [
                        DayAlgo(crossover,
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
