# populate algos list

from algoClasses import Algo, DayAlgo, NightAlgo
from config import maxPosFrac

# intraday functions

# intraday algos
intradayAlgos = []

# overnight functions
def dayMomentumVolume(self, TTOpen, TTClose): # kwargs: numDays
    # rank symbols by momentum*volume
    indicatorPrefix = str(self.numDays) + 'day'
    metrics = {}
    for symbol in Algo.assets:
        metrics[symbol] = \
            Algo.assets[symbol][indicatorPrefix + 'Momentum'][-1] * \
            Algo.assets[symbol][indicatorPrefix + 'Volume_num_stdevs'][-1]

    sortedSymbols = sorted(metrics, key=lambda symbol: metrics[symbol])

    # enter long positions
    for symbol in reversed(sortedSymbols):
        if self.longBuyPow < 100: break
        if metrics[symbol] < 0: break
        self.enterPosition(symbol, 'buy')

    # enter short positions
    for symbol in sortedSymbols:
        if self.shortBuyPow < 100: break
        if metrics[symbol] > 0: break
        self.enterPosition(symbol, 'sell')


# overnight algos
overnightAlgos = []
for numDays in (3, 5, 10):
    overnightAlgos += [
        NightAlgo(dayMomentumVolume, numDays=numDays)
    ]

# multiday functions

# multiday algos
multidayAlgos = []

# all algos list
allAlgos = intradayAlgos + overnightAlgos + multidayAlgos
