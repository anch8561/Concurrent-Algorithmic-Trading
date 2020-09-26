import globalVariables as g
import timing

from alpaca_trade_api.entity import Calendar
from datetime import datetime
from pytest import fixture
from unittest.mock import call, Mock, patch


@fixture
def alpaca():
    class alpaca:
        calendar = [
            Calendar({
                'date': '1996-02-07',
                'open': '09:30',
                'close': '16:00'}),
            Calendar({
                'date': '1996-02-11',
                'open': '09:31',
                'close': '16:01'}),
            Calendar({
                'date': '1996-02-12',
                'open': '09:32',
                'close': '16:02'}),
            Calendar({
                'date': '1996-02-14',
                'open': '09:33',
                'close': '16:03'}),
            Calendar({
                'date': '1996-02-15',
                'open': '09:34',
                'close': '16:04'}),
            Calendar({
                'date': '1996-02-18',
                'open': '09:35',
                'close': '16:05'})]
        # pylint: disable=no-method-argument
        def get_calendar(): return alpaca.calendar
    return alpaca

@fixture
def now(reloadGlobalVariables):
    return g.nyc.localize(datetime(1996, 2, 13, 12, 34, 56, 123456))

def test_init_timing(alpaca):
    # setup
    g.alpacaPaper = alpaca
    class timedate(datetime):
        _now = None
        def now(self): return timedate._now

    # market day
    timedate._now = g.nyc.localize(datetime(1996, 2, 12, 12, 34, 56, 123456))
    with patch('timing.datetime', timedate):
        timing.init_timing()
    assert timing.calendar == alpaca.calendar
    assert timing.i_today == 2

    # weekend / holiday
    timedate._now = g.nyc.localize(datetime(1996, 2, 13, 12, 34, 56, 123456))
    with patch('timing.datetime', timedate):
        timing.init_timing()
    assert timing.calendar == alpaca.calendar
    assert timing.i_today == 3

def test_get_time():
    with patch('timing.datetime') as datetime:
        timing.get_time()
        datetime.now.assert_called_with(g.nyc)

def test_get_market_open(alpaca, now):
    with patch('timing.calendar', alpaca.calendar), \
    patch('timing.i_today', 3), \
    patch('timing.get_time', return_value=now):
        val = timing.get_market_open()
    expected = g.nyc.localize(datetime(1996, 2, 14, 9, 33))
    assert val == expected

def test_get_market_close(alpaca, now):
    with patch('timing.calendar', alpaca.calendar), \
    patch('timing.i_today', 3), \
    patch('timing.get_time', return_value=now):
        val = timing.get_market_close()
    expected = g.nyc.localize(datetime(1996, 2, 14, 16, 3))
    assert val == expected

def test_update_time():
    with patch('timing.get_time', return_value=1), \
    patch('timing.get_market_open', return_value=3), \
    patch('timing.get_market_close', return_value=4):
        timing.update_time()
    assert g.now == 1
    assert g.TTOpen == 2
    assert g.TTClose == 3

def test_get_time_str(now):
    with patch('timing.get_time', return_value=now):
        assert timing.get_time_str() == '12:34:56.123456'
    
def test_get_date(now):
    with patch('timing.get_time', return_value=now):
        assert timing.get_date(-2) == '1996-02-11'
        assert timing.get_date(0) == '1996-02-13'
        assert timing.get_date(2) == '1996-02-15'

def test_is_market_day(alpaca):
    # setup
    dates = [
        '1996-02-10',
        '1996-02-11',
        '1996-02-12',
        '1996-02-13',
        '1996-02-14',
        '1996-02-15',
        '1996-02-16']

    # today is market day
    def get_date(ii): return dates[ii+2] # pylint: disable=function-redefined
    with patch('timing.calendar', alpaca.calendar), \
    patch('timing.i_today', 2), \
    patch('timing.get_date', get_date):
        assert timing.is_market_day(-2) == False
        assert timing.is_market_day(-1) == True
        assert timing.is_market_day(0) == True
        assert timing.is_market_day(1) == False
        assert timing.is_market_day(2) == True
        assert timing.is_market_day(3) == True
        assert timing.is_market_day(4) == False

    # today is not market day
    def get_date(ii): return dates[ii+3]
    with patch('timing.calendar', alpaca.calendar), \
    patch('timing.i_today', 3), \
    patch('timing.get_date', get_date):
        assert timing.is_market_day(-3) == False
        assert timing.is_market_day(-2) == True
        assert timing.is_market_day(-1) == True
        assert timing.is_market_day(0) == False
        assert timing.is_market_day(1) == True
        assert timing.is_market_day(2) == True
        assert timing.is_market_day(3) == False

def test_get_market_date(alpaca):
    # today is market day
    with patch('timing.calendar', alpaca.calendar), \
    patch('timing.i_today', 2), \
    patch('timing.is_market_day', return_value=True):
        assert timing.get_market_date(-2) == '1996-02-07'
        assert timing.get_market_date(0) == '1996-02-12'
        assert timing.get_market_date(2) == '1996-02-15'

    # today is not market day
    with patch('timing.calendar', alpaca.calendar), \
    patch('timing.i_today', 3), \
    patch('timing.is_market_day', return_value=False):
        assert timing.get_market_date(-2) == '1996-02-11'
        assert timing.get_market_date(0) == '1996-02-14'
        assert timing.get_market_date(2) == '1996-02-15'
