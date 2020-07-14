import g
from alpacaAPI import alpacaPaper as alpaca
from algos import allAlgos
from config import minSharePrice, minDayVolume, leverageStrings
from indicators import indicators
from timing import get_date, get_market_date
from warn import warn

import pandas as pd

def update_tradable_assets(numAssets=None):

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

    # get inactive symbols
    inactiveSymbols = []
    for symbol in g.assets:
        if symbol not in activeSymbols:
            inactiveSymbols.append(symbol)
    
    # remove inactive assets
    for ii, symbol in enumerate(inactiveSymbols):
        print(f'Removing asset {ii+1} / {len(inactiveSymbols)}\t{symbol}')
        remove_asset(symbol, alpacaAssets, polygonTickers)

    # add active assets
    for ii, symbol in enumerate(activeSymbols):
        if symbol not in g.assets:
            print(f'Adding asset {ii+1} / {len(activeSymbols)}\t{symbol}')
            add_asset(symbol)


def remove_asset(symbol, alpacaAssets, polygonTickers):
    # remove from assets
    g.assets.pop(symbol)

    # get reasons for removal
    removalReasons = [
        'inactive',
        'unmarginable',
        'unshortable',
        'leveraged',
        'noTicker',
        'lowVolume',
        'lowPrice'
    ]
    for asset in alpacaAssets:
        if asset.symbol == symbol:
            removalReasons.remove('inactive')
            if asset.marginable:
                removalReasons.remove('unmarginable')
            if asset.shortable:
                removalReasons.remove('unshortable')
            if not any(x in asset.name.lower() for x in leverageStrings):
                removalReasons.remove('leveraged')
            for ticker in polygonTickers:
                if ticker.ticker == asset.symbol:
                    removalReasons.remove('noTicker')
                    if ticker.prevDay['v'] > minDayVolume:
                        removalReasons.remove('lowVolume')
                    if ticker.prevDay['l'] > minSharePrice:
                        removalReasons.remove('lowPrice')
                    break
    removalReasons = ', '.join(removalReasons)

    # check for positions
    for algo in allAlgos:
        qty = algo.positions[symbol]['qty']
        if qty: warn(f'{algo.name} {qty} shares of {symbol} ({removalReasons})')

    # check for orders
    for algo in allAlgos:
        orderIDs = []
        for order in algo.orders:
            if order['symbol'] == symbol:
                orderIDs.append(order['id'])
        for orderID in orderIDs:
            algo.alpaca.cancel_order(orderID)
            algo.allOrders.pop(orderID)
            algo.orders.pop(orderID)


# list of lists of positions
positionsList = [g.paperPositions, g.livePositions]
positionsList += [algo.positions for algo in allAlgos]

def add_asset(symbol):
    # add key
    g.assets[symbol] = {}

    # add zero positions
    for positions in positionsList:
        if symbol not in positions:
            positions[symbol] = {'qty': 0, 'basis': 0}

    # init secBars
    g.assets[symbol]['secBars'] = pd.DataFrame()


    # GET MINUTE BARS
    # get historic aggs
    print('    Getting historic min bars')
    fromDate = get_market_date(-1)
    toDate = get_date()
    bars = alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate).df.iloc[-100:]
    bars['ticked'] = False

    # get indicators
    for kk, indicator in enumerate(indicators['min']):
        print(f'\tAdding min indicator {kk+1} / {len(indicators["min"])}\t{indicator.name}')
        bars[indicator.name] = None
        jj = bars.columns.get_loc(indicator.name)
        for ii in range(len(bars.index)):
            bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii])
    
    # write to assets
    g.assets[symbol]['minBars'] = bars


    # GET DAY BARS
    # get historic aggs
    print('    Getting historic day bars')
    fromDate = get_market_date(-100)
    toDate = get_date()
    bars = alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df

    # get indicators
    for kk, indicator in enumerate(indicators['day']):
        print(f'\tAdding day indicator {kk+1} / {len(indicators["day"])}\t{indicator.name}')
        bars[indicator.name] = None
        jj = bars.columns.get_loc(indicator.name)
        for ii in range(len(bars.index)):
            bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii])
    
    # write to assets
    g.assets[symbol]['dayBars'] = bars
