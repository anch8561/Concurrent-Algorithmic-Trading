# allocate cash to algos based on risk and performance metrics

from alpacaAPI import alpaca, alpacaPaper

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