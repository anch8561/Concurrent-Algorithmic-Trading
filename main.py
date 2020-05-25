from alpacaAPI import alpaca, alpacaPaper
from distribute_funds import distribute_funds
from marketHours import *

# import algo classes
from LongShort import LongShort
from MeanReversion import MeanReversion
from ReturnsReversion import ReturnsReversion

# set global parameters
# NOTE: these should either be in distributeFunds.py or config.py
minAllocCash = 10000
maxAllocFrac = 0.1

# initialize algos
longShort = LongShort(minAllocCash, 0.01)
meanReversion = MeanReversion(minAllocCash, 0.01, 7)
returnsReversion7 = returnsReversion(minAllocCash, 0.01, 7)
returnsReversion30 = returnsReversion(minAllocCash, 0.01, 30)
returnsReversion90 = returnsReversion(minAllocCash, 0.01, 90)
algos = [longShort, meanReversion, returnsReversion]

# TODO: dataStreaming

def tick():

    # update Algo.stocks

    for algo in algos: algo.tick() # Parallel thread this


distribute_funds(algos)
while True:
    # StreamConn

    # if beginning of week: distributeFunds()
    # if market open: tick()
