
import algoClass
import config as c
import globalVariables as g

import json
from os import remove
from pandas import DataFrame
from unittest.mock import call, Mock, patch

def test_Algo():
    # pylint: disable=no-member
    testAlgo = algoClass.Algo('min', print, 'short', False, a=1, b=2)
    assert testAlgo.barFreq == 'min'
    assert testAlgo.func == print
    assert testAlgo.longShort == 'short'
    assert testAlgo.a == 1
    assert testAlgo.b == 2
    assert testAlgo.name == '1_2_min_print_short'

def test_activate(testAlgo):
    # setup
    testAlgo.active = False
    testAlgo.start = Mock()

    # test
    testAlgo.activate()
    assert testAlgo.active == True
    testAlgo.start.assert_called_once()

def test_deactivate(testAlgo):
    # setup
    testAlgo.active = True
    testAlgo.stop = Mock()

    # open position
    testAlgo.positions = {
        'AAPL': {'qty': 0},
        'MSFT': {'qty': -1},
        'TSLA': {'qty': 0}}
    testAlgo.deactivate()
    testAlgo.stop.assert_not_called()
    assert testAlgo.active == True

    # typical
    testAlgo.positions = {
        'AAPL': {'qty': 0},
        'MSFT': {'qty': 0},
        'TSLA': {'qty': 0}}
    testAlgo.deactivate()
    testAlgo.stop.assert_called_once()
    assert testAlgo.active == False

def test_start(testAlgo):
    # setup
    testAlgo.update_equity = Mock()
    testAlgo.update_history = Mock()
    testAlgo.save_data = Mock()

    # inactive
    testAlgo.active = False
    testAlgo.start()
    testAlgo.update_equity.assert_not_called()
    testAlgo.update_history.assert_not_called()
    testAlgo.save_data.assert_not_called()

    # active
    testAlgo.active = True
    testAlgo.start()
    testAlgo.update_equity.assert_called_once()
    testAlgo.update_history.assert_called_once_with('start')
    testAlgo.save_data.assert_called_once()

def test_stop(testAlgo):
    # setup
    testAlgo.update_equity = Mock()
    testAlgo.update_history = Mock()
    testAlgo.save_data = Mock()

    # inactive
    testAlgo.active = False
    testAlgo.stop()
    testAlgo.update_equity.assert_not_called()
    testAlgo.update_history.assert_not_called()
    testAlgo.save_data.assert_not_called()

    # active
    testAlgo.active = True
    testAlgo.stop()
    testAlgo.update_equity.assert_called_once()
    testAlgo.update_history.assert_called_once_with('stop')
    testAlgo.save_data.assert_called_once()

def test_save_data(testAlgo):
    fileName = c.algoPath + testAlgo.name + '.data'
    
    # no file
    try: remove(fileName)
    except: pass
    testAlgo.equity = {'long': 0, 'short': 1}
    testAlgo.save_data()
    with open(fileName, 'r') as f:
        data = json.load(f)
    assert data['equity'] == testAlgo.equity

    # overwrite
    data = {'equity': {'long': 0, 'short': 1}}
    with open(fileName, 'w') as f:
        json.dump(data, f)
    testAlgo.equity = {'long': 1, 'short': 0}
    testAlgo.save_data()
    with open(fileName, 'r') as f:
        data = json.load(f)
    assert data['equity'] == testAlgo.equity

def test_load_data(testAlgo):
    # setup
    testAlgo.equity = {'long': 1, 'short': 0}
    data = {'equity': {'long': 0, 'short': 1}}
    fileName = c.algoPath + testAlgo.name + '.data'
    with open(fileName, 'w') as f:
        json.dump(data, f)

    # test
    testAlgo.load_data()
    assert testAlgo.equity == data['equity']

def test_update_equity(testAlgo):
    # setup
    testAlgo.buyPow = 10
    testAlgo.positions = {'AAPL': {'qty': -1}}
    testAlgo.exit_position = Mock()

    # typical
    with patch('algoClass.get_price', return_value=111.11):
        testAlgo.update_equity()
    assert testAlgo.equity == 121.11
    testAlgo.exit_position.assert_not_called()

    # untracked position
    g.alpaca = Mock()
    last_trade = Mock()
    last_trade.price = 111.22
    g.alpaca.get_last_trade = Mock(return_value=last_trade)
    with patch('algoClass.get_price', return_value=None):
        testAlgo.update_equity()
    assert testAlgo.equity == 121.22
    testAlgo.exit_position.called_once_with('AAPL')

