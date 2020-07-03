# This function updates Algo.assets.keys() with symbols that are active and
# marginable on alpaca, available on polygon, and have normal margins (above
# price threshold and not leveraged). It also sets the shortable flags and
# populates Algo.assets with historical data.

from alpacaAPI import alpacaPaper as alpaca
from algoClasses import Algo
from algos import allAlgos, positionsList
from config import minSharePrice, minDayVolume
from marketHours import get_date, get_market_date
from warn import warn
import pandas as pd


def update_tradable_assets(debugging=False, numDebugAssets=100):

    print('Updating tradable assets')

    # get alpaca assets and polygon tickers
    alpacaAssets = alpaca.list_assets('active', 'us_equity')
    if debugging: alpacaAssets = alpacaAssets[:numDebugAssets]
    polygonTickers = alpaca.polygon.all_tickers()

    # get activeSymbols
    # NOTE: this takes a long time. Would it be faster with sort?
    activeSymbols = []
    for ii, asset in enumerate(alpacaAssets):
        print(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}')

        # get price (if on polygon)
        price = 0
        for ticker in polygonTickers:
            if (
                ticker.ticker == asset.symbol and
                ticker.prevDay['v'] > minDayVolume
            ):
                price = ticker.prevDay['l']
                break

        # check marginablility
        # TODO: check leverage
        if asset.marginable and price > minSharePrice:
            activeSymbols.append(asset.symbol)

    # check for inactive assets
    inactiveSymbols = []
    for symbol in Algo.assets:
        if symbol not in activeSymbols:
            inactiveSymbols.append(symbol)
    
    # remove inactive assets
    for ii, symbol in enumerate(inactiveSymbols):
        print(f'Removing asset {ii+1} / {len(inactiveSymbols)}\t{symbol}')
        remove_asset(symbol)

    # add tradable assets
    for ii, symbol in enumerate(activeSymbols):
        if symbol not in Algo.assets:
            print(f'Adding asset {ii+1} / {len(activeSymbols)}\t{symbol}')
            add_asset(symbol)

    # set shortable flag
    for asset in alpacaAssets:
        symbol = asset.symbol
        if symbol in Algo.assets:
            Algo.assets[symbol]['shortable'] = asset.easy_to_borrow
            if not asset.easy_to_borrow:
                for algo in allAlgos:
                    try:
                        if positions[symbol] < 0:
                            qty = positions[symbol]['qty']
                            warn(f'{algo.name} HTB position of {qty} in {symbol}')
                    except: pass

        
        # TODO: sector, industry, and metrics

    # set lastSymbolUpdate
    Algo.lastSymbolUpdate = get_date()


def remove_asset(symbol):
    # remove from assets
    Algo.assets.pop(symbol)

    # check for positions
    # TODO: check algos
    for positions in (Algo.livePositions, Algo.paperPositions):
        if symbol in positions:
            warn(f'You have {positions[symbol]} shares in {symbol} (inactive)')
            # TODO: how to handle? (inactive on alpaca, not marginable, below price threshold)

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
    Algo.assets[symbol] = {}

    # add zero positions
    for positions in positionsList:
        if symbol not in positions:
            positions[symbol] = {'qty': 0, 'basis': 0}

    # init secBars
    Algo.assets[symbol]['secBars'] = pd.DataFrame()

    # get minBars
    fromDate = get_market_date(-1)
    toDate = get_date()
    Algo.assets[symbol]['minBars'] = \
        alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate).df

    # get dayBars
    fromDate = get_market_date(-100)
    toDate = get_date()
    Algo.assets[symbol]['dayBars'] = \
        alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
