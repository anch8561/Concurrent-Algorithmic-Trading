# base class for algos

from alpacaAPI import alpaca, alpacaPaper
from warn import warn
import statistics

class Algo:
    assets = {} # {symbol: {easyToBorrow, ask, bid, minBars, secBars}}
    # 'easyToBorrow': bool; whether shortable on alpaca; updated daily
    # 'ask': float; latest ask price; updated each second
    # 'bid': float; latest bid price; updated each second
    # 'minBars': list; historical minute bars as received from polygon; updated each minute
    # 'secBars': list; historical second bars as received from polygon; updated each second

    paperOrders = {} # {id: {symbol, quantity, price, algo}}
    liveOrders = {}
    
    paperPositions = {} # {symbol: quantity}
    livePositions = {}

    def __init__(self, cash=10000, maxPosFrac=0.01, tags=[], category=None):
        # paper / live
        self.alpaca = alpacaPaper # always call alpaca through self.alpaca
        self.allOrders = Algo.paperOrders # have to be careful not to break these references
        self.allPositions = Algo.paperPositions

        # state variables
        self.cash = cash # buying power NOT literal cash
        self.equity = cash # udpated daily
        self.positions = {} # {symbol: quantity}
        self.orders = {} # {id: {symbol, quantity, price}}
        #  order quantity is positive for buy and negative for sell
        #  order price is an estimate

        # properties
        self.maxPosFrac = maxPosFrac # maximum fraction of buyingPower to hold in a position (at time of order)
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

    def update_metrics(self):
        # TODO: check each datapoint is one market day apart
        growth = [day['growthFrac'] for day in self.history]
        self.mean = statistics.mean(growth)
        self.stdev = statistics.stdev(growth)

    def set_live(self, live):

        # check argument
        if self.live == live:
            warn(f'{self}.set_live({live}) did not change state')
            return
        
        # TODO: cancel orders
        # TODO: close positions
        # TODO: udpate account?

        # update flag and api
        self.live = live
        if live:
            self.alpaca = alpaca
            self.allOrders = Algo.liveOrders
            self.allPositions = Algo.livePositions
        else:
            self.alpaca = alpacaPaper
            self.allOrders = Algo.paperOrders
            self.allPositions = Algo.paperPositions

    def get_trade_quantity(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # returns:
        #   quantity: positive # of shares to buy/sell

        # check symbol
        if symbol not in Algo.assets:
            warn(f'{self.id()} symbol "{symbol}" is not recognized')
            return
        
        # check side and get quote
        if side == 'buy': price = Algo.assets[symbol].ask
        elif side == 'sell': price = Algo.assets[symbol].bid
        else:
            warn(f'{self.id()} trading side "{side}" is not recognized')
            return
        
        # set quantity
        quantity = int(self.maxPosFrac * self.equity / price)
        if quantity * price > self.cash: quantity = int(self.cash / price)
        if quantity == 0: return
        if side == 'sell': quantity *= -1 # set quantity negative for sell

        # check for existing position
        if symbol in self.positions:
            if self.positions[symbol] * quantity > 0: # same side as position
                if abs(self.positions[symbol]) > abs(quantity): # position is large enough
                    return
                elif abs(self.positions[symbol]) > abs(quantity): # add to position
                    quantity -= self.positions[symbol]
                else: # quantity == position
                    return
            elif self.positions[symbol] * quantity < 0: # opposite side from position
                quantity = -self.positions[symbol] # exit position
                # TODO: queue this same trade again
        
        # TODO: check risk
        # TODO: check for leveraged ETFs
        # TODO: check volume

        # check allPositions for zero crossing
        if symbol in self.allPositions:
            if (self.allPositions[symbol] + quantity) * self.allPositions[symbol] < 0: # if trade will swap position
                quantity = -self.allPositions[symbol]
                # TODO: queue this same trade again

        # TODO: check allOrders
        # for existing or [short sell (buy) & short buy (sell)]