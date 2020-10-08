from datetime import timedelta

algoPath = 'algos/' # path for algo data files
logPath = 'logs/' # path for log files

numAssets = 10 # number of symbols to stream (-1 means all)

minAllocBuyPow = 10000 # min buying power to allocate to any algo
maxAllocFrac = 0.1 # max fraction of total buying power to allocate to any algo

minLongShortFrac = 0.3 # min fraction of total buying power to allocate to longs
maxLongShortFrac = 0.7 # max fraction of total buying power to allocate to longs

allocMetricDays = 1

maxSectorFrac = 0.1
maxIndustryFrac = 0.05
maxPosFrac = 0.1

minSharePrice = 20
minDayVolume = 200000
leverageStrings = ('leveraged', '1.5x', '2x', '3x')

minTradeBuyPow = 100 # must be < minAllocBuyPow * maxPosFrac

barTimeout = 2.5 # number of bar periods without new bar before asset is removed
tickDelay = timedelta(seconds=0.1) # time between last bar received and ticking algos

numHistoricDays = 20

marketCloseTransitionPeriod = timedelta(minutes=10)

volumeLimitMult = 0.1 # max order qty relative to prev bar volume
limitPriceFrac = 0.001

# logging
defaultLogLevel = 'info' # min log level sent to stderr
criticalEmails = ['ancharters@gmail.com']
