import algoClass
import config as c
import globalVariables as g
from allocate_buying_power import allocate_buying_power

from numpy import array
from unittest.mock import Mock, patch

def test_allocate_buying_power(algos):
    # setup alpaca.get_account
    class alpaca:
        class account:
            daytrading_buying_power = '20000'
            regt_buying_power = '10000'
        def get_account(): # pylint: disable=no-method-argument
            return alpaca.account
    g.alpaca = alpaca

    # setup algo.get_metrics
    means = [0.4, 0.4, None, 0.4, 0.1, 0.1, 0.2, 0.2, 0.3]
    for ii, algo in enumerate(algos['all']):
        algo.get_metrics = Mock(return_value={'mean': means[ii], 'stdev': None})

    # test
    with patch('allocate_buying_power.c.allocMetricDays', 3), \
        patch('allocate_buying_power.c.maxAllocFrac', 0.25), \
        patch('allocate_buying_power.c.minLongShortFrac', 0.4), \
        patch('allocate_buying_power.c.maxLongShortFrac', 0.6):
        allocate_buying_power(algos)
    testBPs = []
    for algo in algos['all']:
        testBPs.append(algo.buyPow)
        algo.get_metrics.assert_called_once_with(3)
    testBPs = array(testBPs)
    realBPs = array([
        5000, # day   long  0.4 (maxAllocFrac)
        5000, # day   short 0.4 (maxAllocFrac)
        0,    # day   long  -1  (no performance data)
        5000, # day   short 0.4 (maxAllocFrac)
        0,    # night long  0.1 (regTBuyPow)
        2000, # night short 0.1 (regTBuyPow)
        3000, # night long  0.2 (maxLongShortFrac)
        3000, # multi long  0.2 (buyPow)
        2000])# multi short 0.3 (minLongShortFrac)
    assert all(testBPs - realBPs < 5)
