import globalVariables as g
import streaming
from algoClass import Algo

from datetime import datetime
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from pytest import fixture
from unittest.mock import patch, call

def test_process_bar(bars, indicators):
    # setup
    g.assets['min']['AAPL'] = bars.iloc[:-1]
    data = bars.iloc[-1].copy().drop('2_min_mom')
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
        'volume', 'ticked', '2_day_mom'])
    dayBars['vwap'] = 837.59
    yesterday = g.nyc.localize(datetime(2020, 2, 12))
    g.assets['day']['AAPL'] = DataFrame(dayBars, [yesterday])

    # expected day bars
    newBar = {
        'open': bars.open[1], # 1st bar before market open
        'high': bars.high[1:].max(),
        'low': bars.low[1:].min(),
        'close': bars.close[-1],
        'volume': bars.volume[1:].sum(),
        'ticked': False}
    newBar['vwap'] = (bars.volume[1:] * bars.vwap[1:]).sum() / newBar['volume']
    newBar['2_day_mom'] = newBar['vwap'] / dayBars['vwap'] - 1
    date = g.nyc.localize(datetime(2020, 2, 13))
    expected = g.assets['day']['AAPL'].append(DataFrame(newBar, [date]))
    
    # test
    marketOpen = g.nyc.localize(datetime(2020, 2, 13, 16, 20))
    with patch('streaming.timing.get_market_open', return_value=marketOpen):
        streaming.compile_day_bars(indicators)
    assert_frame_equal(g.assets['day']['AAPL'], expected, False)

def test_process_algo_trade(testAlgo):
    # enter same side fill
    testAlgo.longShort = 'short'
    testAlgo.pendingOrders['AAPL'] = {'qty': -5, 'price': 10.30}
    testAlgo.positions['AAPL'] = {'qty': -3, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, -7, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': -8, 'basis': 8.50}
    assert testAlgo.buyPow == 1001.50

    # enter same side partial
    testAlgo.longShort = 'short'
    testAlgo.pendingOrders['AAPL'] = {'qty': -5, 'price': 10.30}
    testAlgo.positions['AAPL'] = {'qty': -3, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, -3, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': -6, 'basis': 8.00}
    assert testAlgo.buyPow == 1021.50

    # enter same side zero
    testAlgo.longShort = 'short'
    testAlgo.pendingOrders['AAPL'] = {'qty': -5, 'price': 10.30}
    testAlgo.positions['AAPL'] = {'qty': -3, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 0, 0)
    assert testAlgo.positions['AAPL'] == {'qty': -3, 'basis': 6.00}
    assert testAlgo.buyPow == 1051.50

    # enter opposite side fill
    testAlgo.longShort = 'long'
    testAlgo.pendingOrders['AAPL'] = {'qty': 5, 'price': 10.10}
    testAlgo.positions['AAPL'] = {'qty': 3, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, -7, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': 8, 'basis': 8.50}
    assert testAlgo.buyPow == 1000.50

    # enter opposite side partial
    testAlgo.longShort = 'long'
    testAlgo.pendingOrders['AAPL'] = {'qty': 5, 'price': 10.10}
    testAlgo.positions['AAPL'] = {'qty': 3, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, -3, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': 8, 'basis': 8.50}
    assert testAlgo.buyPow == 1000.50

    # enter opposite side zero
    testAlgo.longShort = 'long'
    testAlgo.pendingOrders['AAPL'] = {'qty': 5, 'price': 10.10}
    testAlgo.positions['AAPL'] = {'qty': 3, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 0, 0)
    assert testAlgo.positions['AAPL'] == {'qty': 3, 'basis': 6.00}
    assert testAlgo.buyPow == 1050.50

    # exit same side fill
    testAlgo.longShort = 'short'
    testAlgo.pendingOrders['AAPL'] = {'qty': 5, 'price': 9.90}
    testAlgo.positions['AAPL'] = {'qty': -8, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 7, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': -3, 'basis': 6.00}
    assert testAlgo.buyPow == 1010.00

    # exit same side partial
    testAlgo.longShort = 'short'
    testAlgo.pendingOrders['AAPL'] = {'qty': 5, 'price': 9.90}
    testAlgo.positions['AAPL'] = {'qty': -8, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 3, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': -5, 'basis': 6.00}
    assert testAlgo.buyPow == 1006.00

    # exit same side zero
    testAlgo.longShort = 'short'
    testAlgo.pendingOrders['AAPL'] = {'qty': 5, 'price': 9.90}
    testAlgo.positions['AAPL'] = {'qty': -8, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 0, 0)
    assert testAlgo.positions['AAPL'] == {'qty': -8, 'basis': 6.00}
    assert testAlgo.buyPow == 1000.00

    # exit opposite side fill
    testAlgo.longShort = 'long'
    testAlgo.pendingOrders['AAPL'] = {'qty': -5, 'price': 9.90}
    testAlgo.positions['AAPL'] = {'qty': 8, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 7, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': 3, 'basis': 6.00}
    assert testAlgo.buyPow == 1050.00

    # exit opposite side partial
    testAlgo.longShort = 'long'
    testAlgo.pendingOrders['AAPL'] = {'qty': -5, 'price': 9.90}
    testAlgo.positions['AAPL'] = {'qty': 8, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 3, 10.00)
    assert testAlgo.positions['AAPL'] == {'qty': 3, 'basis': 6.00}
    assert testAlgo.buyPow == 1050.00

    # exit opposite side zero
    testAlgo.longShort = 'long'
    testAlgo.pendingOrders['AAPL'] = {'qty': -5, 'price': 9.90}
    testAlgo.positions['AAPL'] = {'qty': 8, 'basis': 6.00}
    testAlgo.buyPow = 1000.00
    streaming.process_algo_trade('AAPL', testAlgo, 0, 0)
    assert testAlgo.positions['AAPL'] == {'qty': 8, 'basis': 6.00}
    assert testAlgo.buyPow == 1000.00

def test_process_trade():
    ## SETUP

    # algos
    algos = []
    orders = [-9, 3, -7, -5]
    for qty in orders:
        algo = Algo('min', print, [], 'short', False)
        algo.pendingOrders['AAPL'] = {'qty': qty}
        algos.append(algo)

    # global
    g.orders['54321'] = {
        'symbol': 'AAPL',
        'qty': -12,
        'price': 9.90,
        'algos': algos}
    g.positions['AAPL'] = 12

    # websocket
    class data:
        event = 'canceled'
        order = {'id': '54321',
            'symbol': 'AAPL',
            'side': 'sell',
            'filled_qty': '12',
            'filled_avg_price': '10.00'}
    

    ## TEST

    with patch('streaming.process_algo_trade') as process_algo_trade:
        streaming.process_trade(data)
        assert g.positions['AAPL'] == 0
        assert '54321' not in g.orders
        calls = [
            call('AAPL', algos[1], -12, 10.00),
            call('AAPL', algos[0], -15, 10.00),
            call('AAPL', algos[2], -6, 10.00),
            call('AAPL', algos[3], -0, 10.00)]
        process_algo_trade.assert_has_calls(calls)
        assert process_algo_trade.call_count == 4
        for algo in algos:
            assert 'AAPL' not in algo.pendingOrders

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

# NOTE: skip stream
