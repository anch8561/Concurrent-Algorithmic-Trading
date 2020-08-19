import config as c
import globalVariables as g
from algoClasses import DayAlgo, NightAlgo
from algos import momentum, momentum_volume, crossover

from pandas import DataFrame
from unittest.mock import Mock

def test_momentum():
    # setup
    testAlgo = DayAlgo(momentum,
        enterNumBars = 3,
        exitNumBars = 2,
        barFreq = 'min')
    testAlgo.enter_position = Mock()
    testAlgo.exit_position = Mock()

    # already ticked
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False, False, True], '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # already entered
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # no enter condition
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.enter_position.assert_not_called()

    # enter long
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.enter_position.assert_called_once_with('AAPL', 'buy')

    # enter short
    testAlgo.enter_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 0}
    bars = {'ticked': [False]*3, '1_min_momentum': [-0.1, -0.2, -0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.enter_position.assert_called_once_with('AAPL', 'sell')

    # no exit condition (long)
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.exit_position.assert_not_called()

    # no exit condition (short)
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': -10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.exit_position.assert_not_called()

    # exit long
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': 10}
    bars = {'ticked': [False]*3, '1_min_momentum': [0.1, -0.2, -0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.exit_position.assert_called_once_with('AAPL')

    # exit short
    testAlgo.exit_position.reset_mock()
    testAlgo.positions['AAPL'] = {'qty': -10}
    bars = {'ticked': [False]*3, '1_min_momentum': [-0.1, 0.2, 0.3]}
    g.assets['min']['AAPL'] = DataFrame(bars)
    testAlgo.tick()
    testAlgo.exit_position.assert_called_once_with('AAPL')

def test_momentum_volume():
    pass

def test_crossover():
    pass
