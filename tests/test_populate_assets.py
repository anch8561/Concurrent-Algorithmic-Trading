import config as c
import globalVariables as g
import populate_assets
import indicators
from algoClasses import Algo

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
            volume = c.minDayVolume + 1,
            low = c.minSharePrice + 1
        ):
            self.ticker = ticker
            self.prevDay = {'v': volume, 'l': low}

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
                Asset('EBAY')]

        class polygon:
            def all_tickers(): # pylint: disable=no-method-argument
                return [
                    Ticker('FB', volume=0),
                    Ticker('GOOG', low=0.00),
                    Ticker('MSFT'),
                    Ticker('WMT'),
                    Ticker('EBAY')]
                
            def historic_agg_v2(*args): # pylint: disable=no-method-argument
                class data:
                    df = DataFrame(
                        {'open': [1, 2, 3],
                        'close': [3, 2, 1]},
                        ['a', 'b', 'c'],
                        dtype=object)
                return data
    
    return alpaca

def test_populate_assets(alpaca):
    g.alpacaPaper = alpaca

    # test
    with patch('populate_assets.add_asset') as add_asset:
        populate_assets.populate_assets(2)
        calls = [
            call('MSFT'),
            call('WMT')]
        add_asset.assert_has_calls(calls)
        assert add_asset.call_count == 2

def test_add_asset(alpaca):
    ## SETUP
    g.alpacaPaper = alpaca
    g.paperPositions['AAPL'] = {'qty': 3, 'basis': 0}
    allAlgos = [Algo(print, False)]
    class timing:
        get_market_open = Mock(return_value='a')
        get_market_date = Mock()
        get_date = Mock()

    with patch('indicators.Indicator.get', return_value=123):
        secIndicator = indicators.Indicator(1, 'sec', indicators.momentum)
        minIndicator = indicators.Indicator(1, 'min', indicators.momentum)
        dayIndicator = indicators.Indicator(1, 'day', indicators.momentum)

        # test# TODO: try unindenting
        with patch('populate_assets.allAlgos', allAlgos), \
            patch('populate_assets.indicators', {
                'sec': [secIndicator],
                'min': [minIndicator],
                'day': [dayIndicator]}), \
            patch('populate_assets.timing', timing) \
        :
            populate_assets.add_asset('AAPL')

    # positions
    assert g.paperPositions == {'AAPL': {'qty': 3, 'basis': 0}}
    assert g.livePositions == {'AAPL': {'qty': 0, 'basis': 0}}
    for algo in allAlgos:
        assert algo.positions == {'AAPL': {'qty': 0, 'basis': 0}}
    
    # sec asset
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked', '1_sec_momentum']
    data = dict.fromkeys(columns, None)
    expectedAsset = DataFrame(data, ['a'])
    assert g.assets['sec']['AAPL'].equals(expectedAsset)

    # min asset
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked', '1_min_momentum']
    data = dict.fromkeys(columns, None)
    expectedAsset = DataFrame(data, ['a'])
    assert g.assets['min']['AAPL'].equals(expectedAsset)

    # day asset
    bars = g.alpacaPaper.polygon.historic_agg_v2().df
    bars['1_day_momentum'] = 123
    assert_frame_equal(g.assets['day']['AAPL'], bars, False)
