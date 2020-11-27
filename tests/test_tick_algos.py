import config as c
import globalVariables as g
import tick_algos
from algoClass import Algo

from datetime import timedelta
from pandas import DataFrame
from pytest import fixture
from unittest.mock import call, Mock, patch

@fixture
def combinedOrder():
    algo1 = Algo('min', print, [], 'short', False) # enter
    algo1.positions['AAPL'] = {'qty': -5, 'basis': 9.00}
    algo1.queuedOrders['AAPL'] = {'qty': -1, 'price': 11.00}

    algo2 = Algo('min', print, [], 'long', False) # opposing enter
    algo2.positions['AAPL'] = {'qty': 4, 'basis': 9.00}
    algo2.queuedOrders['AAPL'] = {'qty':  2, 'price': 11.00}

    algo3 = Algo('min', print, [], 'long', False) # exit
    algo3.positions['AAPL'] = {'qty': 3, 'basis': 9.00}
    algo3.queuedOrders['AAPL'] = {'qty': -3, 'price': 11.00}

    algo4 = Algo('min', print, [], 'short', False) # enter
    algo4.positions['AAPL'] = {'qty': -2, 'basis': 9.00}
    algo4.queuedOrders['AAPL'] = {'qty': -4, 'price': 11.00}

    algo5 = Algo('min', print, [], 'short', False) # enter
    algo5.positions['AAPL'] = {'qty': -1, 'basis': 9.00}
    algo5.queuedOrders['AAPL'] = {'qty': -5, 'price': 11.00}

    return {
        'symbol': 'AAPL',
        'qty': -11,
        'price': 20.00,
        'algos': [algo1, algo2, algo3, algo4, algo5]}

def test_update_algo_orders(combinedOrder):
    # setup
    combinedOrder['qty'] = -5
    algos = combinedOrder['algos']
    algosCopy = algos.copy()

    # test
    tick_algos.update_algo_orders(combinedOrder)
    orders = [algo.queuedOrders['AAPL']['qty'] for algo in algos]
    assert orders == [2, -2, -5]
    buyPows = [algo.buyPow for algo in algosCopy]
    assert buyPows == [11, 0, 0, 22, 0]

def test_get_price():
    g.assets['min']['AAPL'] = DataFrame({'close': 111.11}, ['a'])
    assert tick_algos.get_price('AAPL') == 111.11

def test_get_limit_price():
    with patch('tick_algos.get_price', return_value=111.11), \
        patch('tick_algos.c.limitPriceFrac', 0.1):

        # buy
        price = tick_algos.get_limit_price('AAPL', 'buy')
        assert price == 122.22 # 122.221

        # sell
        price = tick_algos.get_limit_price('AAPL', 'sell')
        assert price == 100 # 99.999

@fixture
def alpaca():
    class alpaca:
        class order:
            id = 54321
        submit_order = Mock(return_value=order)
        class lastTrade:
            price = 123.45
        get_last_trade = Mock(return_value=lastTrade)
    return alpaca

def test_submit_order_LIMIT(alpaca, combinedOrder):
    with patch('tick_algos.g.alpaca', alpaca):
        tick_algos.submit_order(combinedOrder)
        alpaca.submit_order.assert_called_once_with(
            symbol = 'AAPL',
            qty = 11,
            side = 'sell',
            type = 'limit',
            time_in_force = 'day',
            limit_price = 20.00)
        assert g.orders[54321] == {
            'symbol': 'AAPL',
            'qty': -11,
            'price': 20.00,
            'algos': combinedOrder['algos']}

def test_submit_order_MARKET(alpaca, combinedOrder):
    combinedOrder['price'] = None
    with patch('tick_algos.g.alpaca', alpaca):
        tick_algos.submit_order(combinedOrder)
        alpaca.submit_order.assert_called_once_with(
            symbol = 'AAPL',
            qty = 11,
            side = 'sell',
            type = 'market',
            time_in_force = 'day')
        assert g.orders[54321] == {
            'symbol': 'AAPL',
            'qty': -11,
            'price': None,
            'algos': combinedOrder['algos']}