def test_update_history(testAlgo):
    testAlgo.history = {}
    with patch('algoClass.get_date', return_value='1996-02-13'), \
        patch('algoClass.get_time_str', side_effect=['a', 'b']):
        testAlgo.equity = 123
        testAlgo.update_history('start')
        assert testAlgo.history == {'1996-02-13': {
            'a': {'event': 'start', 'equity': 123}}}

        testAlgo.equity = 456
        testAlgo.update_history('stop')
        assert testAlgo.history == {'1996-02-13': {
            'a': {'event': 'start', 'equity': 123},
            'b': {'event': 'stop', 'equity': 456}}}

def test_get_metrics(testAlgo): pass # WIP

def test_get_trade_qty(testAlgo):
    with patch('algoClass.c.maxPositionFrac', 0.1):
        # max position
        testAlgo.equity = 10000
        testAlgo.buyPow = 15000
        testAlgo.positions = {'AAPL': {'qty': 0}}
        testQty = testAlgo.get_trade_qty('AAPL', 'sell', 20)
        assert testQty == -50

        # buying power
        testAlgo.equity = 10000
        testAlgo.buyPow = 500
        testAlgo.positions = {'AAPL': {'qty': 0}}
        testQty = testAlgo.get_trade_qty('AAPL', 'sell', 20)
        assert testQty == -25

        # smaller position
        testAlgo.equity = 10000
        testAlgo.buyPow = 5000
        testAlgo.positions = {'AAPL': {'qty': -6}}
        testQty = testAlgo.get_trade_qty('AAPL', 'sell', 20)
        assert testQty == -44

        # larger position
        testAlgo.equity = 10000
        testAlgo.buyPow = 5000
        testAlgo.positions = {'AAPL': {'qty': -53}}
        testQty = testAlgo.get_trade_qty('AAPL', 'sell', 20)
        assert testQty == 0

def test_queue_order(testAlgo):
    with patch('algoClass.c.minTradeBuyPow', 100), \
        patch('algoClass.get_price', return_value=20), \
        patch('algoClass.get_limit_price', return_value=10), \
        patch('algoClass.Algo.get_trade_qty', return_value=123):
        # no position (exit)
        testAlgo.longShort = 'long'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': 0}
        testAlgo.pendingOrders = {}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'sell')
        assert testAlgo.queuedOrders == {}

        # pending order (exit)
        testAlgo.longShort = 'long'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': 10}
        testAlgo.pendingOrders = {'AAPL': 'order'}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'sell')
        assert testAlgo.queuedOrders == {}

        # exit long
        testAlgo.longShort = 'long'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': 10}
        testAlgo.pendingOrders = {}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'sell')
        assert testAlgo.queuedOrders == {'AAPL': {'qty': -10, 'price': 10}}

        # exit short
        testAlgo.longShort = 'short'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': -10}
        testAlgo.pendingOrders = {}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'buy')
        assert testAlgo.queuedOrders == {'AAPL': {'qty': 10, 'price': 10}}

        # insufficient buying power (enter)
        testAlgo.longShort = 'long'
        testAlgo.buyPow = 10
        testAlgo.positions['AAPL'] = {'qty': 0}
        testAlgo.pendingOrders = {}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'buy')
        assert testAlgo.queuedOrders == {}

        # pending order (enter)
        testAlgo.longShort = 'long'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': 0}
        testAlgo.pendingOrders = {'AAPL': 'order'}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'buy')
        assert testAlgo.queuedOrders == {}

        # enter long
        testAlgo.longShort = 'long'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': 0}
        testAlgo.pendingOrders = {}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'buy')
        assert testAlgo.queuedOrders == {'AAPL': {'qty': 123, 'price': 10}}

        # enter short
        testAlgo.longShort = 'short'
        testAlgo.buyPow = 1000
        testAlgo.positions['AAPL'] = {'qty': 0}
        testAlgo.pendingOrders = {}
        testAlgo.queuedOrders = {}
        testAlgo.queue_order('AAPL', 'sell')
        assert testAlgo.queuedOrders == {'AAPL': {'qty': 123, 'price': 20.6}}

def test_exit_position(testAlgo):
    # long
    testAlgo.queue_order = Mock()
    testAlgo.longShort = 'long'
    testAlgo.exit_position('AAPL')
    testAlgo.queue_order.assert_called_once_with('AAPL', 'sell')

    # short
    testAlgo.queue_order = Mock()
    testAlgo.longShort = 'short'
    testAlgo.exit_position('AAPL')
    testAlgo.queue_order.assert_called_once_with('AAPL', 'buy')

def test_tick(testAlgo):
    testAlgo.func = Mock()
    testAlgo.tick()
    testAlgo.func.assert_called_once_with(testAlgo)
