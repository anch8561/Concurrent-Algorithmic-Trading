from algoClasses import Algo

def null_func(*args): return

def test_Algo():
    testAlgo = Algo(null_func, a=1, b=2)
    assert testAlgo.name == '1_2_null_func'

def test_activate():
    # setup
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
    testAlgo.active = False
    testAlgo.start = null_func # remove alpaca calendar dependency

    # test
    testAlgo.activate()
    assert testAlgo.active == True

def test_deactivate():
    # setup
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
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

# skip start and stop as they only call other methods

from config import algoPath
import json
from os import remove

def test_save_data():
    # setup
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
    testAlgo.equity = {'long': 0, 'short': 1}
    
    # test
    testAlgo.save_data()
    fileName = algoPath + testAlgo.name + '.data'
    with open(fileName, 'r') as f:
        data = json.load(f)
    assert data['equity'] == testAlgo.equity

def test_load_data():
    # setup
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
    testAlgo.equity = {'long': 1, 'short': 0}
    data = {'equity': {'long': 0, 'short': 1}}
    fileName = algoPath + testAlgo.name + '.data'
    with open(fileName, 'w') as f:
        json.dump(data, f)

    # test
    testAlgo.load_data()
    assert testAlgo.equity == data['equity']

from unittest.mock import Mock

def test_enter_position():
    # setup
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
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
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
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
    try: remove(algoPath + 'null_func.data')
    except: pass
    testAlgo = Algo(null_func)
    testAlgo.alpaca = Mock()
    order = Mock()
    order.id = '1234'
    testAlgo.alpaca.submit_order = Mock(return_value=order)
    
    # zero quantity
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.submit_order('AAPL', 0, 111.11, 'enter')
    testAlgo.alpaca.submit_order.assert_not_called()

    # allPositions zero crossing
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.allPositions['AAPL'] = {'qty': 1, 'basis': 0}
    testAlgo.submit_order('AAPL', -2, 111.11, 'enter')
    testAlgo.alpaca.submit_order.assert_called_once_with(
        symbol = 'AAPL',
        qty = 1,
        side = 'sell',
        type = 'limit',
        time_in_force = 'day',
        limit_price = 111.11)
    testAlgo.allPositions.pop('AAPL')
    
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
    testAlgo.allOrders.pop('5678')

    # enter market order
    testAlgo.alpaca.submit_order.reset_mock()
    testAlgo.submit_order('AAPL', -2, None, 'enter')
    testAlgo.alpaca.submit_order.assert_not_called()
    
    # exit market order
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
    




