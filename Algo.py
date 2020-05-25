# base class for algos

from alpacaAPI import alpaca, alpacaPaper
import warnings

class Algo:
    assets = {}

    def __init__(self, cash=10000, maxPosFrac=0.01, tags=[], category=None):
        # state variables
        self.alpaca = alpacaPaper # always call alpaca through this (changes with profitability)
        self.cash = cash
        self.equity = cash # + longs + shorts
        self.maintMargin = 0 # calculated at prev market close
        self.buyingPower = (self.equity - self.maintMargin) * 4
        self.overnightPower = self.buyingPower / 2
        self.maxPosFrac = maxPosFrac # maximum fraction of equity to hold in a position (at time of order)
        self.positions = {} # {symbol: quantity}
        self.orders = [] # [order_id]
        
        self.tags = tags # e.g. 'long', 'short', 'overnight', 'intraday', 'daily', 'weekly'
        self.category = category # e.g. 'longShort', 'meanReversion', 'momentum', 'scalping', etc

        # risk metrics


        # performance metrics
        self.profitable = False # whether using real money
        self.alpha = 0
        self.beta = 0
        self.allocFrac = 0

        self.before_market_open()
    
    def get_asset(symbol, field):
        # needs a blocker so it can't run in parallel
        # if field DNE:
        #     create field
        # if outdated:
        #     get data
        # return data
        pass


    def before_market_open(self):
        # update asset data
        alpaca_assets = alpaca.list_assets('active', 'us_equity')
        for asset in alpaca_assets:
            self.assets[asset.symbol] = {
                'marginable': asset.marginable,
                'easyToBorrow': asset.easy_to_borrow
            }
        # NOTE: this doesn't preserve price data
        # TODO: check for inactive assets

    def set_profitable(self, profitable):
        if self.profitable == profitable:
            warnings.warn(f'{self}.set_profitable({profitable}) did not change state')
            return
        
        # cancel orders
        # close positions
        # udpate account?

        # update flag and api
        self.profitable = profitable
        if profitable: self.alpaca = alpaca
        else: self.alpaca = alpacaPaper

    def get_initial_margin(self):
        pass # it's 50% of purchase price
        # does this have to be maintained until end of day?

    def get_maintenance_margin(self):
        margin = 0
        for symbol in self.positions:
            price = self.alpaca.polygon.last_quote(symbol)
            quantity = self.positions[symbol]

            # calculated at end of day
            # leveraged ETFs have higher margins (2x: 60%, 3x: 90%)
            if quantity > 0: # long
                if price < 2.50: margin += 1.0 * price * quantity
                else: margin += 0.3 * price * quantity
            elif quantity < 0: # short
                if price < 5.00: margin += max(2.50*quantity, price*quantity)
                else: margin += max(5.00*quantity, 0.3*price*quantity)
            else: warnings.warn(f'{self} has zero position in {symbol}')
        return margin
        
    def get_overnight_fee(self, debt):
        # accrues daily (including weekends) and posts at end of month
        return debt * 0.0375 / 360

    def get_short_fee(self, debt):
        # accrues daily (including weekends) and posts at end of month

        # ETB (easy to borrow)
        # fee charged for positions held at end of day
        # fee varies from 30 to 300 bps/yr depending on demand

        # HTB (hard to borrow)
        # fee charged for positions held at any point during day
        # fee is higher than maxFee

        # NOTE: is there any way to get actual fee values from alpaca api?
        minFee = debt * 30/1e-4 / 360
        maxFee = debt * 300/1e4 / 360
        return minFee, maxFee