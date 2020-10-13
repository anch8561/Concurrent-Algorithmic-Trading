import config as c
import globalVariables as g
import timing

from logging import getLogger
from pandas import DataFrame

log = getLogger('main')

def init_assets(numAssets, allAlgos, indicators):
    # numAssets: int; number of symbols to stream (-1 means all)
    log.warning('Populating assets')

    # get alpaca assets and polygon tickers
    alpacaAssets = g.alpaca.list_assets('active', 'us_equity')
    polygonTickers = g.alpaca.polygon.all_tickers()

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
        if numAssets > 0 and len(activeSymbols) == numAssets: break

    # add active assets
    for ii, symbol in enumerate(activeSymbols):
        log.info(f'Adding asset {ii+1} / {len(activeSymbols)}\t{symbol}')
        add_asset(symbol, allAlgos, indicators)


def add_asset(symbol, allAlgos, indicators):
    # add zero positions
    g.positions[symbol] = 0
    for algo in allAlgos:
        if symbol not in algo.positions:
            algo.positions[symbol] = {'qty': 0, 'basis': 0}

    # init second bars
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
    for indicator in indicators['sec']: columns.append(indicator.name)
    data = dict.fromkeys(columns)
    g.assets['sec'][symbol] = DataFrame(data, [timing.get_market_open()])

    # init minute bars
    columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
    for indicator in indicators['min']: columns.append(indicator.name)
    data = dict.fromkeys(columns)
    g.assets['min'][symbol] = DataFrame(data, [timing.get_market_open()])


    ## GET DAY BARS
    try: # get historic aggs
        fromDate = timing.get_market_date(-c.numHistoricDays)
        toDate = timing.get_date()
        bars = g.alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
    except Exception as e:
        log.exception(e)
        g.assets['sec'].pop(symbol)
        g.assets['min'].pop(symbol)
        return

    # get indicators
    bars['ticked'] = False
    for indicator in indicators['day']:
        bars[indicator.name] = None
        jj = bars.columns.get_loc(indicator.name)
        for ii in range(len(bars.index)):
            bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii+1])
    
    # write to assets
    g.assets['day'][symbol] = bars
