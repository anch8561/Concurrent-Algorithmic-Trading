import globalVariables as g
import streaming

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

@fixture
def tradeSetup(testAlgo):
    # global
    g.paperOrders['54321'] = {
        'symbol': 'AAPL',
        'qty': -12,
        'limit': 222.22,
        'enterExit': 'enter',
        'algo': testAlgo}
    g.paperPositions['AAPL'] = {'qty': 23, 'basis': 221.02}

    # algo
    testAlgo.buyPow = {'long': 10000, 'short': 10000}
    testAlgo.orders = g.paperOrders.copy()
    testAlgo.positions['AAPL'] = {'qty': 0, 'basis': 0}

    # websocket
    class data:
        event = 'fill'
        order = {'id': '54321',
            'symbol': 'AAPL',
            'side': 'sell',
            'qty': '12',
            'filled_qty': '12',
            'limit_price': '222.22',
            'filled_avg_price': '222.11'}
    
    # exit
    return data, testAlgo

def test_process_trade_ENTER(tradeSetup):
    data, testAlgo = tradeSetup
    streaming.process_trade(data)
    assert g.paperPositions['AAPL']['qty'] == 11
    assert g.paperPositions['AAPL']['basis'] - 219.830909 < 1e-6
    # (23 * 221.02 - 12 * 222.11) / (23 - 12)
    assert testAlgo.positions['AAPL'] == {'qty': -12, 'basis': 222.11}
    assert testAlgo.buyPow == {'long': 10000, 'short': 10001.32}
    # 10000 + 12 * (222.11 - 222.22)
    assert '54321' not in g.paperOrders
    assert '54321' not in testAlgo.orders

def test_process_trade_EXIT_NO_LIMIT(tradeSetup):
    data, testAlgo = tradeSetup

    # setup
    g.paperOrders['54321']['enterExit'] = 'exit'
    testAlgo.orders['54321']['enterExit'] = 'exit'
    testAlgo.positions['AAPL'] = {'qty': 12, 'basis': 222.01}
    
    g.paperOrders['54321']['limit'] = None
    testAlgo.orders['54321']['limit'] = None
    data.order.pop('limit_price')

    # test
    streaming.process_trade(data)
    assert g.paperPositions['AAPL']['qty'] == 11
    assert g.paperPositions['AAPL']['basis'] - 219.830909 < 1e-6
    # (23 * 221.02 - 12 * 222.11) / (23 - 12)
    assert testAlgo.positions['AAPL'] == {'qty': 0, 'basis': 0}
    assert testAlgo.buyPow == {'long': 12665.32, 'short': 10000}
    # 10000 + 12 * 222.11
    assert '54321' not in g.paperOrders
    assert '54321' not in testAlgo.orders

def test_process_trade_PARTIAL_FILL(tradeSetup):
    data, testAlgo = tradeSetup
    data.event = 'partial_fill'
    streaming.process_trade(data)
    assert g.paperPositions['AAPL']['qty'] == 23
    assert g.paperPositions['AAPL']['basis'] == 221.02
    assert testAlgo.positions['AAPL'] == {'qty': 0, 'basis': 0}
    assert testAlgo.buyPow == {'long': 10000, 'short': 10000}
    assert '54321' in g.paperOrders
    assert '54321' in testAlgo.orders

def test_process_trade_REJECTED(tradeSetup):
    data, testAlgo = tradeSetup
    data.event = 'rejected'
    streaming.process_trade(data)
    assert g.paperPositions['AAPL']['qty'] == 23
    assert g.paperPositions['AAPL']['basis'] == 221.02
    assert testAlgo.positions['AAPL'] == {'qty': 0, 'basis': 0}
    assert testAlgo.buyPow == {'long': 10000, 'short': 12666.64}
    assert '54321' not in g.paperOrders
    assert '54321' not in testAlgo.orders

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
