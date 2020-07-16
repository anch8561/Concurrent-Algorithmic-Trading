import g
from algos import allAlgos
from alpacaAPI import alpacaPaper as alpaca
from config import verbose, minSharePrice, minDayVolume, leverageStrings
from indicators import indicators
from timing import get_date, get_market_date
from warn import warn

import pandas as pd

def populate_assets(numAssets=None):
    # numAssets: int or None; number of symbols to check (None means no limit)

    print('Updating tradable assets')

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
            not any(x in asset.name.lower() for x in leverageStrings)
        ):
            for ticker in polygonTickers:
                if (
                    ticker.ticker == asset.symbol and
                    ticker.prevDay['v'] > minDayVolume and
                    ticker.prevDay['l'] > minSharePrice
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

    # init secBars
    g.assets['sec'][symbol] = pd.DataFrame()


    # GET MINUTE BARS
    try: # get historic aggs
        if verbose: print('    Getting historic min bars')
        fromDate = get_market_date(-1)
        toDate = get_date()
        bars = alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate).df.iloc[-100:]
        bars['ticked'] = False
    except Exception as e:
        warn(e)
        g.assets['sec'].pop(symbol)
        return

    # get indicators
    for kk, indicator in enumerate(indicators['min']):
        if verbose: print(f'\tAdding min indicator {kk+1} / {len(indicators["min"])}\t{indicator.name}')
        bars[indicator.name] = None
        jj = bars.columns.get_loc(indicator.name)
        for ii in range(len(bars.index)):
            bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii])
    
    # write to assets
    g.assets['min'][symbol] = bars


    # GET DAY BARS
    try: # get historic aggs
        if verbose: print('    Getting historic day bars')
        fromDate = get_market_date(-100)
        toDate = get_date()
        bars = alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
    except Exception as e:
        warn(e)
        g.assets['sec'].pop(symbol)
        g.assets['min'].pop(symbol)
        return

    # get indicators
    for kk, indicator in enumerate(indicators['day']):
        if verbose: print(f'\tAdding day indicator {kk+1} / {len(indicators["day"])}\t{indicator.name}')
        bars[indicator.name] = None
        jj = bars.columns.get_loc(indicator.name)
        for ii in range(len(bars.index)):
            bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii])
    
    # write to assets
    g.assets['day'][symbol] = bars
