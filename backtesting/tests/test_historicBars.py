import backtesting.historicBars as histBars

import os, shutil
from datetime import datetime, timedelta
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from tests.conftest import indicators
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
    with patch('backtesting.historicBars.timing', timing), \
    patch('backtesting.historicBars.DataFrame.to_csv', to_csv):
        histBars.get_historic_min_bars(alpaca, calendar, dayBars)
    assert len(to_csv.dfs) == 2

    # expected AAPL index
    index = []
    for date in dayBars['AAPL'].index:
        dateIdx = timing.get_calendar_index(calendar, date.strftime('%Y-%m-%d'))
        for ii in range(390):
            index.append(calendar[dateIdx]['open'] + timedelta(minutes=ii))
    assert all(to_csv.dfs[0].index == index)
    assert to_csv.paths[0] == 'backtesting/bars/min_AAPL.csv'

    # expected MSFT index
    index = []
    for date in dayBars['MSFT'].index:
        dateIdx = timing.get_calendar_index(calendar, date.strftime('%Y-%m-%d'))
        for ii in range(390):
            index.append(calendar[dateIdx]['open'] + timedelta(minutes=ii))
    assert all(to_csv.dfs[1].index == index)
    assert to_csv.paths[1] == 'backtesting/bars/min_MSFT.csv'

def test_init_bar_gens():
    ## SETUP
    # args
    barFreqs = ['sec', 'day']
    symbols = ['AAPL', 'MSFT']
    
    # dir
    try: os.mkdir('backtesting/tests/bars')
    except: pass

    # day
    index = [datetime(2001,2,3), datetime(2001,2,4)]
    dayAAPL = DataFrame({'col1': [1,2], 'col2': [3,4]}, index)
    dayAAPL.to_csv('backtesting/tests/bars/day_AAPL.csv')
    dayMSFT = DataFrame({'col1': [2,3], 'col2': [4,5]}, index)
    dayMSFT.to_csv('backtesting/tests/bars/day_MSFT.csv')

    # sec
    index = [datetime(2001,2,3,4,5,6), datetime(2001,2,3,4,5,7)]
    secAAPL = DataFrame({'col1': [3,4], 'col2': [5,6]}, index)
    secAAPL.to_csv('backtesting/tests/bars/sec_AAPL.csv')
    secMSFT = DataFrame({'col1': [4,5], 'col2': [6,7]}, index)
    secMSFT.to_csv('backtesting/tests/bars/sec_MSFT.csv')


    ## TEST
    with patch('backtesting.historicBars.c.barPath', 'backtesting/tests/bars/'):
        barGens = histBars.init_bar_gens(barFreqs, symbols)

    assert barGens['day']['AAPL']['buffer'] == None
    test = next(barGens['day']['AAPL']['generator'])
    assert_frame_equal(test, dayAAPL.iloc[:1])

    assert barGens['day']['MSFT']['buffer'] == None
    test = next(barGens['day']['MSFT']['generator'])
    assert_frame_equal(test, dayMSFT.iloc[:1])

    assert barGens['sec']['AAPL']['buffer'] == None
    test = next(barGens['sec']['AAPL']['generator'])
    assert_frame_equal(test, secAAPL.iloc[:1])

    assert barGens['sec']['MSFT']['buffer'] == None
    test = next(barGens['sec']['MSFT']['generator'])
    assert_frame_equal(test, secMSFT.iloc[:1])


    ## CLEANUP
    del barGens
    shutil.rmtree('backtesting/tests/bars')

