# update list of tradable assets on alpaca

from alpacaAPI import alpaca
from Algo import Algo
from warn import warn


def update_assets(algos):
    # algos: list of algos

        # check for first run
        if Algo.assets == {}: isFirstRun = True
        else: isFirstRun = False

        # update asset data
        alpacaAssets = alpaca.list_assets('active', 'us_equity')
        polygonTickers = alpaca.polygon.all_tickers()
        tickerSymbols = [ticker.ticker for ticker in polygonTickers]
        for asset in alpacaAssets:
            if (
                asset.marginable and
                asset.symbol in tickerSymbols and
                asset.symbol not in Algo.assets
                # TODO: check share price
            ):
                Algo.assets[asset.symbol] = {}
                if not isFirstRun: print(f'"{asset.symbol}" is now active and marginable')
                Algo.assets[asset.symbol]['shortable'] = asset.easy_to_borrow
                # TODO: sector, industry, leverage, volume, historical data and metrics
        
        # remove inactive assets
        symbols = [asset.symbol for asset in alpacaAssets]
        inactive = []
        for symbol in Algo.assets.keys():
            if symbol not in symbols:
                inactive.append(symbol)
        for symbol in inactive:
            print(f'"{symbol}" is no longer active')

            # remove from assets
            Algo.assets.pop(symbol)

            # check for positions
            if symbol in Algo.livePositions:
                position = Algo.livePositions[symbol]
                warn(f'You have {position} shares in {symbol}')
                # TODO: how to handle this?
            # TODO: paper and algos

            # check for orders
            for ii, order in enumerate(Algo.liveOrders):
                if order['symbol'] == symbol: Algo.liveOrders.pop(ii)
            for ii, order in enumerate(Algo.paperOrders):
                if order['symbol'] == symbol: Algo.paperOrders.pop(ii)
            for algo in algos:
                for ii, order in enumerate(algo.orders):
                    if order['symbol'] == symbol:
                        algo.alpaca.cancel_order(order['id'])
                        algo.orders.pop(ii)
        
        # TODO: remove unmarginable assets