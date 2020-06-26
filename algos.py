from algoClasses import Algo, DayAlgo, NightAlgo
from config import maxPosFrac

# intraday
intradayAlgos = []

def momentum(self): # kwargs: enterNumBars, exitNumBars, barFreq
    indicator = str(1) + barFreq + 'Momentum'
    # NOTE: could use multibar momentum also
    
    # TODO: create zero position for each symbol on construction / update_tradable_assets
    for symbol, asset in Algo.assets.items():
        # enter position
        if self.positions[symbol]['qty'] == 0: # no position
            if all(ii >= 0 for ii in asset[indicator][-self.enterNumBars:]): # momentum up
                self.enter_position(symbol, 'buy')
            elif all(ii <= 0 for ii in asset[indicator][-self.enterNumBars:]): # momentum down
                self.enter_position(symbol, 'sell')
        
        # exit position
        if (
            (
                self.positions[symbol]['qty'] > 0 and # long
                all(ii <= 0 for ii in asset[indicator][-self.exitNumBars:]) # momentum down
            ) or (
                self.positions[symbol]['qty'] < 0 and # short
                all(ii >= 0 for ii in asset[indicator][-self.exitNumBars:]) # momentum up
            )
        ):
            self.exit_position(symbol)




for barFreq in ('sec', 'min'):
    for exitNumBars in (1, 2, 3, 5):
        for enterNumBars in (1, 2, 3, 5):
            if enterNumBars >= exitNumBars:
                intradayAlgos += [
                    DayAlgo(
                        momentum,
                        enterNumBars = enterNumBars,
                        exitNumBars = exitNumBars,
                        barFreq = barFreq)
                ]

# TODO: momentumMACD

# overnight
overnightAlgos = []

def dayMomentumVolume(self): # kwargs: numDays
    # 

    # sort symbols
    indicatorPrefix = str(self.numDays) + 'day'
    metrics = {}
    for symbol in Algo.assets:
        metrics[symbol] = \
            Algo.assets[symbol][indicatorPrefix + 'Momentum'][-1] * \
            Algo.assets[symbol][indicatorPrefix + 'Volume_num_stdevs'][-1]

    sortedSymbols = sorted(metrics, key=lambda symbol: metrics[symbol])

    # enter long
    for symbol in reversed(sortedSymbols):
        if self.longBuyPow < 100: break
        if metrics[symbol] < 0: break
        self.enterPosition(symbol, 'buy')

    # enter short
    for symbol in sortedSymbols:
        if self.shortBuyPow < 100: break
        if metrics[symbol] > 0: break
        self.enterPosition(symbol, 'sell')
for numDays in (3, 5, 10):
    overnightAlgos.append(
        NightAlgo(dayMomentumVolume, numDays=numDays))

# multiday
multidayAlgos = []

# all algos list
allAlgos = intradayAlgos + overnightAlgos + multidayAlgos
