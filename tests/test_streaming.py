import globalVariables as g
import streaming
from Algo import Algo

from datetime import datetime
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from pytest import fixture
from unittest.mock import patch, call

def test_process_bar(bars, indicators):
    # setup
    g.assets['min']['AAPL'] = bars.iloc[:-1]
    data = bars.iloc[-1].copy().drop('1_min_momentum')
    data['start'] = bars.index[-1]
    data['symbol'] = 'AAPL'

    # test
    with patch('streaming.timing.get_time', return_value=123):
        streaming.process_bar('min', data, indicators)
    g.assets['min']['AAPL'].equals(bars)
    assert g.lastBarReceivedTime == 123

def test_compile_day_bars(bars, indicators):
    ## SETUP

    # min bars
    g.assets['min']['AAPL'] = bars

    # old day bars
    dayBars = dict.fromkeys(['open', 'high', 'low', 'close',
        'volume', 'ticked', '1_day_momentum'])
    yesterday = g.nyc.localize(datetime(2020, 2, 12))
    g.assets['day']['AAPL'] = DataFrame(dayBars, [yesterday])

    # expected day bars
    date = g.nyc.localize(datetime(2020, 2, 13))
    newBar = {
        'open': 345.67,
        'high': 600.02,
        'low': 111.11,
        'close': 575.04,
        'volume': 8888 + 7777 + 5555,
        'ticked': False,
        '1_day_momentum': (575.04 - 345.67) / 345.67}
    expected = g.assets['day']['AAPL'].append(
        DataFrame(newBar, [date]))
    
    # test
    marketOpen = g.nyc.localize(datetime(2020, 2, 13, 16, 20))
    with patch('streaming.timing.get_market_open', return_value=marketOpen):
        streaming.compile_day_bars(indicators)
    assert_frame_equal(g.assets['day']['AAPL'], expected, False)

def test_process_algo_trade(testAlgo):
    # enter same side
    algoOrder = {
        'algo': testAlgo,
        'longShort': 'short',
        'qty': -5}
    testAlgo.pendingOrders['AAPL'] = algoOrder
    testAlgo.positions['AAPL'] = 2
    testAlgo.buyPow = 1000
    streaming.process_algo_trade('AAPL', algoOrder, 9.90, -7, 10.00)
    assert testAlgo.positions['AAPL'] == -3
    assert testAlgo.buyPow == 1000.50
    assert 'AAPL' not in testAlgo.pendingOrders

    # enter opposite side
    algoOrder = {
        'algo': testAlgo,
        'longShort': 'long',
        'qty': 5}
    testAlgo.pendingOrders['AAPL'] = algoOrder
    testAlgo.positions['AAPL'] = 2
    testAlgo.buyPow = 1000
    streaming.process_algo_trade('AAPL', algoOrder, 9.90, -7, 10.00)
    assert testAlgo.positions['AAPL'] == 7
    assert testAlgo.buyPow == 1000.50
    assert 'AAPL' not in testAlgo.pendingOrders

    # exit same side
    algoOrder = {
        'algo': testAlgo,
        'longShort': 'short',
        'qty': 5}
    testAlgo.pendingOrders['AAPL'] = algoOrder
    testAlgo.positions['AAPL'] = 2
    testAlgo.buyPow = 1000
    streaming.process_algo_trade('AAPL', algoOrder, 9.90, -7, 10.00)
    assert testAlgo.positions['AAPL'] == 7
    assert testAlgo.buyPow == 1050
    assert 'AAPL' not in testAlgo.pendingOrders

    # exit opposite side
    algoOrder = {
        'algo': testAlgo,
        'longShort': 'long',
        'qty': -5}
    testAlgo.pendingOrders['AAPL'] = algoOrder
    testAlgo.positions['AAPL'] = 2
    testAlgo.buyPow = 1000
    streaming.process_algo_trade('AAPL', algoOrder, 9.90, -7, 10.00)
    assert testAlgo.positions['AAPL'] == -3
    assert testAlgo.buyPow == 1050
    assert 'AAPL' not in testAlgo.pendingOrders

