
import algoClasses
import config as c
import globalVariables as g

import json
from os import remove
from pandas import DataFrame
from pytest import fixture
from unittest.mock import Mock

@fixture
def testAlgo(reloadGlobalVariables):
    testAlgo = algoClasses.Algo(print, False)
    testAlgo.alpaca = Mock()
    testAlgo.allOrders = {}
    testAlgo.allPositions = {}
    return testAlgo

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
        'AAPL': {'qty': 0},
        'MSFT': {'qty': -1},
        'TSLA': {'qty': 0}
    }
    testAlgo.deactivate()
    testAlgo.stop.assert_not_called()
    assert testAlgo.active == True

    # typical
    testAlgo.positions = {
        'AAPL': {'qty': 0},
        'MSFT': {'qty': 0},
        'TSLA': {'qty': 0}
    }
    testAlgo.deactivate()
    testAlgo.stop.assert_called_once()
    assert testAlgo.active == False

# NOTE: skip start and stop as they only call other methods

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

def test_enter_position(testAlgo):
    # setup
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.get_limit_price = Mock(return_value=111.11)
    testAlgo.get_trade_qty = Mock(return_value=-2)
    testAlgo.submit_order = Mock()

    # test
    testAlgo.enter_position('AAPL', 'sell')
    testAlgo.submit_order.assert_called_once_with(
        'AAPL', -2, 111.11, 'enter')
    assert testAlgo.buyPow == {'long': 0, 'short': -2*111.11}

def test_exit_position(testAlgo):
    # setup
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.positions['AAPL'] = {'qty': -2}
    testAlgo.get_limit_price = Mock(return_value=111.11)
    testAlgo.submit_order = Mock()

    # test
    testAlgo.exit_position('AAPL')
    testAlgo.submit_order.assert_called_once_with(
        'AAPL', 2, 111.11, 'exit')

def test_submit_order(testAlgo):
    # setup
    order = Mock()
    order.id = '1234'
    testAlgo.alpaca.submit_order = Mock(return_value=order)
    
    # zero quantity
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.submit_order('AAPL', 0, 111.11, 'enter')
    testAlgo.alpaca.submit_order.assert_not_called()
    testAlgo.orders = {}
    testAlgo.allOrders = {}

    # allPositions zero crossing
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.allPositions['AAPL'] = {'qty': 1}
    testAlgo.submit_order('AAPL', -2, 111.11, 'enter')
    testAlgo.alpaca.submit_order.assert_called_once_with(
        symbol = 'AAPL',
        qty = 1,
        side = 'sell',
        type = 'limit',
        time_in_force = 'day',
        limit_price = 111.11)
    testAlgo.orders = {}
    testAlgo.allOrders = {}
    testAlgo.allPositions = {}
    
    # allOrders opposing short
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.allOrders['5678'] = {
                'symbol': 'AAPL',
                'qty': -2,
                'limit': 111.11,
                'enterExit': 'enter',
                'algo': testAlgo}
    testAlgo.submit_order('AAPL', 2, 111.11, 'enter')
    testAlgo.alpaca.submit_order.assert_not_called()
    testAlgo.orders = {}
    testAlgo.allOrders = {}

    # market order (enter)
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.submit_order('AAPL', -2, None, 'enter')
    testAlgo.alpaca.submit_order.assert_not_called()
    testAlgo.orders = {}
    testAlgo.allOrders = {}
    
    # market order (exit)
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.submit_order('AAPL', -2, None, 'exit')
    testAlgo.alpaca.submit_order.assert_called_once_with(
        symbol = 'AAPL',
        qty = 2,
        side = 'sell',
        type = 'market',
        time_in_force = 'day')
    assert testAlgo.orders['1234'] == {
        'symbol': 'AAPL',
        'qty': -2,
        'limit': None,
        'enterExit': 'exit'}
    assert testAlgo.allOrders['1234'] == {
        'symbol': 'AAPL',
        'qty': -2,
        'limit': None,
        'enterExit': 'exit',
        'algo': testAlgo}
    testAlgo.orders = {}
    testAlgo.allOrders = {}

    # typical
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.submit_order('AAPL', -2, 111.11, 'enter')
    testAlgo.alpaca.submit_order.assert_called_once_with(
        symbol = 'AAPL',
        qty = 2,
        side = 'sell',
        type = 'limit',
        time_in_force = 'day',
        limit_price = 111.11)
    assert testAlgo.orders['1234'] == {
        'symbol': 'AAPL',
        'qty': -2,
        'limit': 111.11,
        'enterExit': 'enter'}
    assert testAlgo.allOrders['1234'] == {
        'symbol': 'AAPL',
        'qty': -2,
        'limit': 111.11,
        'enterExit': 'enter',
        'algo': testAlgo}
    testAlgo.orders = {}
    testAlgo.allOrders = {}

