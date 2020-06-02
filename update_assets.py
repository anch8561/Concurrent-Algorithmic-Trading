# update list of tradable assets on alpaca

from alpacaAPI import alpaca
from Algo import Algo
from warn import warn


def update_assets(algos):
    # algos: list of algos

        # check for first run
        if Algo.assets == {}: isFirstRun = True
        else: isFirstRun = False

        # TODO: cross reference with polygon tickers

        # update asset data
        alpacaAssets = alpaca.list_assets('active', 'us_equity')
        for asset in alpacaAssets:
            if asset.marginable:
                if asset.symbol not in Algo.assets:
                    Algo.assets[asset.symbol] = {}
                    if not isFirstRun: print(f'"{asset.symbol}" is now active and marginable')
                Algo.assets[asset.symbol]['easyToBorrow'] = asset.easy_to_borrow
                # TODO: sector, industry, leverage, volume, historical data and metrics
        
        # remove inactive assets
        symbols = [asset.symbol for asset in alpacaAssets]
        inactive = []
        for asset in Algo.assets:
            if asset not in symbols:
                inactive.append(asset)
        for asset in inactive:
            print(f'"{asset}" is no longer active')

            # remove from assets
            Algo.assets.pop(asset)

            # check for positions
            if asset in Algo.livePositions:
                position = Algo.livePositions[asset]
                warn(f'You have {position} shares in {asset}')
                # TODO: how to handle this?
            # TODO: paper and algos

            # check for orders
            for ii, order in enumerate(Algo.liveOrders):
                if order['symbol'] == asset: Algo.liveOrders.pop(ii)
            for ii, order in enumerate(Algo.paperOrders):
                if order['symbol'] == asset: Algo.paperOrders.pop(ii)
            for algo in algos:
                for ii, order in enumerate(algo.orders):
                    if order['symbol'] == asset:
                        algo.alpaca.cancel_order(order['id'])
                        algo.orders.pop(ii)
        
        # TODO: remove unmarginable assets