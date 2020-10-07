
import algoClasses
import config as c
import globalVariables as g

import json
from os import remove
from pandas import DataFrame
from unittest.mock import call, Mock, patch

def test_Algo():
    testAlgo = algoClasses.Algo(print, a=1, b=2)
    assert testAlgo.name == '1_2_print'

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
        'AAPL': 0,
        'MSFT': -1,
        'TSLA': 0}
    testAlgo.deactivate()
    testAlgo.stop.assert_not_called()
    assert testAlgo.active == True

    # typical
    testAlgo.positions = {
        'AAPL': 0,
        'MSFT': 0,
        'TSLA': 0}
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

def test_get_trade_qty(testAlgo):
    # setup
    cash = 100 * c.minPrice['short'] / c.maxPosFrac
    testAlgo.equity['short'] = cash
    testAlgo.buyPow['short'] = cash
    price = c.minPrice['short'] + 1
    maxPosQty = -int(c.maxPosFrac * cash / price)
    testAlgo.positions = {'AAPL': 0}

    # min price
    priceCopy = price
    price = c.minPrice['short'] - 1
    qty = testAlgo.get_trade_qty('AAPL', 'short', price)
    assert qty == 0
    price = priceCopy

    # max position
    testQty = testAlgo.get_trade_qty('AAPL', 'short', price)
    assert testQty == maxPosQty

    # buying power
    buyPowCopy = testAlgo.buyPow['short']
    testAlgo.buyPow['short'] = c.maxPosFrac * cash / 2
    realQty = -int(testAlgo.buyPow['short'] / price)
    testQty = testAlgo.get_trade_qty('AAPL', 'short', price)
    assert testQty == realQty
    testAlgo.buyPow['short'] = buyPowCopy

    # position (same side smaller)
    testAlgo.positions['AAPL'] = -1
    testQty = testAlgo.get_trade_qty('AAPL', 'short', price)
    assert testQty == maxPosQty + 1
    testAlgo.positions = {}

    # position (same side larger)
    testAlgo.positions['AAPL'] = maxPosQty-1
    testQty = testAlgo.get_trade_qty('AAPL', 'short', price)
    assert testQty == 0
    testAlgo.positions = {}

    # position (opposite side)
    testAlgo.positions['AAPL'] = 1
    testQty = testAlgo.get_trade_qty('AAPL', 'short', price)
    assert testQty == maxPosQty
    testAlgo.positions = {}

def test_queue_order(testAlgo): assert 0

def test_get_metrics(): pass # TODO: WIP function

def test_update_equity(testAlgo):
    # setup
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.positions = {
        'AAPL': 2,
        'MSFT': -1,
        'TSLA': 0}
    testAlgo.queue_order = Mock()
    g.alpaca = Mock()
    last_trade = Mock()
    last_trade.price = 111.11
    g.alpaca.get_last_trade = Mock(return_value=last_trade)

    # typical
    with patch('algoClasses.get_price', return_value=111.11):
        testAlgo.update_equity()
    assert testAlgo.equity == {'long': 222.22, 'short': 111.11}
    testAlgo.queue_order.assert_not_called()

    # untracked position
    with patch('algoClasses.get_price', return_value=None):
        testAlgo.update_equity()
    assert testAlgo.equity == {'long': 222.22, 'short': 111.11}
    calls = [
        call('AAPL', 'exit'),
        call('MSFT', 'exit')]
    testAlgo.queue_order.assert_has_calls(calls)
    testAlgo.queue_order.call_count == 2

def test_update_history(testAlgo):
    testAlgo.history = {}
    with patch('algoClasses.get_date', return_value='1996-02-13'), \
        patch('algoClasses.get_time_str', side_effect=['a', 'b']):
        testAlgo.equity = 123
        testAlgo.update_history('test1')
        assert testAlgo.history == {'1996-02-13': {
            'a': {'event': 'test1', 'equity': 123}}}

        testAlgo.equity = 456
        testAlgo.update_history('test2')
        assert testAlgo.history == {'1996-02-13': {
            'a': {'event': 'test1', 'equity': 123},
            'b': {'event': 'test2', 'equity': 456}}}

def test_NightAlgo_tick():
    # setup
    testAlgo = algoClasses.NightAlgo(print, False)
    def func(self):
        assert self.ticking == True
    testAlgo.func = Mock(side_effect=func)

    # too little buying power
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.tick()
    testAlgo.func.assert_not_called()

    # enough buying power
    testAlgo.buyPow = {
        'long': c.minTradeBuyPow,
        'short': c.minTradeBuyPow}
    testAlgo.tick()
    testAlgo.func.assert_called_once_with(testAlgo)

def test_DayAlgo_tick():
    # setup
    testAlgo = algoClasses.DayAlgo(print, False)
    def func(self):
        assert self.ticking == True
    testAlgo.func = Mock(side_effect=func)

    # test
    testAlgo.tick()
    testAlgo.func.assert_called_once_with(testAlgo)
