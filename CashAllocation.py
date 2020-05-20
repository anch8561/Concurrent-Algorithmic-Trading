# import alpaca api
import alpaca_trade_api as tradeapi
from credentials import creds

# import algo classes
from LongShort import LongShort
from MeanReversion import MeanReversion

# set global parameters
minAllocationCash = 10000
maxAllocationFraction = 0.1

# initialize trade api
alpaca = tradeapi.REST(*creds)
conn = alpaca.StreamConn(*creds)

# initialize algos
longShort = LongShort(minAllocationCash, 0.1)
meanReversion = MeanReversion(minAllocationCash, 0.1, 5)
algos = [longShort, meanReversion]


def distributeFunds():
    account = alpaca.get_account()
    cash = float(account.cash)
    equity = float(account.equity)
    buyingPower = float(account.buying_power)

    # update cash & buyingPower
    for algo in algos:
        cash -= algo.cash
        buyingPower -= algo.cash
    assert(equity >= 25000) # only one of these matters
    assert(cash >= 0) # not sure on the values here
    assert(buyingPower >= 0) # is assert the best way to do this?


def tick():

    # update Algo.stocks

    for algo in algos: algo.tick()


distributeFunds()
while True:
    # StreamConn

    # if beginning of week: distributeFunds()
    # if market open: tick()
