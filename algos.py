# populate algos list

from Algo import Algo
from config import minAllocBP
import indicators as i

intradayAlgos = []
overnightAlgos = [
    Algo( # overnight hold
        buyPow = minAllocBP,
        enterIndicators = [
            i.Indicator(i.momentum, barType='dayBars', numBars=5).name,
            '5DayVolume'],
        exitIndicators = None,
        timeframe = 'overnight',
        equityStyle = 'longShort',
        tickFreq = 'min')
]
multidayAlgos = []
allAlgos = intradayAlgos + overnightAlgos + multidayAlgos
