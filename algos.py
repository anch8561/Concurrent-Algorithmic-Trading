# populate algos list

from Algo import Algo
from config import maxPosFrac
import indicators as i

# intraday functions

# intraday algos
intradayAlgos = [

]

# overnight functions
# def dayMomentumVolume(self, TTOpen, TTClose): # kwargs: numDays
#     # rank symbols by momentum*volume
#     valNamePrefix = str(self.numDays) + 'day'
#     sortedSymbols = sorted(list(Algo.assets.keys()), key=lambda symbol:
#         Algo.assets[symbol][valNamePrefix + 'Momentum'][-1] * 
#         Algo.assets[symbol][valNamePrefix + 'Volume_num_stdevs'][-1])

#     numTrades = int(self.buyPow / (self.equity * maxPosFrac))
#     for symbol in sortedSymbols[:numTrades]:
#         self.enterPosition(symbol)

def dayMomentumVolume(self, TTOpen, TTClose): # kwargs: numDays
    numTrades = int(self.buyPow / (self.equity * maxPosFrac))
    # indicatorName = i.Indicator(i.momentum_times_volume_num_stdevs, 5, 'dayBars').name
    for symbol in Algo.rankings['5dayMomentum_times_volume_num_stdevs'][:numTrades]:
        self.enterPosition(symbol)

# overnight algos
overnightAlgos = [
    Algo(
        tick = dayMomentumVolume,
        timeframe = 'overnight',
        equityStyle = 'longShort',
        numDays = 5)
]

# multiday functions

# multiday algos
multidayAlgos = [

]

# all algos list
allAlgos = intradayAlgos + overnightAlgos + multidayAlgos