def test_get_next_bars(indicators):
    ## SETUP
    # expected timestamp
    timestamp = datetime(2001, 2, 3, 4, 5, 6)

    # bar generators
    def barGen(ii):
        while True:
            yield DataFrame({'vwap': ii}, [datetime(2001, 2, 3, 4, 5, ii)])
            ii += 1
    
    bar = DataFrame({'vwap': 4}, [datetime(2001, 2, 3, 4, 5, 0)])

    barGens = {
        'sec': {
            'AAPL': {'buffer': None, 'generator': barGen(3)}, # behind
            'MSFT': {'buffer': None, 'generator': barGen(6)}, # typical
            'TSLA': {'buffer': None, 'generator': barGen(9)}, # ahead
            'GOOG': {'buffer': bar.copy(), 'generator': barGen(0)}, # buffer behind
            'ZOOM': {'buffer': bar.copy(), 'generator': barGen(0)}, # buffer typical
            'POOP': {'buffer': bar.copy(), 'generator': barGen(0)}}, # buffer ahead
        'min': {
            'AAPL': {'buffer': None, 'generator': barGen(0)}}}
    
    barGens['sec']['GOOG']['buffer'].index = [datetime(2001, 2, 3, 4, 5, 3)]
    barGens['sec']['ZOOM']['buffer'].index = [datetime(2001, 2, 3, 4, 5, 6)]
    barGens['sec']['POOP']['buffer'].index = [datetime(2001, 2, 3, 4, 5, 9)]

    # assets
    asset = DataFrame(
        {'vwap': 5, 'ticked': False, '2_sec_momentum': None},
        [datetime(2001, 2, 3, 4, 5, 0)])

    assets = {
        'sec': {
            'AAPL': asset.copy(), 'MSFT': asset.copy(), 'TSLA': asset.copy(),
            'GOOG': asset.copy(), 'ZOOM': asset.copy(), 'POOP': asset.copy()},
        'min': {'AAPL': asset.copy()}}
    
    # expected assets
    generatorAsset = asset.append(DataFrame(
        {'vwap': 6, 'ticked': False, '2_sec_momentum': 6/5-1},
        [datetime(2001, 2, 3, 4, 5, 6)]))
    
    bufferAsset = asset.append(DataFrame(
        {'vwap': 4, 'ticked': False, '2_sec_momentum': 4/5-1},
        [datetime(2001, 2, 3, 4, 5, 6)]))
    

    ## TEST
    histBars.get_next_bars('sec', timestamp, barGens, indicators, assets)

    # behind
    assert_frame_equal(assets['sec']['AAPL'], generatorAsset, False)
    assert next(barGens['sec']['AAPL']['generator']).vwap[0] == 7
    assert barGens['sec']['AAPL']['buffer'] == None

    # typical
    assert_frame_equal(assets['sec']['MSFT'], generatorAsset, False)
    assert next(barGens['sec']['MSFT']['generator']).vwap[0] == 7
    assert barGens['sec']['MSFT']['buffer'] == None

    # ahead
    assert_frame_equal(assets['sec']['TSLA'], asset, False)
    assert next(barGens['sec']['TSLA']['generator']).vwap[0] == 10
    assert_frame_equal(
        barGens['sec']['TSLA']['buffer'],
        DataFrame({'vwap': 9}, [datetime(2001, 2, 3, 4, 5, 9)]))

    # buffer behind
    assert_frame_equal(assets['sec']['GOOG'], generatorAsset, False)
    assert next(barGens['sec']['GOOG']['generator']).vwap[0] == 7
    assert barGens['sec']['GOOG']['buffer'] == None

    # buffer typical
    assert_frame_equal(assets['sec']['ZOOM'], bufferAsset, False)
    assert next(barGens['sec']['ZOOM']['generator']).vwap[0] == 0
    assert barGens['sec']['ZOOM']['buffer'] == None

    # buffer ahead
    assert_frame_equal(assets['sec']['POOP'], asset, False)
    assert next(barGens['sec']['POOP']['generator']).vwap[0] == 0
    assert_frame_equal(
        barGens['sec']['POOP']['buffer'],
        DataFrame({'vwap': 4}, [datetime(2001, 2, 3, 4, 5, 9)]))

    # other barFreq
    assert_frame_equal(assets['min']['AAPL'], asset, False)
    assert next(barGens['min']['AAPL']['generator']).vwap[0] == 0
    assert barGens['min']['AAPL']['buffer'] == None
