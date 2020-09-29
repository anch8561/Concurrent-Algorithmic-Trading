import config as c
import globalVariables as g
from timing import get_time_str, get_date

import json
import statistics as stats
from alpaca_trade_api.rest import APIError
from logging import getLogger
from os import mkdir

# create algoPath if needed
try: mkdir(c.algoPath)
except Exception: pass

class Algo:
    def __init__(self, func, loadData=True, **kwargs):
        self.func = func # function to determine when to enter and exit positions

        # kwargs, name, and self.log
        self.name = ''
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += self.func.__name__
        self.log = getLogger(self.name)

        # paper / live
        self.live = False # if using real money
        self.alpaca = g.alpacaPaper # always call alpaca through self.alpaca
        self.allOrders = g.paperOrders # have to be careful not to break these references
        self.allPositions = g.paperPositions

        # state variables
        self.active = True # if algo might have open positions
        self.buyPow = {'long': 0, 'short': 0} # updated continuously
        self.equity = {'long': 0, 'short': 0} # updated daily
        self.positions = {} # {symbol: {qty, basis}}
        self.orders = {} # {orderID: {symbol, qty, limit, longShort}}
        # qty is positive for buy/long and negative for sell/short
        self.history = {} # {date: {time: event, equity}}

        # attributes to save / load
        self.dataFields = [
            'live',
            'buyPow',
            'equity',
            'positions',
            'orders',
            'history'
        ]

        # load data
        if loadData: self.load_data()

    def activate(self):
        self.active = True
        self.start()

    def deactivate(self):
        # NOTE: may take multiple attempts
        # exit all positions then stop
        if any(position['qty'] for position in self.positions.values()):
            for symbol, position in self.positions.items():
                if position['qty']:
                    self.exit_position(symbol)
        else:
            self.stop()
            self.active = False

    def start(self):
        if not self.active:
            self.log.exception(f'cannot start while inactive')
        else:
            self.log.info('starting')
            self.cancel_all_orders()
            self.update_equity()
            self.update_history('start')
            self.save_data()
    
    def stop(self):
        if not self.active:
            self.log.exception(f'cannot stop while inactive')
        else:
            self.log.info('stopping')
            self.cancel_all_orders()
            self.update_equity()
            self.update_history('stop')
            self.save_data()

    def save_data(self):
        try: # get data
            data = {}
            for field in self.dataFields:
                try: data[field] = self.__getattribute__(field)
                except Exception as e: self.log.exception(e)
        except Exception as e: self.log.exception(e)
        
        try: # write data
            fileName = c.algoPath + self.name + '.data'
            with open(fileName, 'w') as f:
                json.dump(data, f)
        except Exception as e: self.log.exception(e)

    def load_data(self):
        try: # read data
            fileName = c.algoPath + self.name + '.data'
            with open(fileName, 'r') as f:
                data = json.load(f)
        except Exception as e:
            self.log.exception(e)
            return
             
        try: # set data
            for field in self.dataFields:
                try: self.__setattr__(field, data[field])
                except Exception as e: self.log.exception(e)
        except Exception as e: self.log.exception(e)

    def enter_position(self, symbol, side):
        # symbol: e.g. 'AAPL'

        try: # get price and qty
            limitPrice = self.get_limit_price(symbol, side)
            qty = self.get_trade_qty(symbol, side, limitPrice)
        except Exception as e: self.log.exception(e)

        try: # get longShort
            if side == 'buy': longShort = 'long'
            elif side == 'sell': longShort = 'short'
            else:
                self.log.error(f'unknown side: {side}')
                return
        except Exception as e: self.log.exception(e)

        try: # submit order and update buying power
            if self.submit_order(symbol, qty, limitPrice, 'enter'):
                self.buyPow[longShort] -= abs(qty) * limitPrice
        except Exception as e: self.log.exception(e)

    def exit_position(self, symbol):
        # symbol: e.g. 'AAPL'

        try: # get qty
            qty = -self.positions[symbol]['qty']
        except Exception:
            self.log.warning(f'{symbol}\tno position to exit')
            return

        try: # get price and submit order
            if qty > 0: side = 'buy'
            elif qty < 0: side = 'sell'
            else:
                self.log.warning(f'{symbol}\tno position to exit')
                return

            price = self.get_limit_price(symbol, side)
            self.submit_order(symbol, qty, price, 'exit')

        except Exception as e: self.log.exception(e)

    def submit_order(self, symbol, qty, limitPrice, enterExit):
        # symbol: e.g. 'AAPL'
        # qty: int; signed # of shares to trade (positive buy, negative sell)
        # limitPrice: float or None for market order
        # enterExit: 'enter' or 'exit'
        # returns: bool; whether order was accepted

        try: # get side
            if qty > 0: side = 'buy'
            elif qty < 0: side = 'sell'
            else:
                self.log.warning(f'{symbol}\torder quantity is zero')
                return False
        except Exception as e:
            self.log.exception(e)
            return False

        try: # check allPositions for zero crossing
            if symbol in self.allPositions:
                allPosQty = self.allPositions[symbol]['qty']
                if (allPosQty + qty) * allPosQty < 0: # trade will swap position
                    qty = -allPosQty # exit position
                    self.log.debug(f'{symbol}\texiting global position of {allPosQty}')
            else:
                allPosQty = 0
        except Exception as e:
            self.log.exception(e)
            return False

        try: # check allOrders for opposing short
            if qty > 0 and allPosQty == 0: # buying from zero position
                for orderID, order in self.allOrders.items():
                    if order['symbol'] == symbol and order['qty'] < 0: # pending short
                        self.log.debug(f'{symbol}\topposing global order {orderID}')
                        return False
        except Exception as e:
            self.log.exception(e)
            return False

        try:
            self.log.info(f'{symbol}\tordering {qty} shares')

            # submit order
            if limitPrice == None:
                if enterExit == 'enter':
                    self.log.warning('cannot enter position with market order')
                    return False
                order = self.alpaca.submit_order(
                    symbol = symbol,
                    qty = abs(qty),
                    side = side,
                    type = 'market',
                    time_in_force = 'day')
            else:
                order = self.alpaca.submit_order(
                    symbol = symbol,
                    qty = abs(qty),
                    side = side,
                    type = 'limit',
                    time_in_force = 'day',
                    limit_price = limitPrice)

            # add to orders and allOrders
            self.orders[order.id] = {
                'symbol': symbol,
                'qty': qty,
                'limit': limitPrice,
                'enterExit': enterExit}
            self.allOrders[order.id] = {
                'symbol': symbol,
                'qty': qty,
                'limit': limitPrice,
                'enterExit': enterExit,
                'algo': self}
            
            # exit
            return True

        except Exception as e:
            if isinstance(e, APIError):
                self.log.warning(f'{e}\nOrder: {symbol}\t\t\t{qty}\n' +
                f'Algo Position:\t\t{self.positions[symbol]["qty"]}\n' +
                f'Global Position:\t{self.allPositions[symbol]["qty"]}')
            else:
                self.log.exception(f'{e}\nOrder: {symbol}\t\t\t{qty}\n' +
                f'Algo Position:\t\t{self.positions[symbol]["qty"]}\n' +
                f'Global Position:\t{self.allPositions[symbol]["qty"]}')
            return False

    def cancel_all_orders(self):
        for orderID in self.orders:
            self.alpaca.cancel_order(orderID)
        while len(self.orders): pass # FIX: will max out CPU

    def get_limit_price(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        try:
            price = self.get_price(symbol)

            if side == 'buy':
                price *= 1 + c.limitPriceFrac
            elif side == 'sell':
                price *= 1 - c.limitPriceFrac
            else:
                self.log.error(f'unknown side: {side}')

            return price
        except Exception as e:
            if price != None: self.log.exception(e)
            # else place market order (limitPrice == None)

    def get_metrics(self, numDays):
        try: # calculate growth # FIX: overnight algos start and stop on different days
            growth = {'long': [], 'short': []}
            dates = sorted(self.history, reverse=True)
            for ii, date in enumerate(dates[:numDays]):
                growth['long'].append(0)
                growth['short'].append(0)
                startEquity = {}
                for entry in self.history[date].values():
                    if entry['event'] == 'start':
                        startEquity = entry['equity']
                    elif entry['event'] == 'stop' and startEquity:
                        stopEquity = entry['equity']
                        for longShort in ('long', 'short'):
                            try:
                                growth[longShort][ii] += (1 + growth[longShort][ii]) * \
                                    (stopEquity[longShort] - startEquity[longShort]) / startEquity[longShort]
                            except Exception as e:
                                if startEquity != 0: self.log.exception(e)
                        startEquity = {}
        except Exception as e: self.log.exception(e)
        
        metrics = {'mean': {}, 'stdev': {}}
        for longShort in ('long', 'short'):
            try: metrics['mean'][longShort] = stats.mean(growth[longShort])
            except Exception: metrics['mean'][longShort] = None
            
            try: metrics['stdev'][longShort] = stats.stdev(growth[longShort])
            except Exception: metrics['stdev'][longShort] = None
        return metrics

    def get_price(self, symbol):
        try: return g.assets['min'][symbol].close.iloc[-1] # TODO: secBars
        except Exception as e: self.log.exception(e)

    def get_trade_qty(self, symbol, side, price, volumeMult=1, barFreq='min'):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # price: float
        # volumeMult: float; volume limit multiplier
        # barFreq: 'sec', 'min', or 'day'; bar frequency for checking volume limit
        # returns: int; signed # of shares to trade (positive buy, negative sell)

        try: # get buying power and equity
            if side == 'buy':
                equity = self.equity['long']
                buyPow = self.buyPow['long']
            elif side == 'sell':
                equity = self.equity['short']
                buyPow = self.buyPow['short']
        except Exception as e:
            self.log.exception(e)
            return 0

        try: # check price
            if side == 'buy' and price < c.minLongPrice:
                self.log.debug(f'{symbol}\tshare price < {c.minLongPrice}')
                return 0
            elif side == 'sell' and price < c.minShortPrice:
                self.log.debug(f'{symbol}\tshare price < {c.minShortPrice}')
                return 0
        except Exception as e:
            # NOTE: possibly triggered by missing 1st bar (price == None)
            self.log.exception(e)
            return 0

        try: # set quantity
            qty = int(c.maxPosFrac * equity / price)
            reason = 'max position fraction'
        except Exception as e:
            self.log.exception(e)
            return 0

        try: # check buying power
            if qty * price > buyPow:
                qty = int(buyPow / price)
                reason = 'buying power'
        except Exception as e:
            self.log.exception(e)
            return 0
        
        try: # check volume
            try:
                volume = g.assets[barFreq][symbol].volume.iloc[-1]
            except Exception as e:
                self.log.exception(e)
                volume = 0
            if qty > volume * volumeMult:
                qty = volume * volumeMult
                reason = 'volume'
        except Exception as e:
            self.log.exception(e)
            return 0

        # check zero
        if qty == 0: return 0

        try: # set sell quantity negative
            if side == 'sell': qty *= -1
            self.log.debug(f'{symbol}\t{reason} qty limit: {qty}')
        except Exception as e:
            self.log.exception(e)
            return 0

        try: # check for existing position
            if symbol in self.positions:
                posQty = self.positions[symbol]['qty']
                if posQty * qty > 0: # same side as position
                    if abs(posQty) < abs(qty): # position is smaller than order
                        qty -= posQty # add to position
                        self.log.debug(f'{symbol}\tadding {qty} to position of {posQty}')
                    else: # position is large enough
                        self.log.debug(f'{symbol}\tposition of {posQty} is large enough')
                        return 0
                elif posQty * qty < 0: # opposite side from position
                    qty = -posQty # exit position
                    self.log.debug(f'{symbol}\texiting position of {posQty}')
        except Exception as e:
            self.log.exception(e)
            return 0

        try: # check for existing orders
            for orderID, order in self.orders.items():
                if order['symbol'] == symbol:
                    if order['qty'] * qty < 0: # opposite side
                        self.alpaca.cancel_order(orderID)
                        self.log.debug(f'{symbol}\tcancelling opposing order {orderID}')
                    else: # same side
                        self.log.debug(f'{symbol}\talready placed order for {order["qty"]}')
                        return 0
        except Exception as e:
            self.log.exception(e)
            return 0

        # TODO: check risk

        return qty

    def set_live(self, live):
        # live: bool; if algo uses real money

        self.live = live
        if live:
            self.alpaca = g.alpacaLive
            self.allOrders = g.liveOrders
            self.allPositions = g.livePositions
        else:
            self.alpaca = g.alpacaPaper
            self.allOrders = g.paperOrders
            self.allPositions = g.paperPositions

    def update_equity(self):
        # copy buying power
        self.equity = self.buyPow.copy()

        # check positions
        for symbol, position in self.positions.items():
            qty = position['qty']
            if qty: # get position value
                longShort = 'long' if qty > 0 else 'short'
                price = self.get_price(symbol)
                try: self.equity[longShort] += price * abs(qty)
                except Exception as e:
                    if price == None: # exit position of unknown value
                        self.log.warning(f'Exiting untracked position: {qty} {symbol}')
                        self.exit_position(symbol)

                        price = self.alpaca.get_last_trade(symbol).price
                        self.log.warning(f'Adding estimated value to equity: ${price * abs(qty)}')
                        self.equity[longShort] += price * abs(qty)
                    else: self.log.exception(e)

    def update_history(self, event):
        # event: 'start' or 'stop'
        date = get_date()
        if date not in self.history:
            self.history[date] = {}
        self.history[date][get_time_str()] = {
            'event': event,
            'equity': self.equity
        }

class NightAlgo(Algo):
    def tick(self):
        if (
            self.buyPow['long'] >= c.minTradeBuyPow or
            self.buyPow['short'] >= c.minTradeBuyPow
        ):
            try: self.func(self)
            except Exception as e: self.log.exception(e)

class DayAlgo(Algo):
    def tick(self):
        try: self.func(self)
        except Exception as e: self.log.exception(e)
