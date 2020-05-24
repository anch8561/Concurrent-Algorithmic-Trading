from alpacaAPI import alpaca, alpacaPaper
from distributeFunds import distributeFunds
from marketHours import *

# import algo classes
from LongShort import LongShort
from MeanReversion import MeanReversion

# set global parameters
minAllocationCash = 10000
maxAllocationFraction = 0.1

# initialize algos
longShort = LongShort(minAllocationCash, 0.01)
meanReversion = MeanReversion(minAllocationCash, 0.01, 7)
algos = [longShort, meanReversion]

# TODO: dataStreaming

def tick():

    # update Algo.stocks

    for algo in algos: algo.tick() # Parallel thread this


distributeFunds()
while True:
    # StreamConn

    # if beginning of week: distributeFunds()
    # if market open: tick()
