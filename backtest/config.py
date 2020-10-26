from datetime import timedelta

# file paths
algoPath = 'backtest/algos/' # path for algo data files
logPath = 'backtest/logs/' # path for log files

# init logging
defaultLogLevel = 'warning' # default min log level sent to stderr

# allocate buying power
buyPow = 1e5

# init assets
numAssets = 2 # default number of symbols to stream (-1 means all)
leverageStrings = ('leveraged', '1.5x', '2x', '3x')
minSharePrice = 20
minDayCashFlow = 1e8
minDaySpread = 0.01

# main
marketCloseTransitionPeriod = timedelta(minutes=10)
