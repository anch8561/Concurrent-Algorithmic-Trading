import algoClasses
import config as c
import globalVariables as g
import tick_algos

from datetime import timedelta
from unittest.mock import Mock, patch

def test_tick_algos_NIGHT(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod + timedelta(seconds=1)
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs:
        ## DEATIVATION ATTEMPT

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
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs:
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
    
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs:
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
    
    with patch('tick_algos.streaming.process_backlogs') as process_backlogs:
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
