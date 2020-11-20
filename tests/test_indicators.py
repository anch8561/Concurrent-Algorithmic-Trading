import globalVariables as g
import indicators
Indicator = indicators.Indicator

import statistics as stats
from unittest.mock import Mock, call

def test_Indicator():
    testInd = Indicator('min', print, numBars=3)
    # NOTE: skipping unused kwargs
    assert testInd.name == '3_min_print'
    assert testInd.func == print

def test_Indicator_get():
    # setup
    testInd = Indicator('min', print, numBars=3)
    testInd.func = Mock(return_value=123)

    # test
    val = testInd.get(None)
    testInd.func.assert_called_once_with(testInd, None)
    assert val == 123

def test_mom(bars):
    testInd = Indicator('min', indicators.mom, numBars=3)
    val = testInd.get(bars)
    assert val == 567.56 / 456.45 - 1

def test_vol_stdevs(bars):
    testInd = Indicator('min', indicators.vol_stdevs, numBars=3)
    val = testInd.get(bars)
    expected = -1.091089451179962
    assert val - expected < 1e-6

def test_EMA(bars):
    # 1st bar
    testInd = Indicator('min', indicators.EMA, numBars=3)
    bars[testInd.name] = None
    val = testInd.get(bars)
    assert val == 567.56

    # typical
    bars[testInd.name] = 444.33
    val = testInd.get(bars)
    assert val == 444.33 + (567.56 - 444.33) / 2


def test_KAMA(bars):
    # 1st bar
    testInd = Indicator('min', indicators.KAMA, effNumBars=3, fastNumBars=4, slowNumBars=5)
    bars[testInd.name] = None
    val = testInd.get(bars)
    assert val == 567.56

    # typical
    bars[testInd.name] = 444.33
    fastSC = 2/5
    slowSC = 2/6
    ER = 1/3
    SC = (ER * (fastSC - slowSC) + slowSC)**2
    val = testInd.get(bars)
    assert val == 444.33 + SC * (567.56 - 444.33)
