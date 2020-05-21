# import alpaca api
import alpaca_trade_api as tradeapi
from credentials import *

# import algo classes
from LongShort import LongShort
from MeanReversion import MeanReversion

# set global parameters
minAllocationCash = 10000
maxAllocationFraction = 0.1

# initialize trade api
alpaca = tradeapi.REST(*paper.creds)
conn = alpaca.StreamConn(*paper.creds)

# initialize algos
longShort = LongShort(minAllocationCash, 0.1)
meanReversion = MeanReversion(minAllocationCash, 0.1, 5)
algos = [longShort, meanReversion]


def distributeFunds():
    account = alpaca.get_account()
    cash = float(account.cash) # not sure which values we need
    equity = float(account.equity)
    buyingPower = float(account.buying_power)

    # calculate weights based on performance
    # calculate fractions based on weights and min / max allocations
    # distribute money according to fractions
    for algo in algos:
        algo.cash = algo.allocationFraction*buyingPower


def tick():

    # update Algo.stocks

    for algo in algos: algo.tick() # Parallel thread this


distributeFunds()
while True:
    # StreamConn

    # if beginning of week: distributeFunds()
    # if market open: tick()
