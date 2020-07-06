from algos import intradayAlgos, overnightAlgos, multidayAlgos
from alpacaAPI import alpacaLive, alpacaPaper
from config import minAllocBuyPow, maxAllocFrac, minLongShortFrac, maxLongShortFrac
from warn import warn

import numpy as np
import scipy.optimize as opt

buyPow = 200000 # FIX: for testing
regTBuyPow = 100000

def distribute_funds():
    # get performance weights
    w = []
    for algos in (intradayAlgos, overnightAlgos, multidayAlgos):
        for algo in algos:
            metrics = algo.get_metrics()
            w.append(metrics['mean']['long'])
            w.append(metrics['mean']['short'])
        
    w = np.array(w)

    # get weight region lengths
    n = len(w)
    n_intraday = len(intradayAlgos) * 2
    n_overnight = len(overnightAlgos) * 2
    n_multiday = len(multidayAlgos) * 2

    # set opt func
    func = lambda x: - x * w

    # set initial guess
    x0 = [0] * n

    # set allcoation bounds
    bounds = opt.Bounds(
        lb = [0] * n,
        ub = [maxAllocFrac] * n
    )
    
    # set allocation constraints
    constraints = opt.LinearConstraint(
        A = [
            [1] * n, # sum <= 1

            [1, -1] * (n/2), # long == short

            # overnight + multiday <= regT
            [0] * n_intraday + [1] * (n_overnight + n_multiday),

            # intraday - overnight <= daytrading - regT
            [1] * n_intraday + [-1] * n_overnight + [0] * n_multiday
        ],
        lb = [
            0, # sum <= 1
            minLongShortFrac * 2 - 1, # long == short
            0, # overnight + multiday <= regT
            0 # intraday - overnight <= daytrading - regT
        ],
        ub = [
            1, # sum <= 1
            maxLongShortFrac * 2 - 1, # long == short
            regTBuyPow, # overnight + multiday <= regT
            buyPow - regTBuyPow # intraday - overnight <= daytrading - regT
        ]
    )

    # solve
    x = opt.minimize(func, x0, 
        bounds = bounds,
        constraints = constraints)

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
