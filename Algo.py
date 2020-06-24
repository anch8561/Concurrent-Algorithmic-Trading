# base class for algos

import alpacaAPI
from config import maxPosFrac, limitPriceFrac, minLongPrice, minShortPrice
from warn import warn

from datetime import timedelta
import statistics, json

class Algo:
    assets = {} # {symbol: {easyToBorrow, secBars, minBars, dayBars, <various indicators>}}
    # 'shortable': bool; whether easy_to_borrow on alpaca
    # 'secBars': pd.dataframe; past 10k second bars
    # 'minBars': pd.dataframe; past 1k minute bars
    # 'dayBars': pd.dataframe; past 100 day bars

    paperOrders = {} # {orderID: {symbol, qty, limit, algo}}
    liveOrders = {}

    paperPositions = {} # {symbol: {qty, basis}}
    livePositions = {}

    # streaming buffers
    writing = False
    secBars = []
    minBars = []
    orderUpdates = []

    def __init__(self, buyPow, timeframe, equityStyle, enterIndicators, exitIndicators = None, tickFreq='sec'):
        # TODO: check arguments

        # paper / live
        self.live = False # whether using real money
        self.alpaca = alpacaAPI.alpacaPaper # always call alpaca through self.alpaca
        self.allOrders = Algo.paperOrders # have to be careful not to break these references
        self.allPositions = Algo.paperPositions

        # state variables
        self.active = True # if algo has open positions or needs its metrics updated
        self.buyPow = buyPow # buying power
        self.equity = buyPow # udpated daily
        self.positions = {} # {symbol: {qty, basis}}
        self.orders = {} # {orderID: {symbol, qty, limit}}
        # qty is positive for buy/long and negative for sell/short

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
            'buyPow',
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
        # live: bool; whether algo uses real money

        # check argument
        if self.live == live:
            warn(f'{self.id()} set_live({live}) did not change state')
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

    def id(self): warn(f'{self} missing id()')

    def tick(self, TTOpen, TTClose):
        # TTOpen: datetime.timedelta; time until open (open time - current time)
        # TTClose: datetime.timedelta; time until close (close time - current time)
        pass

    def overnight_enter(self):
        numTrades = int(self.buyPow / (self.equity * maxPosFrac))

        for symbol in Algo.assets:
            enterSignal = True
            for indicator in self.enterIndicators:
                if (
                    (
                        indicator.type is 'rank' and
                        Algo.assets[symbol][indicator] > numTrades
                        # FIX: unlikely to place numTrades trades unless all other indicators are true for top ranked
                    ) or
                    (
                        indicator.type is 'bool' and
                        Algo.assets[symbol][indicator] == False
                    )
                ):
                    enterSignal = False
            if enterSignal: self.enter_position(symbol)

    def enter_position(self, symbol):
        # symbol: e.g. 'AAPL'
        qty = self.get_trade_qty(symbol)
        self.submit_order(symbol, qty)

    def exit_position(self, symbol):
        # symbol: e.g. 'AAPL'

        # get quantity
        try: qty = -self.positions[symbol]['qty']
        except: qty = 0
        if qty == 0: warn(f'{self.id()} no position in "{symbol}" to exit')

        # submit order
        self.submit_order(symbol, qty)

    def exit_all_positions(self):
        for symbol in self.positions:
            self.exit_position(symbol)

    def get_limit_price(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        # get price
        try: price = Algo.assets[symbol]['secBars'].iloc[-1].close
        except Exception as e: print(e)

        # add limit
        if side == 'buy':
            price *= 1 + limitPriceFrac
        elif side == 'sell':
            price *= 1 - limitPriceFrac
        else: warn(f'{self.id()} unknown side "{side}"')

        return price

    def get_trade_qty(self, symbol, limitPrice=None, volumeMult=1, barType='minBars'):
        # symbol: e.g. 'AAPL'
        # limitPrice: float or None for market order
        # volumeMult: float; volume limit multiplier
        # barType: 'secBars', 'minBars', or 'dayBars'; bar type for checking volume limit
        # returns: int; signed # of shares to trade (positive buy, negative sell)

        # check arguments
        # TODO: replace with try except
        if symbol not in Algo.assets:
            warn(f'{self.id()} unknown symbol "{symbol}"')
            return 0

        # get side
        if self.equityStyle == 'long':
            side = 'buy'
        elif self.equityStyle == 'short':
            side = 'sell'
        else:
            warn(f'{self.id()} unknown equityStyle "{self.equityStyle}"')

        # get price
        if limitPrice == None:
            price = self.get_limit_price(symbol)
        else:
            price = limitPrice

        # check price
        if side == 'long' and price < 3:
            print(f'{symbol}: share price < 3.00')
            return 0
        if side == 'short' and price < 17:
            print(f'{symbol}: share price < 17.00')
            return 0

        # set quantity
        qty = int(maxPosFrac * self.equity / price)
        print(f'{symbol}: quantity: {qty}')

        # check buying power
        if qty * price > self.buyPow:
            qty = int(self.buyPow / price)
            print(f'{symbol}: buyPow limit quantity: {qty}')
        
        # check volume
        try:
            volume = Algo.assets[symbol][barType][0].volume
        except Exception as e:
            print(e)
        if qty > volume * volumeMult:
            qty = volume * volumeMult
            print(f'{symbol}: volume limit quantity: {qty}')

        # check zero
        if qty == 0: return 0
        
        # set sell quantity negative
        if side == 'sell': qty *= -1

        # check for existing position
        if symbol in self.positions:
            posQty = self.positions[symbol]['qty']
            if posQty * qty > 0: # same side as position
                if abs(posQty) < abs(qty): # position is smaller than order
                    qty -= posQty # add to position
                    print(f'{symbol}: adding {qty} to position of {posQty}')
                else: # position is large enough
                    print(f'{symbol}: position of {posQty} is large enough')
                    return 0
            elif posQty * qty < 0: # opposite side from position
                qty = -posQty # exit position
                print(f'{symbol}: exiting position of {posQty}')
                # TODO: queue same trade again

        # check for existing orders
        for orderID, order in self.orders.items():
            if order['symbol'] == symbol:
                if order['qty'] * qty < 0: # opposite side
                    warn(f'{self.id()} opposing orders')
                    # TODO: log first order info
                    # TODO: cancel first order
                else: # same side
                    print(f'{symbol}: already placed order for {order["qty"]}')
                    return 0

        # TODO: check risk
        # TODO: check for leveraged ETFs

        return qty

    def submit_order(self, symbol, qty, limitPrice=None):
        # symbol: e.g. 'AAPL'
        # qty: int; signed # of shares to trade (positive buy, negative sell)
        # limitPrice: float or str; limit price (market order if limit == None)

        if qty == 0: return

        # check allPositions for zero crossing
        if symbol in self.allPositions:
            allPosQty = self.allPositions[symbol]['qty']
            if (allPosQty + qty) * allPosQty < 0: # trade will swap position
                qty = -allPosQty # exit position
                print(f'{symbol}: exiting global position of {qty}')
                # TODO: queue same trade again
        else:
            allPosQty = 0

        # check allOrders for opposing short
        if qty > 0 and allPosQty == 0: # buying from zero position
            for orderID, order in self.allOrders.items():
                if order['symbol'] == symbol and order['qty'] < 0: # pending short
                    warn(f'{self.id()} opposing global order of {order["qty"]}')
                    # TODO: log first order info
                    return

        # get side and limitPrice
        side = 'buy' if qty > 0 else 'sell'
        if limitPrice == None: limitPrice = self.get_limit_price(symbol)

        try:
            # submit order
            order = self.alpaca.submit_order(
                symbol = symbol,
                qty = abs(qty),
                side = side,
                type = 'limit',
                time_in_force = 'day',
                limit_price = limitPrice)
            
            self.buyPow -= abs(qty) * limit

            # add to orders and allOrders
            orderID = order.order_id
            self.orders[orderID] = {
                'symbol': symbol,
                'qty': qty,
                'limit': limit}
            self.allOrders[orderID] = {
                'symbol': symbol,
                'qty': qty,
                'limit': limitPrice,
                'algo': self}
        except Exception as e: print(e)

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
