import globalVariables as g
import streaming

from datetime import datetime
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from pytz import timezone
from unittest.mock import patch

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
        'volume', 'ticked', '1_day_momentum'], None)
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
    print(expected)
    print(g.assets['day']['AAPL'])
    assert_frame_equal(g.assets['day']['AAPL'], expected, False)

def test_process_trade():
    pass

def test_process_all_trades():
    pass

def test_stream():
    pass
