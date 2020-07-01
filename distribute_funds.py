# allocate cash to algos based on risk and performance metrics

from algos import intradayAlgos, overnightAlgos, multidayAlgos
from config import minAllocBuyPow, maxAllocFrac
from warn import warn

def distribute_funds(intradayAlgos, overnightAlgos, multidayAlgos):

    # calculate weights based on performance
    # calculate fractions based on weights and min / max allocations
    # distribute money according to fractions

    for algo in algos: algo.update_metrics()

    # TODO: calculate allocFrac

    for alpaca in (alpacaLive, alpacaPaper):
        for algoType in ('overnight', 'intraday'):
            pass
    # consider overnight, live / paper, fees

    # set live
        # cancel orders once
        # close positions until closed
        # then algo.set_live()


def get_overnight_fee(self, debt):
        # accrues daily (including weekends) and posts at end of month
        return debt * 0.0375 / 360

def get_short_fee(self, debt):
    # accrues daily (including weekends) and posts at end of month

    # ETB (easy to borrow)
    # fee charged for positions held at end of day
    # fee varies from 30 to 300 bps/yr depending on demand

    # HTB (hard to borrow)
    # fee charged for positions held at any point during day
    # fee is higher than maxFee

    # NOTE: is there any way to get actual fee values from alpaca api?
    minFee = debt * 30/1e-4 / 360
    maxFee = debt * 300/1e4 / 360
    return minFee, maxFee


def update_margins():
    # NOTE: this function might not be needed
    initMargin = 0
    maintMargin = 0

    # check positions
    for symbol in positions:
        price = alpaca.polygon.last_quote(symbol)
        quantity = positions[symbol]

        

        initMargin += abs(price * quantity / 2)
        if quantity > 0: # long
            if price < 2.50: maintMargin += price * quantity
            else: maintMargin += price * quantity * 0.3
        elif quantity < 0: # short
            if price < 5.00: maintMargin += max(2.50*quantity, price*quantity)
            else: maintMargin += max(5.00*quantity, 0.3*price*quantity)
        else: warn(f'zero position in {symbol}')

    # check orders
    for order in orders:
        if order['symbol'] not in positions:
            margin += order['price'] * order['quantity']
        else: pass