# NOTE: skip cancel_all_orders as it depends on streaming

def test_get_limit_price(testAlgo):
    # setup
    testAlgo.get_price = Mock(return_value=111.11)

    # buy
    testPrice = testAlgo.get_limit_price('AAPL', 'buy')
    realPrice = 111.11 * (1 + c.limitPriceFrac)
    assert testPrice == realPrice

    # sell
    testPrice = testAlgo.get_limit_price('AAPL', 'sell')
    realPrice = 111.11 * (1 - c.limitPriceFrac)
    assert testPrice == realPrice

def test_get_metrics(): pass # TODO: WIP function

def test_get_price(testAlgo):
    g.assets['min']['AAPL'] = DataFrame({'close': 111.11}, ['a'])
    assert testAlgo.get_price('AAPL') == 111.11

def test_get_trade_qty(testAlgo):
    # setup
    cash = 100 * c.minShortPrice / c.maxPosFrac
    testAlgo.equity['short'] = cash
    testAlgo.buyPow['short'] = cash
    price = c.minShortPrice + 1
    maxPosQty = -int(c.maxPosFrac * cash / price)
    volume = int(cash / c.minShortPrice)
    g.assets['min']['AAPL'] = DataFrame({'volume': volume}, ['a'])
    testAlgo.alpaca.cancel_order = Mock()

    # min price
    priceCopy = price
    price = c.minShortPrice - 1
    qty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert qty == 0
    price = priceCopy

    # max position fraction
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == maxPosQty

    # buying power
    buyPowCopy = testAlgo.buyPow['short']
    testAlgo.buyPow['short'] = c.maxPosFrac * cash / 2
    realQty = -int(testAlgo.buyPow['short'] / price)
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == realQty
    testAlgo.buyPow['short'] = buyPowCopy

    # volume
    volumeCopy = volume
    volume = maxPosQty - 1
    g.assets['min']['AAPL'] = DataFrame({'volume': volume}, ['a'])
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == -volume
    volume = volumeCopy
    g.assets['min']['AAPL'] = DataFrame({'volume': volume}, ['a'])
    
    # zero
    buyPowCopy = testAlgo.buyPow['short']
    testAlgo.buyPow['short'] = 0
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == 0
    testAlgo.buyPow['short'] = buyPowCopy

    # existing position (same side smaller)
    testAlgo.positions['AAPL'] = {'qty': -1}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == maxPosQty + 1
    testAlgo.positions = {}

    # existing position (same side larger)
    testAlgo.positions['AAPL'] = {'qty': maxPosQty-1}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == 0
    testAlgo.positions = {}

    # existing position (opposite side)
    testAlgo.positions['AAPL'] = {'qty': 1}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == -1
    testAlgo.positions = {}

    # existing order (opposite side)
    testAlgo.orders['1234'] = {
        'symbol': 'AAPL',
        'qty': 2,
        'limit': 111.11,
        'enterExit': 'enter'}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    testAlgo.alpaca.cancel_order.assert_called_once_with('1234')
    assert testQty == maxPosQty
    testAlgo.orders = {}

    # existing order (same side)
    testAlgo.orders['1234'] = {
        'symbol': 'AAPL',
        'qty': -2,
        'limit': 111.11,
        'enterExit': 'enter'}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == 0
    testAlgo.orders = {}

def test_set_live(testAlgo):
    testAlgo.set_live(True)
    assert testAlgo.alpaca == g.alpacaLive
    assert testAlgo.allOrders == g.liveOrders
    assert testAlgo.allPositions == g.livePositions

# NOTE: skip set_ticking as it depends on streaming

def test_update_equity(testAlgo):
    # setup
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.positions = {
        'AAPL': {'qty': 2},
        'MSFT': {'qty': -1},
        'TSLA': {'qty': 0}
    }

    # typical
    testAlgo.get_price = Mock(return_value=111.11)
    testAlgo.update_equity()
    assert testAlgo.equity == {'long': 222.22, 'short': 111.11}

    # untracked position
    testAlgo.get_price = Mock(return_value=None)
    testAlgo.exit_position = Mock()
    last_trade = Mock()
    last_trade.price = 111.11
    testAlgo.alpaca.get_last_trade = Mock(return_value=last_trade)
    testAlgo.update_equity()
    assert testAlgo.equity == {'long': 222.22, 'short': 111.11}

# NOTE: skip update_history as it depends on timing

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