def test_process_queued_orders(alpaca, allAlgos):
    # setup
    allAlgos[0].queuedOrders['AAPL'] = {'qty':  1, 'price': 9.00}
    allAlgos[0].queuedOrders['MSFT'] = {'qty': -2, 'price': 8.00}
    allAlgos[0].queuedOrders['TSLA'] = {'qty':  3, 'price': 10.00}
    allAlgos[1].queuedOrders['MSFT'] = {'qty': -4, 'price': 11.00}
    allAlgos[1].queuedOrders['TSLA'] = {'qty':  5, 'price': 7.00}
    allAlgos[2].queuedOrders['AAPL'] = {'qty': -6, 'price': 13.00}
    allAlgos[2].queuedOrders['MSFT'] = {'qty':  7, 'price': 10.00}
    allAlgos[2].queuedOrders['TSLA'] = {'qty': -8, 'price': 9.00}
    allAlgos[3].queuedOrders['MSFT'] = {'qty':  9, 'price': 11.00}
    # -5 AAPL, 10 MSFT, 0 TSLA
    g.positions = {'AAPL': 3, 'MSFT': 5, 'TSLA': 7}
    expectedPendingOrders = [algo.queuedOrders.copy() for algo in allAlgos]
    expectedPendingOrders[2]['AAPL']['qty'] = -4

    # test
    with patch('tick_algos.random.shuffle') as shuffle, \
        patch('tick_algos.update_algo_orders') as update_algo_orders, \
        patch('tick_algos.get_limit_price', return_value=None) as get_limit_price, \
        patch('tick_algos.get_price', return_value=None) as get_price, \
        patch('tick_algos.submit_order') as submit_order, \
        patch('tick_algos.g.alpaca', alpaca), \
        patch('tick_algos.streaming.process_trade') as process_trade:

        tick_algos.process_queued_orders(allAlgos)
        
        assert shuffle.call_count == 3
        assert update_algo_orders.call_count == 3
        calls = [
            call('AAPL', 'sell'),
            call('MSFT', 'buy')]
        get_limit_price.assert_has_calls(calls)
        get_price.assert_called_once_with('TSLA')
        calls = [
            call({
                'symbol': 'AAPL',
                'qty': -3,
                'price': None,
                'algos': [
                    allAlgos[0],
                    allAlgos[2]]}),
            call({
                'symbol': 'MSFT',
                'qty': 10,
                'price': None,
                'algos': [
                    allAlgos[0],
                    allAlgos[1],
                    allAlgos[2],
                    allAlgos[3]]})]
        submit_order.assert_has_calls(calls, True)
        alpaca.get_last_trade.assert_called_once_with('TSLA')
        process_trade.assert_called_once()
        for algo in allAlgos:
            assert algo.queuedOrders == {}
        testPendingOrders = [algo.pendingOrders for algo in allAlgos]
        assert testPendingOrders == expectedPendingOrders

