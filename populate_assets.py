import config as c
import globalVariables as g
from algos import allAlgos
from alpacaAPI import alpacaPaper as alpaca
from indicators import indicators
from timing import get_market_open, get_date, get_market_date
from warn import warn

from pandas import DataFrame

def populate_assets(numAssets=None):
    # numAssets: int or None; number of symbols to check (None means no limit)

    print('Populating assets')

    # get alpaca assets and polygon tickers
    alpacaAssets = alpaca.list_assets('active', 'us_equity')
    if numAssets: alpacaAssets = alpacaAssets[:numAssets]
    polygonTickers = alpaca.polygon.all_tickers()

    # get active symbols
    activeSymbols = []
    for ii, asset in enumerate(alpacaAssets):
        print(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}')
        if (
            asset.marginable and
            asset.shortable and
            not any(x in asset.name.lower() for x in c.leverageStrings)
        ):
            for ticker in polygonTickers:
                if (
                    ticker.ticker == asset.symbol and
                    ticker.prevDay['v'] > c.minDayVolume and
                    ticker.prevDay['l'] > c.minSharePrice
                ):
                    activeSymbols.append(asset.symbol)
                    break

    # add active assets
    for ii, symbol in enumerate(activeSymbols):
        print(f'Adding asset {ii+1} / {len(activeSymbols)}\t{symbol}')
        add_asset(symbol)


# list of lists of positions
positionsList = [g.paperPositions, g.livePositions]
positionsList += [algo.positions for algo in allAlgos]


def add_asset(symbol):
    # add zero positions
    for positions in positionsList:
        if symbol not in positions:
            positions[symbol] = {'qty': 0, 'basis': 0}

    # init second bars
    g.assets['sec'][symbol] = DataFrame()

    # init minute bars
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
    for indicator in indicators['min']: columns.append(indicator.name)
    data = {}
    for column in columns: data[column] = None
    g.assets['min'][symbol] = DataFrame(data, [get_market_open()])


    # GET DAY BARS
    try: # get historic aggs
        fromDate = get_market_date(-c.numHistoricDays)
        toDate = get_date()
        bars = alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
    except Exception as e:
        warn(e)
        g.assets['sec'].pop(symbol)
        g.assets['min'].pop(symbol)
        return

    # get indicators
    for indicator in indicators['day']:
        bars[indicator.name] = None
        jj = bars.columns.get_loc(indicator.name)
        for ii in range(len(bars.index)):
            bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii])
    
    # write to assets
    g.assets['day'][symbol] = bars
