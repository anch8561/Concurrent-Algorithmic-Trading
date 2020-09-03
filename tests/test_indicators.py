import globalVariables as g
import indicators
from indicators import Indicator

import statistics as stats
import ta, time
from pandas import DataFrame
from pytest import fixture
from unittest.mock import Mock, call

@fixture
def bars():
    data = {'open': [232.32, 345.67, 222.22, 543.21],
        'high': [454.54, 456.78, 444.44, 543.21],
        'low': [121.21, 123.45, 111.11, 543.21],
        'close': [343.43, 234.56, 333.33, 543.21],
        'volume': [9999, 8888, 7777, 6666]}
    return DataFrame(data, ['a', 'b', 'c', 'd'])

def test_Indicator():
    testInd = Indicator(3, 'min', print)
    # NOTE: skipping unused kwargs
    assert testInd.name == '3_min_print'

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
    assert val == (543.21 - 345.67) / 345.67

def test_volume(bars):
    testInd = Indicator(3, 'min', indicators.volume)
    val = testInd.get(bars)
    assert val == 8888 + 7777 + 6666

def test_volume_stdevs(bars):
    testInd = Indicator(3, 'min', indicators.volume_stdevs)
    val = testInd.get(bars)
    assert val == -1

def test_typical_price(bars):
    testInd = Indicator(3, 'min', indicators.typical_price)
    val = testInd.get(bars)
    assert val == (543.21 + 111.11 + 543.21) / 3

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
    realVal = ta.momentum.kama(bars.close[-3:], 3)[-1]
    assert testVal == realVal
