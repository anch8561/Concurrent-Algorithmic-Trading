# base class for algos

import alpacaAPI
from config import maxPosFrac
from warn import warn

from datetime import timedelta
import statistics, json

class Algo:
    assets = {} # {symbol: {easyToBorrow, secBars, minBars, dayBars, <various indicators>}}
    # 'shortable': bool; whether easy_to_borrow on alpaca
    # 'secBars': pd.dataframe; past 10k second bars
    # 'minBars': pd.dataframe; past 1k minute bars
    # 'dayBars': pd.dataframe; past 100 day bars

    paperOrders = {} # {id: {symbol, quantity, price, algo}}
    liveOrders = {}

    paperPositions = {} # {symbol: quantity}
    livePositions = {}

    # streaming buffers
    writing = False
    secBars = []
    minBars = []
    orderUpdates = []

    def __init__(self, BP, timeframe, equityStyle, enterIndicators, exitIndicators = None, tickFreq='sec'):
        # TODO: check arguments

        # paper / live
        self.live = False # whether using real money
        self.alpaca = alpacaAPI.alpacaPaper # always call alpaca through self.alpaca
        self.allOrders = Algo.paperOrders # have to be careful not to break these references
        self.allPositions = Algo.paperPositions

        # state variables
        self.BP = BP # buying power
        self.equity = BP # udpated daily
        self.positions = {} # {symbol: {quantity, basis}}
        self.orders = {} # {id: {symbol, quantity, price}}
        # quantity is positive for buy/long and negative for sell/short
        # order price is an estimate

        # inticators
        self.enterIndicators = enterIndicators
        self.exitIndicators = exitIndicators

        # properties
        self.timeframe = timeframe # 'intraday', 'overnight', or 'multiday'
        self.equityStyle = equityStyle # 'long', 'short', or 'longShort'
        self.tickFreq = tickFreq # 'sec' or 'min'

        # risk and performance metrics
        self.history = [] # [{time, prevTime, equity, prevEquity, cashFlow, growthFrac}]
        # change in equity minus cash allocations over previous equity
        # extra fields are kept for error proofing
        self.mean = 0 # average daily growth
        self.stdev = 0 # sample standard deviation of daily growth
        self.allocFrac = 0

        # attributes to save / load
        self.dataFields = [
            'live',
            'history',
            'BP',
            'equity',
            'positions',
            'orders',
            'timeframe',
            'equityStyle',
            'tickFreq'
        ]

    def update_metrics(self):
        # TODO: check each datapoint is one market day apart
        growth = [day['growthFrac'] for day in self.history]
        if len(growth) >= 5: growth = growth[5:]
        self.mean = statistics.mean(growth)
        self.stdev = statistics.stdev(growth)

    def set_live(self, live):

        # check argument
        if self.live == live:
            warn(f'{self}.set_live({live}) did not change state')
            return
        
        # TODO: cancel orders
        # TODO: close positions

        # update flag and api
        self.live = live
        if live:
            self.alpaca = alpacaAPI.alpaca
            self.allOrders = Algo.liveOrders
            self.allPositions = Algo.livePositions
        else:
            self.alpaca = alpacaAPI.alpacaPaper
            self.allOrders = Algo.paperOrders
            self.allPositions = Algo.paperPositions

    def id(self):
        warn(f'{self} missing id()')

    def tick(self, openTimedelta, closeTimedelta):
        # openTimedelta: datetime.timedelta (current time - open time)
        # openTimedelta: datetime.timedelta (current time - close time)
        pass

    def overnight_enter(self, symbol):
        # check if indicator conditions are met
        for indicator in self.enterIndicators:
            if not Algo.assets[symbol][indicator]:
                return
        
        # enter position
        if self.equityStyle == 'long': side = 'buy'
        elif self.equityStyle == 'short': side = 'sell'
        else: warn(f'unknown equity style "{self.equityStyle}"')
        qty = self.get_trade_quantity(symbol, side)

    def overnight_exit(self):
        # exit all positions
        for symbol in self.positions: pass

    def get_trade_quantity(self, symbol, side, limitPrice=None, volumeMult=1, barType='minBars'):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # limitPrice: float or None for market order
        # volumeMult: float; volume limit multiplier
        # barType: 'secBars', 'minBars', or 'dayBars'; quantity < volume of last bar of this type
        # returns: 
        #   quantity: int; positive # of shares to buy/sell

        # check arguments
        if symbol not in Algo.assets:
            warn(f'{self.id()} symbol "{symbol}" not recognized')
            return
        if side not in ('buy', 'sell'):
            warn(f'{self.id()} trading side "{side}" not recognized')
            return
        # TODO: check other args
        if barType not in ('secBars', 'minBars', 'dayBars'):
            warn(f'{self.id()} barType "{barType}" not recognized')
            return

        # get price
        if limitPrice == None:
            price = Algo.assets[symbol]['secBars'][0].close
        else:
            price = limitPrice

        # check price
        if side == 'long' and price < 3:
            print(f'{symbol}: Share price < 3.00')
            return
        if side == 'short' and price < 17:
            print(f'{symbol}: Share price < 17.00')
            return

        # set quantity
        quantity = int(maxPosFrac * self.equity / price)
        print(f'{symbol}: Quantity: {quantity}')

        # check buying power
        if limitPrice == None: price *= 1.04
        if quantity * price > self.BP:
            quantity = int(self.BP / price)
            print(f'{symbol}: BP limit quantity: {quantity}')
        
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
                    print(f'{symbol}: Existing position of {self.positions[symbol]} large enough')
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
                else: # same side
                    print(f'{symbol}: Existing order for {order["quantity"]}')
                    return

        # check allPositions for zero crossing
        if symbol in self.allPositions:
            if (self.allPositions[symbol] + quantity) * self.allPositions[symbol] < 0: # if trade will swap position
                quantity = -self.allPositions[symbol]
                print(f'{symbol}: Exiting global position of {self.allPositions[symbol]}')
                # TODO: queue same trade again

        # check allOrders for opposing shorts
        for order in self.allOrders:
            if order['symbol'] == symbol:
                if order['quantity'] < 0 and self.allPositions[symbol] == 0: # pending short
                    order = self.alpaca.get_order(order['id'])
                    warn(f'{self.id()} opposing global order')
                    # TODO: log first order info
                    return


        # TODO: check risk
        # TODO: check for leveraged ETFs

        return quantity

    def cancel_order(self, id):
        # id: str

        # cancel order
        self.alpaca.cancel_order(id)

        # remove from orders and allOrders
        for orders in (self.orders, self.allOrders):
            index = None
            for ii, order in enumerate(orders):
                if order['id'] == id:
                    index = ii
            if index is not None: orders.pop(index)

    def save_data(self):
        # get data
        data = {}
        for field in self.dataFields:
            data[field] = self.__getattribute__(field)
        
        # write data
        fileName = self.id() + '.data'
        file = open(fileName, 'w')
        json.dump(data, file)
        file.close()

    def load_data(self):
        # read data
        fileName = self.id() + '.data'
        file = open(fileName, 'r')
        data = json.load(file)
        file.close()

        # set data
        for field in self.dataFields:
            self.__setattr__(field, data[field])
