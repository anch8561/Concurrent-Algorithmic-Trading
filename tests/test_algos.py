import algos
import config as c
import globalVariables as g
from Algo import Algo, Algo

from pandas import DataFrame
from unittest.mock import Mock, call

def test_momentum():
    # setup
    testAlgo = Algo(algos.momentum, False,
        numUpBars = 3,
        numDownBars = 2,
        barFreq = 'min')
    testAlgo.queue_order = Mock()

    # already ticked
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False, False, True], '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.queue_order.assert_not_called()

    # no condition
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.queue_order.assert_not_called()

    # long
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.queue_order.assert_called_once_with('AAPL', 'long')

    # short
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, -0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.queue_order.assert_called_once_with('AAPL', 'short')

def test_momentum_volume():
    # setup
    testAlgo = Algo(algos.momentum_volume, False,
        numBars = 2,
        barFreq = 'day')
    def queue_order(symbol, longShort):
        testAlgo.buyPow[longShort] -= c.minTradeBuyPow
    testAlgo.queue_order = Mock(side_effect=queue_order)
    bars = {'2_day_volume_stdevs': [0.1, 2.2], '2_day_momentum': [-0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b']) # 0.88
    bars = {'2_day_volume_stdevs': [0.4, 3.1], '2_day_momentum': [0.1, -0.2]}
    g.assets['day']['GOOG'] = DataFrame(bars, ['a', 'b']) # -0.62
    bars = {'2_day_volume_stdevs': [2.3, 1.3], '2_day_momentum': [0.5, 0.3]}
    g.assets['day']['MSFT'] = DataFrame(bars, ['a', 'b']) # 0.39
    bars = {'2_day_volume_stdevs': [1.2, 2.1], '2_day_momentum': [-0.7, -0.4]}
    g.assets['day']['TSLA'] = DataFrame(bars, ['a', 'b']) # -0.84

    # metric < 0
    testAlgo.queue_order.reset_mock()
    cash = c.minTradeBuyPow * 3
    testAlgo.buyPow = {'long': cash, 'short': cash}
    testAlgo.tick()
    calls = [
        call('AAPL', 'long'),
        call('MSFT', 'long'),
        call('TSLA', 'short'),
        call('GOOG', 'short')]
    testAlgo.queue_order.assert_has_calls(calls)
    assert testAlgo.queue_order.call_count == 4

    # buying power
    testAlgo.queue_order.reset_mock()
    cash = c.minTradeBuyPow * 1.5
    testAlgo.buyPow = {'long': cash, 'short': cash}
    testAlgo.tick()
    calls = [
        call('AAPL', 'long'),
        call('TSLA', 'short')]
    testAlgo.queue_order.assert_has_calls(calls)
    assert testAlgo.queue_order.call_count == 2

def test_crossover():
    # setup
    testAlgo = Algo(algos.crossover, False,
        barFreq = 'day',
        fastNumBars = 3,
        fastMovAvg = 'SMA',
        slowNumBars = 5,
        slowMovAvg = 'EMA')
    testAlgo.queue_order = Mock()

    # already ticked
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False, True], '3_day_SMA': [0.1, 1.2], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.queue_order.assert_not_called()

    # no condition
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 0.4], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.queue_order.assert_not_called()

    # long
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False]*2, '3_day_SMA': [1.2, 0.1], '5_day_EMA': [0.4, 0.3]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.queue_order.assert_called_once_with('AAPL', 'long')

    # short
    testAlgo.queue_order.reset_mock()
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 1.2], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.queue_order.assert_called_once_with('AAPL', 'short')
