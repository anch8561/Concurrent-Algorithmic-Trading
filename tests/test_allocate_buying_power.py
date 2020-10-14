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
            daytrading_buying_power = '10000'
            regt_buying_power = '6000'
        def get_account(): # pylint: disable=no-method-argument
            return alpaca.account
    g.alpaca = alpaca

    # setup algo.get_metrics
    means = [None, 0.3, 0.1, 0.2, 0.3, 0.1, 0.2]
    for ii, algo in enumerate(algos['all']):
        algo.get_metrics = Mock(return_value={'mean': means[ii], 'stdev': None})

    # test
    with patch('allocate_buying_power.c.allocMetricDays', 3), \
        patch('allocate_buying_power.c.maxAllocFrac', 0.5), \
        patch('allocate_buying_power.c.minLongShortFrac', 0.4), \
        patch('allocate_buying_power.c.maxLongShortFrac', 0.7):
        allocate_buying_power(algos)
    testBPs = []
    for algo in algos['all']:
        testBPs.append(algo.buyPow)
        algo.get_metrics.assert_called_once_with(3)
    testBPs = array(testBPs)
    realBPs = array([
        0,      # day   long  -1  (no performance data)
        5000,   # day   short 0.3 (maxAllocFrac)
        4000,   # day   long  0.1 (buyPow)
        1000,   # day   short 0.2 (minLongShortFrac)
        3000,   # night long  0.3 (maxAllocFrac)
        1800,   # night short 0.1 (regTBuyPow)
        1200])  # night long  0.2 (maxLongShortFrac)
    assert all(testBPs - realBPs < 5)
