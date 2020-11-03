import backtest.historicBars as histBars

from datetime import datetime, timedelta
from pandas import DataFrame
from unittest.mock import call, Mock, patch

def test_get_historic_min_bars():
    class Barset:
        def __init__(self, data: dict, index: list):
            self.df = DataFrame(data, index)

    class alpaca:
        class polygon:
            def historic_agg_v2(self, symbol, multiplier, _from, to):
                index = []
                for ii in range(5000):
                    index.append(datetime(
                        _from.year,
                        _from.month,
                        _from.day) + timedelta(minutes=ii))
                for ii in range(1000):
                    index.append(datetime(
                        to.year,
                        to.month,
                        to.day) + timedelta(minutes=ii))
                return Barset({}, index)

    calendar = [
        {'open': datetime(2020, 10, 19, 9, 30),
        'close': datetime(2020, 10, 19, 16, 0)},
        {'open': datetime(2020, 10, 20, 9, 31),
        'close': datetime(2020, 10, 20, 16, 1)},
        {'open': datetime(2020, 10, 21, 9, 32),
        'close': datetime(2020, 10, 21, 16, 2)},
        {'open': datetime(2020, 10, 22, 9, 33),
        'close': datetime(2020, 10, 22, 16, 3)},
        {'open': datetime(2020, 10, 23, 9, 34),
        'close': datetime(2020, 10, 23, 16, 4)},
        {'open': datetime(2020, 10, 26, 9, 35),
        'close': datetime(2020, 10, 26, 16, 5)},
        {'open': datetime(2020, 10, 27, 9, 36),
        'close': datetime(2020, 10, 27, 16, 6)},
        {'open': datetime(2020, 10, 28, 9, 37),
        'close': datetime(2020, 10, 28, 16, 7)},
        {'open': datetime(2020, 10, 29, 9, 38),
        'close': datetime(2020, 10, 29, 16, 8)},
        {'open': datetime(2020, 10, 30, 9, 39),
        'close': datetime(2020, 10, 30, 16, 9)},
        {'open': datetime(2020, 10, 31, 9, 40),
        'close': datetime(2020, 10, 31, 16, 10)},
        {'open': datetime(2020, 11, 1, 9, 41),
        'close': datetime(2020, 11, 1, 16, 11)}]

    dayBars = {
        'AAPL': DataFrame({}, [
            datetime(2020, 10, 20),
            datetime(2020, 10, 21),
            datetime(2020, 10, 22),
            datetime(2020, 10, 23),
            datetime(2020, 10, 26)]),
        'MSFT': DataFrame({}, [
            datetime(2020, 10, 19),
            datetime(2020, 10, 20),
            datetime(2020, 10, 21)])}

    class timing:
        # pylint: disable=no-self-argument
        # pylint: disable=unsubscriptable-object
        def get_calendar_index(calendar, str):
            for ii, date in enumerate(calendar):
                if date['open'].strftime('%Y-%m-%d') == str:
                    return ii
        def get_calendar_date(calendar, idx):
            return calendar[idx]['open'].replace(
                hour = 0, minute = 0, second = 0, microsecond = 0)
        def get_market_open(calendar, idx):
            return calendar[idx]['open']
        def get_market_close(calendar, idx):
            return calendar[idx]['close']

    with patch('backtest.historicBars.timing', timing), \
    patch('backtest.historicBars.DataFrame.to_csv') as to_csv:
        histBars.get_historic_min_bars(alpaca, calendar, dayBars)

        calls = []
        index = []
        for jj in range(1, 6):
            for ii in range(390):
                index.append(calendar[jj]['open'] + timedelta(minutes=ii))
        calls.append(call(DataFrame({}, index), 'backtest/bars/min_AAPL.csv'))
        index = []
        for jj in range(0, 3):
            for ii in range(390):
                index.append(calendar[jj]['open'] + timedelta(minutes=ii))
        calls.append(call(DataFrame({}, index), 'backtest/bars/min_MSFT.csv'))
        print(to_csv.mock_calls[0])
        print(to_csv.call_args_list[0])
        assert 0 # TODO: assert_frame_equal with mock calls


def test_init_bar_gens(): pass

def get_next_bars(): pass
