# This function updates Algo.assets.keys() with symbols that are active and
# marginable on alpaca, available on polygon, and have normal margins (above
# price threshold and not leveraged). It also sets the shortable flags and
# populates Algo.assets with historical data.

from alpacaAPI import alpaca
from Algo import Algo
from marketHours import get_date, get_n_market_days_ago
from warn import warn


def get_tradable_assets(algos, debugging=False):
    # algos: list of algos

    print('Updating tradable assets')

    # check for first run
    logging = False if Algo.assets == {} else True

    # get activeSymbols
    alpacaAssets = alpaca.list_assets('active', 'us_equity')
    if debugging: alpacaAssets = alpacaAssets[:100]
    polygonTickers = alpaca.polygon.all_tickers()
    activeSymbols = []
    # NOTE: this takes a long time. Would it be faster with sort?
    for ii, asset in enumerate(alpacaAssets):
        print(f'Checking asset {ii} / {len(alpacaAssets)}')

        # get price (if on polygon)
        price = 0
        for ticker in polygonTickers:
            if ticker.ticker == asset.symbol:
                price = ticker.prevDay['l']
                break

        # check marginablility
        # TODO: check leverage
        if asset.marginable and price > 3:
            activeSymbols.append(asset.symbol)

    # check for inactive assets
    inactive = []
    for symbol in Algo.assets:
        if symbol not in activeSymbols:
            inactive.append(symbol)
    
    # remove inactive assets
    for symbol in inactive:
        if logging: print(f'"{symbol}" is no longer active')

        # remove from assets
        Algo.assets.pop(symbol)

        # check for positions
        # TODO: check algos
        for positions in (Algo.livePositions, Algo.paperPositions):
            if symbol in positions:
                position = positions[symbol]
                warn(f'You have {position} shares in {symbol} (inactive)')
                # TODO: how to handle? (inactive on alpaca, not marginable, below price threshold)

        # check for orders
        for algo in algos:
            for ii, order in enumerate(algo.orders):
                if order['symbol'] == symbol:
                    algo.alpaca.cancel_order(order['id'])
                    algo.orders.pop(ii)
        for orders in (Algo.livePositions, Algo.paperOrders):
            for ii, order in enumerate(orders):
                if order['symbol'] == symbol:
                    orders.pop(ii)

    # add tradable assets
    for asset in alpacaAssets:
        # get symbol and price (if on polygon)
        symbol = asset.symbol
        price = 0
        for ticker in polygonTickers:
            if ticker.ticker == symbol:
                price = ticker.prevDay['l']
                break

        # check marginablility
        # TODO: check leverage
        if asset.marginable and price > 3:
            # check for new asset
            if symbol not in Algo.assets:
                add_asset(symbol)
                if logging: print(f'"{symbol}" is now active')

            # set shortable flag
            Algo.assets[symbol]['shortable'] = asset.easy_to_borrow
            # TODO: warn about HTB positions
            

            # TODO: sector, industry, and metrics

    # set lastSymbolUpdate
    Algo.lastSymbolUpdate = get_date()


def remove_asset(symbol):
    pass

def add_asset(symbol):
    # add key
    Algo.assets[symbol] = {}

    # TODO: try to load data (esp for secBars)

    # get minBars
    fromDate = get_n_market_days_ago(1)
    toDate = get_date()
    Algo.assets[symbol]['minBars'] = \
        alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate).df

    # get dayBars
    fromDate = get_n_market_days_ago(100)
    toDate = get_date()
    Algo.assets[symbol]['dayBars'] = \
        alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df