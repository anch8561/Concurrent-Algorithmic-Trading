from datetime import timedelta

# file paths
resultsPath = 'backtesting/backtests/' # path for backtest results
savedBarPath = 'backtesting/bars/' # path for previously downloaded barsets

# init logs
defaultLogLevel = 'info' # default min log level sent to stderr

# allocate buying power
buyPow = 1e5

# init assets
numAssets = 10 # default number of symbols to "stream" (-1 means all)
leverageStrings = ('leveraged', '1.5x', '2x', '3x')
minSharePrice = 20
minDayCashFlow = 1e8
minDaySpread = 0.01

# queue order
minTradeBuyPow = 100

# get trade qty
maxPositionFrac = 0.1

# price fractions
limitPriceFrac = 0
stopLossFrac = 0.001

# tick algos
marketCloseTransitionPeriod = timedelta(minutes=10)

# assertions
assert minTradeBuyPow <= buyPow * maxPositionFrac
