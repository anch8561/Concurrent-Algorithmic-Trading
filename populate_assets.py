import config as c
import globalVariables as g
from algos import allAlgos
from indicators import indicators
from timing import get_market_open, get_date, get_market_date

from logging import getLogger
from pandas import DataFrame

log = getLogger()

def populate_assets(numAssets):
    # numAssets: int or None; number of symbols to stream (None means all)
    log.warning('Populating assets')

    # get alpaca assets and polygon tickers
    alpacaAssets = g.alpacaPaper.list_assets('active', 'us_equity')
    polygonTickers = g.alpacaPaper.polygon.all_tickers()

    # get active symbols
    activeSymbols = []
    for ii, asset in enumerate(alpacaAssets):
        log.info(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}')
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
        
        # check numAssets
        if c.numAssets != None and len(activeSymbols) == c.numAssets: break

    # add active assets
    for ii, symbol in enumerate(activeSymbols):
        log.info(f'Adding asset {ii+1} / {len(activeSymbols)}\t{symbol}')
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
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
    for indicator in indicators['sec']: columns.append(indicator.name)
    data = {}
    for column in columns: data[column] = None
    g.assets['sec'][symbol] = DataFrame(data, [get_market_open()])

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
        bars = g.alpacaPaper.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
    except Exception as e:
        log.exception(e)
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