def test_tick_algos_NIGHT(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod + timedelta(seconds=1)
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    with patch('tick_algos.g.alpaca'), \
        patch('tick_algos.process_queued_orders') as process_queued_orders, \
        patch('tick_algos.streaming.process_backlogs') as process_backlogs:
        ## DEACTIVATION ATTEMPT

        # setup
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['overnight']: algo.active = False
        algos['overnight'][1].active = True

        # test
        state = tick_algos.tick_algos(algos, indicators, 'overnight')
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            if algo is algos['overnight'][1]:
                algo.deactivate.assert_called_once()
            else:
                algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()

        process_queued_orders.assert_called_once_with(algos['all'])
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once_with(indicators)
        assert state == 'overnight'
        

        ## SUCCESSFUL DEACTIVATION

        # setup
        def set_active(): algos['overnight'][1].active = False
        for algo in algos['all']:
            algo.activate.reset_mock()
            algo.deactivate = Mock(side_effect=set_active)
            algo.tick.reset_mock()
        process_queued_orders.reset_mock()
        g.assets['min'] = {'AAPL': bars.copy()}
        process_backlogs.reset_mock()
        for algo in algos['overnight']: algo.active = False
        algos['overnight'][1].active = True

        # test
        state = tick_algos.tick_algos(algos, indicators, 'overnight')
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            if algo is algos['overnight'][1]:
                algo.deactivate.assert_called_once()
            else:
                algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['intraday']:
            algo.activate.called_once()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()

        process_queued_orders.assert_called_once_with(algos['all'])
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once_with(indicators)
        assert state == 'intraday'

def test_tick_algos_DAY(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod + timedelta(seconds=1)
    g.assets['min'] = {'AAPL': bars}
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    # test
    with patch('tick_algos.g.alpaca'), \
        patch('tick_algos.process_queued_orders') as process_queued_orders, \
        patch('tick_algos.streaming.process_backlogs') as process_backlogs:

        state = tick_algos.tick_algos(algos, indicators, 'intraday')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_called_once()
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        
        process_queued_orders.assert_called_once_with(algos['all'])
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once_with(indicators)
        assert state == 'intraday'

def test_tick_algos_NIGHT_CLOSING_SOON(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod - timedelta(seconds=1)
    g.assets['min'] = {'AAPL': bars}
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    # test
    with patch('tick_algos.g.alpaca'), \
        patch('tick_algos.process_queued_orders') as process_queued_orders, \
        patch('tick_algos.streaming.process_backlogs') as process_backlogs:

        state = tick_algos.tick_algos(algos, indicators, 'overnight')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_called_once()
        
        process_queued_orders.assert_called_once_with(algos['all'])
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once_with(indicators)
        assert state == 'overnight'

def test_tick_algos_DAY_CLOSING_SOON(algos, bars, indicators):
    # setup
    g.TTClose = c.marketCloseTransitionPeriod - timedelta(seconds=1)
    for algo in algos['all']:
        algo.activate = Mock()
        algo.deactivate = Mock()
        algo.tick = Mock()
    
    with patch('tick_algos.g.alpaca'), \
        patch('tick_algos.streaming.compile_day_bars') as compile_day_bars, \
        patch('tick_algos.process_queued_orders') as process_queued_orders, \
        patch('tick_algos.streaming.process_backlogs') as process_backlogs:
        ## DEATIVATION ATTEMPT

        # setup
        g.assets['min'] = {'AAPL': bars.copy()}
        for algo in algos['intraday']: algo.active = True

        # test
        state = tick_algos.tick_algos(algos, indicators, 'intraday')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_called_once()
            algo.tick.assert_not_called()
        for algo in algos['overnight']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()

        compile_day_bars.assert_not_called()
        process_queued_orders.assert_called_once_with(algos['all'])
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once_with(indicators)
        assert state == 'intraday'
        

        ## SUCCESSFUL DEACTIVATION

        # setup
        for algo in algos['all']:
            algo.activate.reset_mock()
            algo.deactivate.reset_mock()
            algo.tick.reset_mock()
        compile_day_bars.reset_mock()
        process_queued_orders.reset_mock()
        g.assets['min'] = {'AAPL': bars.copy()}
        process_backlogs.reset_mock()
        for algo in algos['intraday']: algo.active = False

        # test
        state = tick_algos.tick_algos(algos, indicators, 'intraday')
        for algo in algos['intraday']:
            algo.activate.assert_not_called()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()
        for algo in algos['overnight']:
            algo.activate.assert_called_once()
            algo.deactivate.assert_not_called()
            algo.tick.assert_not_called()

        compile_day_bars.assert_called_once_with(indicators)
        process_queued_orders.assert_called_once_with(algos['all'])
        assert g.assets['min']['AAPL'].ticked[-1]
        process_backlogs.assert_called_once_with(indicators)
        assert state == 'overnight'
