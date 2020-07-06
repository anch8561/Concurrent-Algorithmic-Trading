import g
from alpacaAPI import alpacaPaper as alpaca
from algos import allAlgos, positionsList
from config import minSharePrice, minDayVolume, leverageStrings
from timing import get_date, get_market_date
from warn import warn

import pandas as pd

def update_tradable_assets(debugging=False, numDebugAssets=100):

    print('Updating tradable assets')

    # get alpaca assets and polygon tickers
    alpacaAssets = alpaca.list_assets('active', 'us_equity')
    if debugging: alpacaAssets = alpacaAssets[:numDebugAssets]
    polygonTickers = alpaca.polygon.all_tickers()

    # get active symbols
    activeSymbols = []
    for ii, asset in enumerate(alpacaAssets):
        print(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}')
        if (
            asset.marginable and
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

    # set easyToBorrow flag
    for asset in alpacaAssets:
        symbol = asset.symbol
        if symbol in g.assets:
            g.assets[symbol]['easyToBorrow'] = asset.easy_to_borrow
            if not asset.easy_to_borrow:
                for algo in allAlgos:
                    qty = algo.positions[symbol]['qty']
                    if qty < 0: warn(f'{algo.name} {qty} HTB shares of {symbol}')
        
    # TODO: sector, industry, and metrics

    # set lastSymbolUpdate
    g.lastSymbolUpdate = get_date()


def remove_asset(symbol, alpacaAssets, polygonTickers):
    # remove from assets
    g.assets.pop(symbol)

    # get reasons for removal
    removalReasons = [
        'inactive',
        'unmarginable',
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


def add_asset(symbol):
    # add key
    g.assets[symbol] = {}

    # add zero positions
    for positions in positionsList:
        if symbol not in positions:
            positions[symbol] = {'qty': 0, 'basis': 0}

    # init secBars
    g.assets[symbol]['secBars'] = pd.DataFrame()

    # get minBars
    fromDate = get_market_date(-1)
    toDate = get_date()
    g.assets[symbol]['minBars'] = \
        alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate).df

    # get dayBars
    fromDate = get_market_date(-100)
    toDate = get_date()
    g.assets[symbol]['dayBars'] = \
        alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
