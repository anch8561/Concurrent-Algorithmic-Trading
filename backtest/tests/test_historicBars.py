import backtest.historicBars as histBars

from datetime import datetime, timedelta
from pandas import DataFrame
from pandas.testing import assert_index_equal
from unittest.mock import call, Mock, patch

def test_get_historic_min_bars():
    ## SETUP
    class timing:
        # pylint: disable=no-self-argument
        # pylint: disable=unsubscriptable-object
        def get_calendar_index(calendar, str):
            for ii, date in enumerate(calendar):
                if date['open'].strftime('%Y-%m-%d') == str:
                    return ii
        def get_market_open(calendar, idx):
            return calendar[idx]['open']
        def get_market_close(calendar, idx):
            return calendar[idx]['close']
    
    calendar = [
        {'open': datetime(2020, 10, 1, 9, 31),
        'close': datetime(2020, 10, 1, 16, 1)},
        {'open': datetime(2020, 10, 2, 9, 32),
        'close': datetime(2020, 10, 2, 16, 2)}]
    for jj in range(5, 26, 7):
        for ii in range(jj, jj+5):
            calendar.append(
                {'open': datetime(2020, 10, ii, 9, 30+ii),
                'close': datetime(2020, 10, ii, 16, ii)})

    class Barset:
        def __init__(self, data: dict, index: list):
            self.df = DataFrame(data, index)

    class alpaca:
        class polygon:
            def historic_agg_v2(self, symbol, multiplier, _from, to):
                fromDateIdx = timing.get_calendar_index(
                    calendar, _from.strftime('%Y-%m-%d'))
                index = []
                for day in calendar[fromDateIdx:fromDateIdx+10]:
                    for ii in range(500):
                        index.append(datetime(
                            day['open'].year,
                            day['open'].month,
                            day['open'].day,
                            9) + timedelta(minutes=ii))
                if index[-1] < to:
                    for ii in range(500):
                        index.append(datetime(
                            to.year,
                            to.month,
                            to.day,
                            9) + timedelta(minutes=ii))
                return Barset({}, index)

    dayBars = {
        'AAPL': DataFrame({}, [
            datetime(2020, 10, 5),
            datetime(2020, 10, 6),
            datetime(2020, 10, 7),
            datetime(2020, 10, 8),
            datetime(2020, 10, 9),
            datetime(2020, 10, 12),
            datetime(2020, 10, 13),
            datetime(2020, 10, 14),
            datetime(2020, 10, 15),
            datetime(2020, 10, 16),
            datetime(2020, 10, 19)]),
        'MSFT': DataFrame({}, [
            datetime(2020, 10, 1),
            datetime(2020, 10, 2),
            datetime(2020, 10, 5),
            datetime(2020, 10, 6),
            datetime(2020, 10, 7),
            datetime(2020, 10, 8),
            datetime(2020, 10, 9),
            datetime(2020, 10, 12),
            datetime(2020, 10, 13),
            datetime(2020, 10, 14),
            datetime(2020, 10, 15),
            datetime(2020, 10, 16)])}
    
    def to_csv(self, path):
        to_csv.dfs.append(self)
        to_csv.paths.append(path)
    to_csv.dfs = []
    to_csv.paths = []


    ## TEST
    with patch('backtest.historicBars.timing', timing), \
    patch('backtest.historicBars.DataFrame.to_csv', to_csv):
        histBars.get_historic_min_bars(alpaca, calendar, dayBars)
    assert len(to_csv.dfs) == 2

    # expected AAPL index
    index = []
    for date in dayBars['AAPL'].index:
        dateIdx = timing.get_calendar_index(calendar, date.strftime('%Y-%m-%d'))
        for ii in range(390):
            index.append(calendar[dateIdx]['open'] + timedelta(minutes=ii))
    assert all(to_csv.dfs[0].index == index)

    # expected MSFT index
    index = []
    for date in dayBars['MSFT'].index:
        dateIdx = timing.get_calendar_index(calendar, date.strftime('%Y-%m-%d'))
        for ii in range(390):
            index.append(calendar[dateIdx]['open'] + timedelta(minutes=ii))
    assert all(to_csv.dfs[1].index == index)

def test_init_bar_gens(): pass

def get_next_bars(): pass
