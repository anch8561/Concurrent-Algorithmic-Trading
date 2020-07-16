from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from alpacaAPI import alpacaLive, alpacaPaper
from config import verbose, minAllocBuyPow, maxAllocFrac, minLongShortFrac, maxLongShortFrac, allocMetricDays
from warn import warn

import numpy as np
import scipy.optimize as opt

def allocate_buying_power():
    print('Allocating buying power')

    # get buying power
    account = alpacaPaper.get_account() # FIX: paper
    buyPow = float(account.daytrading_buying_power)
    regTBuyPow = float(account.regt_buying_power)
    print(f'Daytrading buying power: {buyPow}')
    print(f'Overnight buying power:  {regTBuyPow}')

    try: # get performance weights
        w = []
        for algo in allAlgos:
            try: # get performance metrics
                metrics = algo.get_metrics(allocMetricDays)

                try: # get long equity growth
                    w.append(metrics['mean']['long'])
                except:
                    w.append(0)
                    warn(f'{algo.name} missing long data')
                
                try: # get short equity growth
                    w.append(metrics['mean']['short'])
                except:
                    w.append(0)
                    warn(f'{algo.name} missing short data')
            except:
                warn(f'{algo.name} missing performance data')

            try:
                if verbose:
                    print(f'{algo.name}')
                    print(f"\tlong growth:  {metrics['mean']['long']}\t+/- {metrics['stdev']['long']}")
                    print(f"\tshort growth: {metrics['mean']['short']}\t+/- {metrics['stdev']['short']}")
            except:
                warn(f'{algo.name} missing risk data')
        w = np.array(w)
    except Exception as e: warn(e)

    try: # get weight region lengths
        n_all = len(allAlgos) * 2
        n_intraday = len(intradayAlgos) * 2
        n_overnight = len(overnightAlgos) * 2
        n_multiday = len(multidayAlgos) * 2
    except Exception as e: warn(e)

    try: # set objective function and initial guess
        func = lambda x: - np.dot(x, w)
        x0 = [0] * n_all
    except Exception as e: warn(e)

    try: # set allcoation bounds
        bounds = opt.Bounds(
            lb = [0] * n_all,
            ub = [maxAllocFrac] * n_all
        )
    except Exception as e: warn(e)
    
    try: # set allocation constraints
        constraints = opt.LinearConstraint(
            A = [
                [1, -1] * int(n_all / 2), # longShortFrac bounds

                # overnight + multiday <= regT
                [0] * n_intraday + [1] * (n_overnight + n_multiday),

                # intraday + multiday <= daytrading
                [1] * n_intraday + [0] * n_overnight + [1] * n_multiday
            ],
            lb = [
                minLongShortFrac * 2 - 1, # longShortFrac bounds
                0, # overnight + multiday <= regT
                0 # intraday + multiday <= daytrading
            ],
            ub = [
                maxLongShortFrac * 2 - 1, # longShortFrac bounds
                regTBuyPow / buyPow, # overnight + multiday <= regT
                1 # intraday + multiday <= daytrading
            ]
        )
    except Exception as e: warn(e)

    try: # calculate allocation
        results = opt.minimize(func, x0,
            bounds = bounds,
            constraints = constraints)
        allocFrac = results.x
    except Exception as e: warn(e)

    # distribute buying power
    # NOTE: allowing this to crash if broken
    for ii, algo in enumerate(allAlgos):
        algo.buyPow['long'] = int(allocFrac[ii*2] * buyPow)
        algo.buyPow['short'] = int(allocFrac[ii*2+1] * buyPow)
        print(f'{algo.name}\n\t{algo.buyPow}')

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