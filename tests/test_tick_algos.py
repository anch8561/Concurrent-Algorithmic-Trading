import config as c
import globalVariables as g
import tick_algos

from datetime import timedelta
from pandas import DataFrame
from unittest.mock import Mock, patch

def set_order_qty(): assert 0

def test_get_price():
    g.assets['min']['AAPL'] = DataFrame({'close': 111.11}, ['a'])
    assert tick_algos.get_price('AAPL') == 111.11

def test_get_limit_price():
    with patch('tick_algos.get_price', return_value=111.11), \
        patch('tick_algos.c.limitPriceFrac', 0.1):

        # buy
        price = tick_algos.get_limit_price('AAPL', 'buy')
        assert price == 122.221

        # sell
        price = tick_algos.get_limit_price('AAPL', 'sell')
        assert price == 99.999

def test_submit_order(): assert 0

def test_process_queued_orders(): assert 0

def test_tick_algos_NIGHT(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod + timedelta(seconds=1)
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs, \
        patch('tick_algos.g.alpaca'):
        ## DEACTIVATION ATTEMPT

        # setup
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['overnight']: algo.active = True

        # test
        state = tick_algos.tick_algos(algos, indicators, 'night')
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_called_once()
            algo.tick.assert_not_called()
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['multiday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.called_once()
        assert state == 'night'
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once()
        

        ## SUCCESSFUL DEACTIVATION

        # setup
        for algo in algos['all']:
            algo.activate.reset_mock()
            algo.deactivate.reset_mock()
            algo.tick.reset_mock()
        process_backlogs.reset_mock()
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['overnight']: algo.active = False

        # test
        state = tick_algos.tick_algos(algos, indicators, 'night')
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_called_once()
            algo.tick.assert_not_called()
        for algo in algos['intraday']:
            algo.activate.called_once()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['multiday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.called_once()
        assert state == 'day'
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once()

def test_tick_algos_DAY(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod + timedelta(seconds=1)
    g.assets['min'] = {'AAPL': bars}
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    # test
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs, \
        patch('tick_algos.g.alpaca'):
        state = tick_algos.tick_algos(algos, indicators, 'day')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_called_once()
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['multiday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.called_once()
        assert state == 'day'
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once()

def test_tick_algos_NIGHT_CLOSING_SOON(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod - timedelta(seconds=1)
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs, \
        patch('tick_algos.g.alpaca'):
        ## DEATIVATION ATTEMPT

        # setup
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['intraday']: algo.active = True

        # test
        state = tick_algos.tick_algos(algos, indicators, 'night')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_called_once()
        for algo in algos['multiday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.called_once()
        assert state == 'night'
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once()

def test_tick_algos_DAY_CLOSING_SOON(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod - timedelta(seconds=1)
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs, \
        patch('tick_algos.g.alpaca'):
        ## DEATIVATION ATTEMPT

        # setup
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['intraday']: algo.active = True

        # test
        state = tick_algos.tick_algos(algos, indicators, 'day')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_called_once()
            algo.tick.assert_not_called()
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['multiday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.called_once()
        assert state == 'day'
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once()
        

        ## SUCCESSFUL DEACTIVATION

        # setup
        for algo in algos['all']:
            algo.activate.reset_mock()
            algo.deactivate.reset_mock()
            algo.tick.reset_mock()
        process_backlogs.reset_mock()
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['intraday']: algo.active = False

        # test
        state = tick_algos.tick_algos(algos, indicators, 'day')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_called_once()
            algo.tick.assert_not_called()
        for algo in algos['overnight']:
            algo.activate.assert_called_once()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['multiday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.called_once()
        assert state == 'night'
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once()
