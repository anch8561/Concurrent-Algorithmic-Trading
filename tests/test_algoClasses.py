import config as c
import globalVariables as g
from algoClasses import Algo

import json, logging
from copy import deepcopy
from os import remove
from pandas import DataFrame
from unittest.mock import Mock

logging.basicConfig(level=logging.DEBUG)

def null_func(*args): return

def TestAlgo():
    try: remove(c.algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
    testAlgo.alpaca = Mock()
    testAlgo.allOrders = {}
    testAlgo.allPositions = {}
    return testAlgo

def test_Algo():
    testAlgo = Algo(null_func, a=1, b=2)
    assert testAlgo.name == '1_2_null_func'

def test_activate():
    # setup
    testAlgo = TestAlgo()
    testAlgo.active = False
    testAlgo.start = null_func # remove alpaca calendar dependency

    # test
    testAlgo.activate()
    assert testAlgo.active == True

def test_deactivate():
    # setup
    testAlgo = TestAlgo()
    testAlgo.active = True
    testAlgo.stop = null_func # remove alpaca calendar dependency

    # open position
    testAlgo.positions = {
        'AAPL': {'qty': 0, 'basis': 0},
        'MSFT': {'qty': -1, 'basis': 0},
        'TSLA': {'qty': 0, 'basis': 0}
    }
    testAlgo.deactivate()
    assert testAlgo.active == True

    # typical
    testAlgo.positions = {
        'AAPL': {'qty': 0, 'basis': 0},
        'MSFT': {'qty': 0, 'basis': 0},
        'TSLA': {'qty': 0, 'basis': 0}
    }
    testAlgo.deactivate()
    assert testAlgo.active == False

# NOTE: skip start and stop as they only call other methods

def test_save_data():
    # setup
    testAlgo = TestAlgo()
    testAlgo.equity = {'long': 0, 'short': 1}
    
    # test
    testAlgo.save_data()
    fileName = c.algoPath + testAlgo.name + '.data'
    with open(fileName, 'r') as f:
        data = json.load(f)
    assert data['equity'] == testAlgo.equity

def test_load_data():
    # setup
    testAlgo = TestAlgo()
    testAlgo.equity = {'long': 1, 'short': 0}
    data = {'equity': {'long': 0, 'short': 1}}
    fileName = c.algoPath + testAlgo.name + '.data'
    with open(fileName, 'w') as f:
        json.dump(data, f)

    # test
    testAlgo.load_data()
    assert testAlgo.equity == data['equity']

def test_enter_position():
    # setup
    testAlgo = TestAlgo()
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.get_limit_price = Mock(return_value=111.11)
    testAlgo.get_trade_qty = Mock(return_value=-2)
    testAlgo.submit_order = Mock()

    # test
    testAlgo.enter_position('AAPL', 'sell')
    testAlgo.submit_order.assert_called_once_with(
        'AAPL', -2, 111.11, 'enter')
    assert testAlgo.buyPow == {'long': 0, 'short': -2*111.11}

def test_exit_position():
    # setup
    testAlgo = TestAlgo()
    testAlgo.buyPow = {'long': 0, 'short': 0}
    testAlgo.positions = {'AAPL': {'qty': -2, 'basis': 0}}
    testAlgo.get_limit_price = Mock(return_value=111.11)
    testAlgo.submit_order = Mock()

    # test
    testAlgo.exit_position('AAPL')
    testAlgo.submit_order.assert_called_once_with(
        'AAPL', 2, 111.11, 'exit')

def test_submit_order():
    # setup
    testAlgo = TestAlgo()
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
    testAlgo.allPositions = {'AAPL': {'qty': 1, 'basis': 0}}
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

def test_get_limit_price():
    # setup
    testAlgo = TestAlgo()
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

def test_get_price():
    # setup
    testAlgo = TestAlgo()
    assetsCopy = deepcopy(g.assets)
    g.assets['min']['AAPL'] = DataFrame({'close': 111.11}, [0])

    # test
    assert testAlgo.get_price('AAPL') == 111.11
    g.assets = assetsCopy

def test_get_trade_qty():
    # setup
    testAlgo = TestAlgo()
    cash = 100 * c.minShortPrice / c.maxPosFrac
    testAlgo.equity['short'] = cash
    testAlgo.buyPow['short'] = cash
    price = c.minShortPrice + 1
    maxPosQty = -int(c.maxPosFrac * cash / price)
    assetsCopy = deepcopy(g.assets)
    volume = int(cash / c.minShortPrice)
    g.assets['min']['AAPL'] = DataFrame({'volume': volume}, [0])
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
    g.assets['min']['AAPL'] = DataFrame({'volume': volume}, [0])
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == -volume
    volume = volumeCopy
    g.assets['min']['AAPL'] = DataFrame({'volume': volume}, [0])
    
    # zero
    buyPowCopy = testAlgo.buyPow['short']
    testAlgo.buyPow['short'] = 0
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == 0
    testAlgo.buyPow['short'] = buyPowCopy

    # existing position (same side smaller)
    testAlgo.positions['AAPL'] = {'qty': -1, 'basis': 0}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == maxPosQty + 1
    testAlgo.positions = {}

    # existing position (same side larger)
    testAlgo.positions['AAPL'] = {'qty': maxPosQty-1, 'basis': 0}
    testQty = testAlgo.get_trade_qty('AAPL', 'sell', price)
    assert testQty == 0
    testAlgo.positions = {}

    # existing position (opposite side)
    testAlgo.positions['AAPL'] = {'qty': 1, 'basis': 0}
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

    # reset assets
    g.assets = assetsCopy
