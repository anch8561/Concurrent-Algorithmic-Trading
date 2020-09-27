import algos
import config as c
import globalVariables as g
from algoClasses import DayAlgo, NightAlgo

from pandas import DataFrame
from unittest.mock import Mock, call

def test_momentum():
    # setup
    testAlgo = DayAlgo(algos.momentum, False,
        enterNumBars = 3,
        exitNumBars = 2,
        barFreq = 'min')
    testAlgo.enter_position = Mock()
    testAlgo.exit_position = Mock()

    # already ticked
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False, False, True], '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # already entered
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # no enter condition
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # enter long
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.enter_position.assert_called_once_with('AAPL', 'buy')

    # enter short
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*3, '1_min_momentum': [-0.1, -0.2, -0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.enter_position.assert_called_once_with('AAPL', 'sell')

    # no exit condition (long)
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.exit_position.assert_not_called()

    # no exit condition (short)
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': -10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.exit_position.assert_not_called()

    # exit long
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, -0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.exit_position.assert_called_once_with('AAPL')

    # exit short
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': -10}
    bars = {'ticked': [False]*3, '1_min_momentum': [-0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars, ['a', 'b', 'c'])
    testAlgo.tick()
    testAlgo.exit_position.assert_called_once_with('AAPL')

def test_momentum_volume():
    # setup
    testAlgo = NightAlgo(algos.momentum_volume, False,
        numBars = 2,
        barFreq = 'day')
    def enter_position(symbol, side):
        longShort = 'long' if side == 'buy' else 'short'
        testAlgo.buyPow[longShort] -= c.minTradeBuyPow
    testAlgo.enter_position = Mock(side_effect=enter_position)
    bars = {'2_day_volume_stdevs': [0.1, 2.2], '2_day_momentum': [-0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b']) # 0.88
    bars = {'2_day_volume_stdevs': [0.4, 3.1], '2_day_momentum': [0.1, -0.2]}
    g.assets['day']['GOOG'] = DataFrame(bars, ['a', 'b']) # -0.62
    bars = {'2_day_volume_stdevs': [2.3, 1.3], '2_day_momentum': [0.5, 0.3]}
    g.assets['day']['MSFT'] = DataFrame(bars, ['a', 'b']) # 0.39
    bars = {'2_day_volume_stdevs': [1.2, 2.1], '2_day_momentum': [-0.7, -0.4]}
    g.assets['day']['TSLA'] = DataFrame(bars, ['a', 'b']) # -0.84

    # metric < 0
    testAlgo.enter_position.reset_mock()
    cash = c.minTradeBuyPow * 3
    testAlgo.buyPow = {'long': cash, 'short': cash}
    testAlgo.tick()
    calls = [
        call('AAPL', 'buy'),
        call('MSFT', 'buy'),
        call('TSLA', 'sell'),
        call('GOOG', 'sell')]
    testAlgo.enter_position.assert_has_calls(calls)
    assert testAlgo.enter_position.call_count == 4

    # buying power
    testAlgo.enter_position.reset_mock()
    cash = c.minTradeBuyPow * 1.5
    testAlgo.buyPow = {'long': cash, 'short': cash}
    testAlgo.tick()
    calls = [
        call('AAPL', 'buy'),
        call('TSLA', 'sell')]
    testAlgo.enter_position.assert_has_calls(calls)
    assert testAlgo.enter_position.call_count == 2

def test_crossover():
    # setup
    testAlgo = DayAlgo(algos.crossover, False,
        barFreq = 'day',
        fastNumBars = 3,
        fastMovAvg = 'SMA',
        slowNumBars = 5,
        slowMovAvg = 'EMA')
    testAlgo.enter_position = Mock()
    testAlgo.exit_position = Mock()

    # already ticked
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False, True], '3_day_SMA': [0.1, 1.2], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # already entered
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 1.2], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # no enter condition
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 0.4], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # enter long
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*2, '3_day_SMA': [1.2, 0.1], '5_day_EMA': [0.4, 0.3]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.enter_position.assert_called_once_with('AAPL', 'buy')

    # enter short
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 1.2], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.enter_position.assert_called_once_with('AAPL', 'sell')

    # no exit condition (long)
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 0.3], '5_day_EMA': [0.4, 0.3]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.exit_position.assert_not_called()

    # no exit condition (short)
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': -10}
    bars = {'ticked': [False]*2, '3_day_SMA': [1.2, 0.4], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.exit_position.assert_not_called()

    # exit long
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*2, '3_day_SMA': [0.1, 1.2], '5_day_EMA': [0.4, 0.3]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.exit_position.assert_called_once_with('AAPL')

    # exit short
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': -10}
    bars = {'ticked': [False]*2, '3_day_SMA': [1.2, 0.1], '5_day_EMA': [0.3, 0.4]}
    g.assets['day']['AAPL'] = DataFrame(bars, ['a', 'b'])
    testAlgo.tick()
    testAlgo.exit_position.assert_called_once_with('AAPL')
