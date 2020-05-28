# base class for algos

from alpacaAPI import alpaca, alpacaPaper
import warnings, statistics

class Algo:
    assets = {}
    paperOrders = [] # [{id, symbol, quantity, price, algo}]
    liveOrders = []
    paperPositions = {} # {symbol: quantity}
    livePositions = {}

    def __init__(self, buyingPower=10000, maxPosFrac=0.01, tags=[], category=None):
        # state variables
        self.alpaca = alpacaPaper # always call alpaca through this (changes with profitability)
        self.buyingPower = buyingPower
        self.positions = {} # {symbol: quantity}
        self.orders = [] # [{id, symbol, quantity, price}]
        #  order quantity is positive for buy and negative for sell
        #  order price is an estimate

        # properties
        self.maxPosFrac = maxPosFrac # maximum fraction of equity to hold in a position (at time of order)
        self.tags = tags # e.g. 'long', 'short', 'longShort', 'intraday', 'daily', 'weekly', 'overnight'
        self.category = category # e.g. 'meanReversion', 'momentum', 'scalping', etc

        # risk metrics


        # performance metrics
        self.history = [] # [{time, prevTime, equity, prevEquity, cashFlow, growthFrac}]
        # change in equity minus cash allocations over previous equity
        # extra fields are kept for error proofing
        self.mean = 0 # average daily growth
        self.stdev = 0 # sample standard deviation of daily growth

        self.live = False # whether using real money
        self.allocFrac = 0

        self.update_assets() # NOTE: this should happen once per day before market open

    def update_assets(self, algos):
        alpacaAssets = alpaca.list_assets('active', 'us_equity')

        # update asset data
        for asset in alpacaAssets:
            if asset.marginable:
                if asset not in self.assets:
                    print(f'"{asset}" is now active and marginable')
                self.assets[asset.symbol]['easyToBorrow'] = asset.easy_to_borrow
                # TODO: sector, industry, leverage, volume, historical data and metrics
        
        # remove inactive assets
        symbols = [asset.symbol for asset in alpacaAssets]
        inactive = []
        for asset in self.assets:
            if asset not in symbols:
                inactive.append(asset)
        for asset in inactive:
            print(f'"{asset}" is no longer active')

            # remove from assets
            self.assets.pop(asset)

            # check for positions
            if asset in self.livePositions:
                position = self.livePositions[asset]
                warnings.warn(f'You have {position} shares in {asset}')
                # TODO: how to handle this?
            # TODO: paper and algos

            # check for orders
            for ii, order in enumerate(self.liveOrders):
                if order['symbol'] == asset: self.liveOrders.pop(ii)
            for ii, order in enumerate(self.paperOrders):
                if order['symbol'] == asset: self.paperOrders.pop(ii)
            for algo in algos:
                for ii, order in enumerate(algo.orders):
                    if order['symbol'] == asset:
                        algo.alpaca.cancel_order(order['id'])
                        algo.orders.pop(ii)
        
        # TODO: remove unmarginable assets

    def update_metrics(self):
        # TODO: check each datapoint is one market day apart
        growth = [day['growthFrac'] for day in self.history]
        self.mean = statistics.mean(growth)
        self.stdev = statistics.stdev(growth)

    def set_live(self, live):

        # check argument
        if self.live == live:
            warnings.warn(f'{self}.set_live({live}) did not change state')
            return
        
        # TODO: cancel orders
        # TODO: close positions
        # TODO: udpate account?

        # update flag and api
        self.live = live
        if live: self.alpaca = alpaca
        else: self.alpaca = alpacaPaper
