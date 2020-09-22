import config as c
import globalVariables as g

from logging import getLogger
import numpy as np
import scipy.optimize as opt

log = getLogger()

def allocate_buying_power(algos):
    # algos: dict of lists of algos (keys: 'intraday', 'overnight', 'multiday', 'all')

    log.warning('Allocating buying power')

    # get buying power
    account = g.alpacaPaper.get_account() # FIX: paper
    buyPow = float(account.daytrading_buying_power)
    regTBuyPow = float(account.regt_buying_power)
    log.warning(f'Daytrading buying power: {buyPow}')
    log.warning(f'Overnight buying power:  {regTBuyPow}')

    try: # get performance weights
        w = []
        for algo in algos['all']:
            metrics = algo.get_metrics(c.allocMetricDays)
            w.append(metrics['mean']['long'])
            w.append(metrics['mean']['short'])
            algo.log.debug(
                f"\tlong growth:  {metrics['mean']['long']}\t+/- {metrics['stdev']['long']}\n" +
                f"\tshort growth: {metrics['mean']['short']}\t+/- {metrics['stdev']['short']}")
        w = np.array(w)
    except Exception as e: log.exception(e)

    try: # get weight region lengths
        n_all = len(algos['all']) * 2
        n_intraday = len(algos['intraday']) * 2
        n_overnight = len(algos['overnight']) * 2
        n_multiday = len(algos['multiday']) * 2
    except Exception as e: log.exception(e)

    try: # set objective function and initial guess
        func = lambda x: - np.dot(x, w)
        x0 = [0] * n_all
    except Exception as e: log.exception(e)

    try: # set allcoation bounds
        bounds = opt.Bounds(
            lb = [0] * n_all,
            ub = [c.maxAllocFrac] * n_all
        )
    except Exception as e: log.exception(e)
    
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
                c.minLongShortFrac * 2 - 1, # longShortFrac bounds
                0, # overnight + multiday <= regT
                0 # intraday + multiday <= daytrading
            ],
            ub = [
                c.maxLongShortFrac * 2 - 1, # longShortFrac bounds
                regTBuyPow / buyPow, # overnight + multiday <= regT
                1 # intraday + multiday <= daytrading
            ]
        )
    except Exception as e: log.exception(e)

    try: # calculate allocation
        results = opt.minimize(func, x0,
            bounds = bounds,
            constraints = constraints)
        allocFrac = results.x
    except Exception as e: log.exception(e)

    try: # distribute buying power
        for ii, algo in enumerate(algos['all']):
            algo.buyPow['long'] = int(allocFrac[ii*2] * buyPow)
            algo.buyPow['short'] = int(allocFrac[ii*2+1] * buyPow)
            algo.log.info(f'Buying power: {algo.buyPow}')
    except Exception as e: log.exception(e)
