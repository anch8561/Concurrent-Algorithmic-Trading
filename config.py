from datetime import timedelta

# file paths
algoPath = 'algos/' # path for algo data files
logPath = 'logs/' # path for log files

# init logs
defaultLogLevel = 'info' # default min log level sent to stderr
criticalEmails = ['ancharters@gmail.com']

# allocate buying power
allocMetricDays = 1
minAllocBuyPow = 10000 # min buying power to allocate to any algo
maxAllocFrac = 0.1 # max fraction of total buying power to allocate to any algo
minLongShortFrac = 0.3 # min fraction of total buying power to allocate long
maxLongShortFrac = 0.7 # max fraction of total buying power to allocate long

# init assets
numAssets = 10 # default number of symbols to stream (-1 means all)
minSharePrice = 20
minDayCashFlow = 1e8
minDaySpread = 0.01
leverageStrings = ('leveraged', '1.5x', '2x', '3x')
numHistoricDays = 20

# main
tickDelay = timedelta(seconds=0.1) # time between last bar received and ticking algos

# queue order
minTradeBuyPow = 100

# get trade qty
maxSectorFrac = 0.1 # unused
maxIndustryFrac = 0.05 # unused
maxPositionFrac = 0.02

# get limit price
limitPriceFrac = 0.001

# tick algos
marketCloseTransitionPeriod = timedelta(minutes=10)

# assertions
assert minTradeBuyPow <= minAllocBuyPow * maxPositionFrac
