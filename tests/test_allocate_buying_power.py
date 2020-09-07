import config as c
import globalVariables as g
from algoClasses import Algo
from allocate_buying_power import allocate_buying_power

import numpy as np
import scipy.optimize as opt

def test_allocate_buying_power(algos):
    # setup alpaca.get_account
    class alpacaPaper:
        class account:
            daytrading_buying_power = '123456.78'
            regt_buying_power = '45678.90'
        def get_account(): # pylint: disable=no-method-argument
            return alpacaPaper.account
    g.alpacaPaper = alpacaPaper

    # setup algo.get_metrics
    def metric(reset=False):
        ii = 0
        while True:
            yield dict(mean=dict(long=ii-5, short=5-ii))
            ii += 1
            if reset: ii = 0
    def get_metrics(days=0, reset=False):
        return next(metric(reset))
    Algo.get_metrics = get_metrics

    # test
    allocate_buying_power(algos)
    testBPs = []
    for algo in algos['all']:
        testBPs.append(algo.buyPow)
    
    ## REAL

    # get buying power
    buyPow = float(alpacaPaper.account.daytrading_buying_power)
    regTBuyPow = float(alpacaPaper.account.regt_buying_power)

    # get performance weights
    get_metrics(reset=True)
    w = []
    for algo in algos['all']:
        metrics = algo.get_metrics(c.allocMetricDays)
        w.append(metrics['mean']['long'])
        w.append(metrics['mean']['short'])
    w = np.array(w)

    # get weight region lengths
    n_all = 18
    n_intraday = 4
    n_overnight = 6
    n_multiday = 8

    # set objective function and initial guess
    func = lambda x: - np.dot(x, w)
    x0 = [0] * n_all

    # set allcoation bounds
    bounds = opt.Bounds(
        lb = [0] * n_all,
        ub = [c.maxAllocFrac] * n_all
    )

    # set allocation constraints
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

    # calculate allocation
    results = opt.minimize(func, x0,
        bounds = bounds,
        constraints = constraints)
    allocFrac = results.x

    # distribute buying power
    for ii, algo in enumerate(algos['all']):
        algo.buyPow['long'] = int(allocFrac[ii*2] * buyPow)
        algo.buyPow['short'] = int(allocFrac[ii*2+1] * buyPow)
    
    # test
    realBPs = []
    for algo in algos['all']:
        realBPs.append(algo.buyPow)
    assert testBPs == realBPs
