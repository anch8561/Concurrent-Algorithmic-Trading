import g
from algoClasses import DayAlgo, NightAlgo
from config import maxPosFrac, minTradeBuyPow

# intraday
intradayAlgos = []

def momentum(self): # kwargs: enterNumBars, exitNumBars, barFreq
    indicator = str(1) + '_' + self.barFreq + '_momentum'
    # NOTE: could use multibar momentum also
    
    for symbol, bars in g.assets[self.barFreq].items():
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

for exitNumBars in (1, 2, 3, 5):
    for enterNumBars in (1, 2, 3, 5):
        if enterNumBars >= exitNumBars:
            intradayAlgos += [
                DayAlgo(
                    momentum,
                    enterNumBars = enterNumBars,
                    exitNumBars = exitNumBars,
                    barFreq = 'min'
                )
            ]

# TODO: momentumMACD

# overnight
overnightAlgos = []

def momentum_volume(self): # kwargs: numBars
    # sort symbols
    indicatorPrefix = str(self.numBars) + '_' + self.barFreq
    metrics = {}
    for symbol, bars in g.assets[self.barFreq].items():
        try: metrics[symbol] = \
            bars[indicatorPrefix + '_momentum'][-1] * \
            bars[indicatorPrefix + '_volume_num_stdevs'][-1]
        except: pass
    sortedSymbols = sorted(metrics, key=lambda symbol: metrics[symbol])

    # enter long
    for symbol in reversed(sortedSymbols):
        if self.buyPow['long'] < minTradeBuyPow: break
        if metrics[symbol] < 0: break
        self.enter_position(symbol, 'buy')

    # enter short
    for symbol in sortedSymbols:
        if self.buyPow['short'] < minTradeBuyPow: break
        if metrics[symbol] > 0: break
        self.enter_position(symbol, 'sell')

for numBars in (3, 5, 10):
    overnightAlgos.append(
        NightAlgo(momentum_volume, numBars=numBars, barFreq='day'))

# multiday
multidayAlgos = []

def crossover(self): # kwargs: barFreq, fastNumBars, fastMovAvg, slowNumBars, slowMovAvg
    fastInd = str(self.fastNumBars) + '_' + self.barFreq + '_' + self.fastMovAvg
    slowInd = str(self.slowNumBars) + '_' + self.barFreq + '_' + self.slowMovAvg

    for symbol, bars in g.assets[self.barFreq].items():
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

for movAvg in ('SMA', 'EMA', 'KAMA'):
    for slowNumBars in (5, 10, 20):
        for fastNumBars in (3, 5, 10):
            if slowNumBars > fastNumBars:
                multidayAlgos += [
                    DayAlgo(
                        crossover,
                        barFreq = 'day',
                        fastNumBars = fastNumBars,
                        fastMovAvg = movAvg,
                        slowNumBars = slowNumBars,
                        slowMovAvg = movAvg)
                ]

# all algos list
allAlgos = intradayAlgos + overnightAlgos + multidayAlgos
