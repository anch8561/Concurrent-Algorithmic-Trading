import config as c
import globalVariables as g

from logging import getLogger
import numpy as np
import scipy.optimize as opt

log = getLogger('main')

def allocate_buying_power(algos):
    # algos: dict of lists of algos; {intraday, overnight, multiday, all}

    log.warning('Allocating buying power')

    # get buying power
    account = g.alpaca.get_account()
    buyPow = float(account.daytrading_buying_power)
    regTBuyPow = float(account.regt_buying_power)
    log.warning(f'Daytrading buying power: {buyPow}')
    log.warning(f'Overnight buying power:  {regTBuyPow}')

    try: # get algo metrics
        weights = []
        longShortVec = []
        for algo in algos['all']:
            try: # get weight
                metrics = algo.get_metrics(c.allocMetricDays)
                if metrics['mean'] == None:
                    log.warning(f'No performance data for {algo.name}')
                    metrics['mean'] = -1 # assume worst
                weights.append(metrics['mean'])
            except Exception as e:
                log.exception(e)
                weights.append(0)

            try: # get longShort
                if algo.longShort == 'long': longShortVec.append(1)
                else: longShortVec.append(-1)
            except Exception as e:
                log.exception(e)
                longShortVec.append(0)

            try: algo.log.debug(f"\tgrowth: {metrics['mean']}\t+/- {metrics['stdev']}")
            except Exception as e: log.exception(e)
        weights = np.array(weights)
    except Exception as e: log.exception(e)

    try: # get weight region lengths
        n_all = len(algos['all'])
        n_intraday = len(algos['intraday'])
        n_overnight = len(algos['overnight'])
        n_multiday = len(algos['multiday'])
    except Exception as e: log.exception(e)

    try: # set objective function and initial guess
        func = lambda x: - np.dot(x, weights)
        x0 = [0] * n_all
    except Exception as e: log.exception(e)

    try: # set allocation bounds
        bounds = opt.Bounds(
            lb = [0] * n_all,
            ub = [c.maxAllocFrac] * n_all
        )
    except Exception as e: log.exception(e)
    
    try: # set allocation constraints
        constraints = opt.LinearConstraint(
            A = [
                # day longShortFrac bounds
                longShortVec[:n_intraday] + [0] * n_overnight + longShortVec[-n_multiday:],
                
                # night longShortFrac bounds
                [0] * n_intraday + longShortVec[-(n_overnight + n_multiday):],

                # intraday + multiday <= daytrading
                [1] * n_intraday + [0] * n_overnight + [1] * n_multiday,

                # overnight + multiday <= regT
                [0] * n_intraday + [1] * (n_overnight + n_multiday)
            ],
            lb = [
                c.minLongShortFrac * 2 - 1, # day longShortFrac bounds (scale 0<->1 to -1<->1)
                c.minLongShortFrac - 0.5, # night longShortFrac bounds (scale 0<->1 to -1<->1)
                0, # intraday + multiday <= daytrading
                0 # overnight + multiday <= regT
            ],
            ub = [
                c.maxLongShortFrac * 2 - 1, # day longShortFrac bounds (scale 0<->1 to -1<->1)
                c.maxLongShortFrac - 0.5, # night longShortFrac bounds (scale 0<->1 to -1<->1)
                1, # intraday + multiday <= daytrading
                regTBuyPow / buyPow # overnight + multiday <= regT
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
            algo.buyPow = int(allocFrac[ii] * buyPow)
            algo.log.info(f'Buying power: {algo.buyPow}')
    except Exception as e: log.exception(e)

    # TODO: add c.minAllocBuyPow threshold
