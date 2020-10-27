from datetime import timedelta

# file paths
algoPath = 'backtest/algos/' # path for algo data files
logPath = 'backtest/logs/' # path for log files

# init logs
defaultLogLevel = 'warning' # default min log level sent to stderr

# allocate buying power
buyPow = 1e5

# init assets
numAssets = 2 # default number of symbols to "stream" (-1 means all)
leverageStrings = ('leveraged', '1.5x', '2x', '3x')
minSharePrice = 20
minDayCashFlow = 1e8
minDaySpread = 0.01

# queue order
minTradeBuyPow = 100

# get trade qty
maxPositionFrac = 0.02

# get limit price
limitPriceFrac = 0.001

# tick algos
marketCloseTransitionPeriod = timedelta(minutes=10)

# assertions
assert minTradeBuyPow <= buyPow * maxPositionFrac
