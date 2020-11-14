import globalVariables as g
import indicators
Indicator = indicators.Indicator

import statistics as stats
import ta
from unittest.mock import Mock, call

def test_Indicator():
    testInd = Indicator(3, 'min', print)
    # NOTE: skipping unused kwargs
    assert testInd.name == '3_min_print'
    assert testInd.func == print

def test_Indicator_get():
    # setup
    testInd = Indicator(3, 'min', print)
    testInd.func = Mock(return_value=123)

    # test
    val = testInd.get(None)
    testInd.func.assert_called_once_with(testInd, None)
    assert val == 123

def test_momentum(bars):
    testInd = Indicator(3, 'min', indicators.momentum)
    val = testInd.get(bars)
    assert val == 567.56 / 234.23 - 1

def test_volume_stdevs(bars):
    testInd = Indicator(3, 'min', indicators.volume_stdevs)
    val = testInd.get(bars)
    expected = -1.091089451179962
    assert val - expected < 1e-6

def test_SMA(bars):
    testInd = Indicator(3, 'min', indicators.SMA)
    testVal = testInd.get(bars)
    realVal = ta.trend.sma_indicator(bars.vwap, 3)[-1]
    assert testVal == realVal

def test_EMA(bars):
    testInd = Indicator(3, 'min', indicators.EMA)
    testVal = testInd.get(bars)
    realVal = ta.trend.ema_indicator(bars.vwap, 3)[-1]
    assert testVal == realVal

def test_KAMA(bars):
    testInd = Indicator(3, 'min', indicators.KAMA)
    testVal = testInd.get(bars)
    realVal = ta.momentum.kama(bars.vwap, 3)[-1]
    assert testVal == realVal
