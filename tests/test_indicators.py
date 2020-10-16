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
    assert val == (575.04 - 345.67) / 345.67

def test_volume(bars):
    testInd = Indicator(3, 'min', indicators.volume)
    val = testInd.get(bars)
    assert val == 8888 + 7777 + 5555

def test_volume_stdevs(bars):
    testInd = Indicator(3, 'min', indicators.volume_stdevs)
    val = testInd.get(bars)
    expected = -1.091089451179962
    assert val - expected < 1e-6

def test_typical_price(bars):
    testInd = Indicator(3, 'min', indicators.typical_price)
    val = testInd.get(bars)
    assert val == (600.02 + 111.11 + 575.04) / 3

def test_SMA(bars):
    testInd = Indicator(3, 'min', indicators.SMA)
    testVal = testInd.get(bars)
    realVal = ta.trend.sma_indicator(bars.close[-3:], 3)[-1]
    assert testVal == realVal

def test_EMA(bars):
    testInd = Indicator(3, 'min', indicators.EMA)
    testVal = testInd.get(bars)
    realVal = ta.trend.ema_indicator(bars.close[-3:], 3)[-1]
    assert testVal == realVal

def test_KAMA(bars):
    testInd = Indicator(3, 'min', indicators.KAMA)
    testVal = testInd.get(bars)
    realVal = ta.momentum.kama(bars.close, 3)[-1]
    assert testVal == realVal
