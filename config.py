from datetime import timedelta

algoPath = 'algos/'

verbose = True

minAllocBuyPow = 10000
maxAllocFrac = 0.1

minLongShortFrac = 0.3
maxLongShortFrac = 0.7

allocMetricDays = 1

maxSectorFrac = 0.1
maxIndustryFrac = 0.05
maxPosFrac = 0.1

minSharePrice = 20
minDayVolume = 200000
leverageStrings = ('leveraged', '1.5x', '2x', '3x')

minTradeBuyPow = 100
minLongPrice = 3
minShortPrice = 17

barTimeout = 2.5 # number of bar periods without new bar before asset is removed
tickDelay = timedelta(seconds=1) # time between last bar received and ticking algos

numHistoricDays = 20

marketCloseTransitionPeriod = timedelta(minutes=10)

limitPriceFrac = 0.02