@fixture
def tradeSetup():
    # global
    g.orders['54321'] = {
        'symbol': 'AAPL',
        'qty': -12,
        'price': 10.10,
        'algoOrders': []}
    g.positions['AAPL'] = 12

    # algos
    algos = []
    algo = Algo(print, 'short', False, n=0) # reduced exit
    algo.buyPow = {'long': 10000, 'short': 10000}
    algo.positions['AAPL'] = 8
    algo.pendingOrders['AAPL'] = {
        'algo': algo,
        'longShort': 'long',
        'qty': -7}
    algo.pendingOrders['AAPL'] = {
        'algo': algo,
        'longShort': 'short',
        'qty': -6}
    algos.append(algo)
    g.orders['54321']['algoOrders'].append(
        algo.pendingOrders['AAPL'])
    g.orders['54321']['algoOrders'].append(
        algo.pendingOrders['AAPL'])

    algo = Algo(print, 'short', False, n=1) # opposing order
    algo.buyPow = {'long': 10000, 'short': 10000}
    algo.positions['AAPL'] = -3
    algo.pendingOrders['AAPL'] = {
        'algo': algo,
        'longShort': 'short',
        'qty': 3}
    algos.append(algo)
    g.orders['54321']['algoOrders'].append(
        algo.pendingOrders['AAPL'])
    
    algo = Algo(print, 'short', False, n=2) # cancelled exit
    algo.buyPow = {'long': 10000, 'short': 10000}
    algo.positions['AAPL'] = 5
    algo.pendingOrders['AAPL'] = {
        'algo': algo,
        'longShort': 'short',
        'qty': -2}
    algos.append(algo)
    g.orders['54321']['algoOrders'].append(
        algo.pendingOrders['AAPL'])

    # websocket
    class data:
        event = 'fill'
        order = {'id': '54321',
            'symbol': 'AAPL',
            'side': 'sell',
            'filled_qty': '12',
            'filled_avg_price': '10.00'}
    
    # exit
    return data, algos

def test_process_trade_FILL(tradeSetup):
    # TODO: patch process_algo_trade
    data, algos = tradeSetup
    streaming.process_trade(data)
    assert g.positions['AAPL'] == 0
    assert '54321' not in g.orders
    assert algos[0].positions['AAPL'] == -5
    assert algos[0].buyPow == {'long': 10070, 'short': 10000.6}
    assert '54321' not in algos[0].pendingOrders
    assert '54321' not in algos[0].pendingOrders
    assert algos[1].positions['AAPL'] == 0
    assert algos[1].buyPow == {'long': 10000, 'short': 10030}
    assert '54321' not in algos[1].pendingOrders
    assert '54321' not in algos[1].pendingOrders
    assert algos[2].positions['AAPL'] == 3
    assert algos[2].buyPow == {'long': 10000, 'short': 10000.2}
    assert '54321' not in algos[2].pendingOrders
    assert '54321' not in algos[2].pendingOrders

def test_process_trade_CANCELLED(tradeSetup):
    data, algos = tradeSetup
    data.event = 'canceled'
    data.order['filled_qty'] = '8'

    streaming.process_trade(data)
    assert g.positions['AAPL'] == 4
    assert '54321' not in g.orders
    assert algos[0].positions['AAPL'] == -3
    assert algos[0].buyPow == {'long': 10070, 'short': 10020.6}
    assert '54321' not in algos[0].pendingOrders
    assert '54321' not in algos[0].pendingOrders
    assert algos[1].positions['AAPL'] == 0
    assert algos[1].buyPow == {'long': 10000, 'short': 10030}
    assert '54321' not in algos[1].pendingOrders
    assert '54321' not in algos[1].pendingOrders
    assert algos[2].positions['AAPL'] == 5
    assert algos[2].buyPow == {'long': 10000, 'short': 10020.2}
    assert '54321' not in algos[2].pendingOrders
    assert '54321' not in algos[2].pendingOrders

def test_process_bars_backlog(indicators):
    # setup
    calls = []
    for ii in range(2):
        streaming.barsBacklog['sec'].append(ii)
        streaming.barsBacklog['min'].append(ii)
        calls.append(call('sec', ii, indicators))
        calls.append(call('min', ii, indicators))

    # test
    with patch('streaming.process_bar') as process_bar:
        streaming.process_bars_backlog(indicators)
        process_bar.assert_has_calls(calls, True)
        assert process_bar.call_count == 4
        assert streaming.barsBacklog == {'sec': [], 'min': []}

def test_process_trades_backlog():
    # setup
    calls = []
    for ii in range(5):
        streaming.tradesBacklog.append(ii)
        calls.append(call(ii))

    # test
    with patch('streaming.process_trade') as process_trade:
        streaming.process_trades_backlog()
        process_trade.assert_has_calls(calls, True)
        assert process_trade.call_count == 5
        assert streaming.tradesBacklog == []

def test_process_backlogs(indicators):
    with patch('streaming.backlogLock') as backlogLock, \
    patch('streaming.process_bars_backlog') as process_bars_backlog, \
    patch('streaming.process_trades_backlog') as process_trades_backlog:
        streaming.process_backlogs(indicators)
        backlogLock.acquire.assert_called_once_with()
        process_bars_backlog.assert_called_once_with(indicators)
        process_trades_backlog.assert_called_once_with()
        backlogLock.release.assert_called_once_with()

# NOTE: skip stream as it depends on websockets
