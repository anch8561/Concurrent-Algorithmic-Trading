import backtest.historicBars as histBars

from datetime import datetime
from pandas import DataFrame
from unittest.mock import call, Mock, patch

def test_get_historic_min_bars():
    class Bar:
        def __init__(self, data: dict, index: list):
            self.df = DataFrame(data, index)
    
    class Polygon:
        def __init__(self):
            self.ii = -1
            self.bars = [] # TODO: sets of 5000+ bars
        def historic_agg_v2(self, *args):
            self.ii += 1
            return self.bars[self.ii]

    class alpaca:
        polygon = Polygon()

    calendar = [
        {'open': datetime(2020, 10, 19, 9, 30),
        'close': datetime(2020, 10, 19, 16, 0)},
        {'open': datetime(2020, 10, 20, 9, 31),
        'close': datetime(2020, 10, 20, 16, 1)},
        {'open': datetime(2020, 10, 21, 9, 32),
        'close': datetime(2020, 10, 21, 16, 2)},
        {'open': datetime(2020, 10, 26, 9, 33),
        'close': datetime(2020, 10, 26, 16, 3)},
        {'open': datetime(2020, 10, 27, 9, 34),
        'close': datetime(2020, 10, 27, 16, 4)},
        {'open': datetime(2020, 10, 28, 9, 35),
        'close': datetime(2020, 10, 28, 16, 5)}]

    dayBars = {
        'AAPL': DataFrame({}, [
            datetime(2020, 10, 26),
            datetime(2020, 10, 27),
            datetime(2020, 10, 28)]),
        'MSFT': DataFrame({}, [
            datetime(2020, 10, 19),
            datetime(2020, 10, 20),
            datetime(2020, 10, 21)])}

    class timing:
        get_calendar_index = Mock(side_effect=[4, 0])
        def get_market_open(self, calendar, idx):
            return calendar[idx]['open']
        def get_market_close(self, calendar, idx):
            return calendar[idx]['close']

    with patch('histBars.timing', timing), \
    patch('histBars.DataFrame.to_csv'):
        histBars.get_historic_min_bars(alpaca, calendar, dayBars)
    timing.get_calendar_index.assert_has_calls([
        call(calendar, '2020-10-26'),
        call(calendar, '2020-10-19')])

def test_init_bar_gens(): pass

def get_next_bars(): pass
