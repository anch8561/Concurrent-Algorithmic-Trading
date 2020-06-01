# base class for algos

from alpacaAPI import alpaca, alpacaPaper
from warn import warn
import statistics

class Algo:
    assets = {} # {symbol: {easyToBorrow, secBars, minBars, dayBars}}
    # 'easyToBorrow': bool; whether shortable on alpaca
    # 'secBars': list; past 10k second bars as received from polygon
    # 'minBars': list; past 1k minute bars as received from polygon
    # 'dayBars': list; past 100 daily bars as received from polygon

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

    def id(self):
        warn(f'{self} missing id()')

    def get_trade_quantity(self, symbol, side, price, orderType, volumeMult=1, barType='minBars'):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # price: float
        # orderType: 'market' or 'limit' (market orders have 4% added to price for the cash check)
        # returns: 
        #   quantity: int; positive # of shares to buy/sell

        # check arguments
        if symbol not in Algo.assets:
            warn(f'{self.id()} symbol "{symbol}" not recognized')
            return
        if side not in ('buy', 'sell'):
            warn(f'{self.id()} trading side "{side}" not recognized')
            return
        if barType not in ('secBars', 'minBars', 'dayBars'):
            warn(f'{self.id()} barType "{barType}" not recognized')
            return

        # check share price
        if side == 'long' and price < 3:
            print(f'{symbol}: Share price < 3.00')
            return
        if side == 'short' and price < 17:
            print(f'{symbol}: Share price < 17.00')
            return

        # set quantity
        quantity = int(self.maxPosFrac * self.equity / price)
        print(f'{symbol}: Quantity: {quantity}')

        # check cash
        if orderType == "market": price *= 1.04
        if quantity * price > self.cash:
            quantity = int(self.cash / price)
            print(f'{symbol}: Cash limit quantity: {quantity}')
        
        # check volume
        volume = Algo.assets[symbol][barType][0].volume
        if quantity > volume * volumeMult:
            quantity = volume * volumeMult
            print(f'{symbol}: Volume limit quantity: {quantity}')

        # check zero
        if quantity == 0: return
        
        # set sell quantity negative
        if side == 'sell': quantity *= -1

        # check for existing position
        if symbol in self.positions:
            if self.positions[symbol] * quantity > 0: # same side as position
                if abs(self.positions[symbol]) > abs(quantity): # add to position
                    quantity -= self.positions[symbol]
                    print(f'{symbol}: Adding {quantity} to exising position of {self.positions[symbol]}')
                else: # position is large enough
                    print(f'{symbol}: Exising position of {self.positions[symbol]} large enough')
                    return
            elif self.positions[symbol] * quantity < 0: # opposite side from position
                quantity = -self.positions[symbol] # exit position
                print(f'{symbol}: Exiting position of {self.positions[symbol]}')
                # TODO: queue same trade again

        # check for existing orders
        for order in self.orders:
            if order['symbol'] == symbol:
                if order['quantity'] * quantity < 0: # opposite side
                    order = self.alpaca.get_order(order['id'])
                    warn(f'{self.id()} opposing orders')
                    # TODO: log first order info
                    # TODO: cancel first order
                    return
                else: # same side
                    return

        # check allPositions for zero crossing
        if symbol in self.allPositions:
            if (self.allPositions[symbol] + quantity) * self.allPositions[symbol] < 0: # if trade will swap position
                quantity = -self.allPositions[symbol]
                print(f'{symbol}: Exiting global position of {self.allPositions[symbol]}')
                # TODO: queue same trade again

        # TODO: check allOrders for opposing shorts
        for order in self.allOrders:
            if order['symbol'] == symbol:
                if order['quantity'] < 0 and self.allPositions[symbol] == 0: # pending short
                    order = self.alpaca.get_order(order['id'])
                    warn(f'{self.id()} opposing orders')
                    # TODO: log first order info
                    # TODO: cancel first order


        # TODO: check risk
        # TODO: check for leveraged ETFs