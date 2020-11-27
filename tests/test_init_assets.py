import config as c
import globalVariables as g
import init_assets
from algoClass import Algo

from importlib import reload
from pandas import DataFrame
from pandas.testing import assert_frame_equal
from pytest import fixture
from unittest.mock import patch, Mock, call

@fixture
def alpaca():
    class Asset:
        def __init__(self, symbol,
            name = '',
            marginable = True,
            shortable = True
        ):
            self.symbol = symbol
            self.name = name
            self.marginable = marginable
            self.shortable = shortable

    class Ticker:
        def __init__(self, ticker,
            high = 22.00,
            low = 21.00,
            close = 21.50,
            volume = 1000
        ):
            self.ticker = ticker
            self.prevDay = {'v': volume, 'h': high, 'l': low, 'c': close}

    class alpaca:
        def list_assets(*args): # pylint: disable=no-method-argument
            return [
                Asset('AAPL'),
                Asset('AMZN', marginable=False),
                Asset('TSLA', shortable=False),
                Asset('DWT', 'VelocityShares 3x Inverse Crude Oil ETN ETF'),
                Asset('FB'),
                Asset('GOOG'),
                Asset('MSFT'),
                Asset('WMT'),
                Asset('EBAY'),
                Asset('SPY')]

        class polygon:
            def all_tickers(): # pylint: disable=no-method-argument
                return [
                    Ticker('FB', volume=10),
                    Ticker('GOOG', low=19.99),
                    Ticker('MSFT', high=21.01),
                    Ticker('WMT'),
                    Ticker('EBAY'),
                    Ticker('SPY')]
                
            def historic_agg_v2(*args): # pylint: disable=no-method-argument
                class data:
                    df = DataFrame(
                        {'open': [1, 2, 3],
                        'close': [3, 2, 1]},
                        ['a', 'b', 'c'],
                        dtype=object)
                return data
    
    return alpaca

def test_init_assets(alpaca, allAlgos, indicators):
    g.alpaca = alpaca

    # test
    with patch('init_assets.c.minSharePrice', 20), \
        patch('init_assets.c.minDayCashFlow', 2e4), \
        patch('init_assets.c.minDaySpread', 0.01), \
        patch('init_assets.add_asset') as add_asset:
        init_assets.init_assets(2, allAlgos, indicators)
        calls = [
            call('WMT', allAlgos, indicators),
            call('EBAY', allAlgos, indicators)]
        add_asset.assert_has_calls(calls)
        assert add_asset.call_count == 2

def test_add_asset(alpaca, allAlgos, indicators):
    ## SETUP
    g.alpaca = alpaca
    class timing:
        get_market_open = Mock(return_value='a')
        get_market_date = Mock()
        get_date = Mock()

    ## TEST
    with patch('init_assets.timing', timing), \
    patch('indicators.Indicator.get', return_value=123):
        init_assets.add_asset('AAPL', allAlgos, indicators)

    # positions
    assert g.positions == {'AAPL': 0}
    for algo in allAlgos:
        assert algo.positions == {'AAPL': {'qty': 0, 'basis': 0}}
    
    # sec asset
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked', '2_sec_mom']
    data = dict.fromkeys(columns)
    data['ticked'] = True
    expectedAsset = DataFrame(data, ['a'])
    assert g.assets['sec']['AAPL'].equals(expectedAsset)

    # min asset
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked', '2_min_mom']
    data = dict.fromkeys(columns)
    data['ticked'] = True
    expectedAsset = DataFrame(data, ['a'])
    assert g.assets['min']['AAPL'].equals(expectedAsset)

    # day asset
    bars = g.alpaca.polygon.historic_agg_v2().df
    bars['ticked'] = True
    bars['2_day_mom'] = 123
    assert_frame_equal(g.assets['day']['AAPL'], bars, False)
