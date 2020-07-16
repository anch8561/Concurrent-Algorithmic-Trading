import alpacaAPI
import config as c
import globalVariables as g
from timing import get_time, get_date
from warn import warn

import json, os
import statistics as stats

# create c.algoPath if needed
try: os.mkdir(c.algoPath)
except: pass

class Algo:
    def __init__(self, func, **kwargs):
        self.func = func # function to determine when to enter and exit positions

        # name and kwargs
        self.name = ''
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += self.func.__name__

        # paper / live
        self.live = False # whether using real money
        self.alpaca = alpacaAPI.alpacaPaper # always call alpaca through self.alpaca
        self.allOrders = g.paperOrders # have to be careful not to break these references
        self.allPositions = g.paperPositions

        # state variables
        self.active = True # whether algo might have open positions
        self.buyPow = {'long': 0, 'short': 0} # updated continuously
        self.equity = {'long': 0, 'short': 0} # updated daily
        self.positions = {} # {symbol: {qty, basis}}
        self.orders = {} # {orderID: {symbol, qty, limit, longShort}}
        # qty is positive for buy/long and negative for sell/short
        self.ticking = False # trade update blocking flag
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
        self.load_data()

    def activate(self):
        self.active = True
        self.start()

    def deactivate(self):
        # NOTE: may take multiple attempts
        # exit all positions then stop
        self.set_ticking(True)
        if any(position['qty'] for position in self.positions.values()):
            for symbol, position in self.positions.items():
                if position['qty']:
                    self.exit_position(symbol)
        else:
            self.stop()
            self.active = False
        self.set_ticking(False)

    def start(self):
        if not self.active:
            warn(f'{self.name} cannot start while inactive')
        else:
            self.cancel_all_orders()
            self.set_ticking(True)
            self.update_equity()
            self.update_history('start')
            self.save_data()
            self.set_ticking(False)
    
    def stop(self):
        if not self.active:
            warn(f'{self.name} cannot stop while inactive')
        else:
            self.cancel_all_orders()
            self.set_ticking(True)
            self.update_equity()
            self.update_history('stop')
            self.save_data()
            self.set_ticking(False)

    def save_data(self):
        try: # get data
            data = {}
            for field in self.dataFields:
                data[field] = self.__getattribute__(field)
        except Exception as e: warn(e)
        
        try: # write data
            fileName = c.algoPath + self.name + '.data'
            with open(fileName, 'w') as f:
                json.dump(data, f)
        except Exception as e: warn(e)

    def load_data(self):
        try: # read data
            fileName = c.algoPath + self.name + '.data'
            with open(fileName, 'r') as f:
                data = json.load(f)
        except Exception as e:
            warn(e)
            return
             
        try: # set data
            for field in self.dataFields:
                self.__setattr__(field, data[field])
        except Exception as e: warn(e)

    def enter_position(self, symbol, side):
        # symbol: e.g. 'AAPL'

        # get price and qty
        price = self.get_limit_price(symbol, side)
        qty = self.get_trade_qty(symbol, side, price)

        # get longShort
        if side == 'buy': longShort = 'long'
        elif side == 'sell': longShort = 'short'

        # submit order and update buying power
        self.submit_order(symbol, qty, price, longShort, 'enter')
        self.buyPow[longShort] -= abs(qty) * price

    def exit_position(self, symbol):
        # symbol: e.g. 'AAPL'

        # get qty
        try: qty = -self.positions[symbol]['qty']
        except:
            warn(f'{self.name} no position in "{symbol}" to exit')
            return

        # get side and longShort
        if qty > 0:
            side = 'buy'
            longShort = 'short'
        elif qty < 0:
            side = 'sell'
            longShort = 'long'
        else: return

        # get price and submit order
        price = self.get_limit_price(symbol, side)
        self.submit_order(symbol, qty, price, longShort, 'exit')

    def submit_order(self, symbol, qty, limitPrice, longShort, enterExit):
        # symbol: e.g. 'AAPL'
        # qty: int; signed # of shares to trade (positive buy, negative sell)
        # longShort: 'long' or 'short'
        # limitPrice: float or None for configured price collar

        if qty == 0: return

        # check allPositions for zero crossing
        if symbol in self.allPositions:
            allPosQty = self.allPositions[symbol]['qty']
            if (allPosQty + qty) * allPosQty < 0: # trade will swap position
                qty = -allPosQty # exit position
                if c.verbose: print(f'{self.name}\t{symbol}\texiting global position of {qty}')
        else:
            allPosQty = 0

        # check allOrders for opposing short
        if qty > 0 and allPosQty == 0: # buying from zero position
            for orderID, order in self.allOrders.items():
                if order['symbol'] == symbol and order['qty'] < 0: # pending short
                    if c.verbose: print(f'{self.name}\t{symbol}\topposing global order {orderID}')
                    return

        # get side
        side = 'buy' if qty > 0 else 'sell'

        try:
            print(f'{self.name}\t{symbol}\tordering {qty} shares')

            # submit order
            order = self.alpaca.submit_order(
                symbol = symbol,
                qty = abs(qty),
                side = side,
                type = 'limit',
                time_in_force = 'day',
                limit_price = limitPrice)

            # add to orders and allOrders
            orderID = order.id
            self.orders[orderID] = {
                'symbol': symbol,
                'qty': qty,
                'limit': limitPrice,
                'longShort': longShort,
                'enterExit': enterExit}
            self.allOrders[orderID] = {
                'symbol': symbol,
                'qty': qty,
                'limit': limitPrice,
                'longShort': longShort,
                'enterExit': enterExit,
                'algo': self}
        except Exception as e: warn(e)

    def cancel_all_orders(self):
        for orderID in self.orders:
            self.alpaca.cancel_order(orderID)
        while len(self.orders): pass

    def get_limit_price(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        price = self.get_price(symbol)

        try:
            if side == 'buy':
                price *= 1 + c.limitPriceFrac
            elif side == 'sell':
                price *= 1 - c.limitPriceFrac
            else: warn(f'{self.name} unknown side "{side}"')

            return price
        except: pass

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
                            except: pass # in case start equity is zero
                        startEquity = {}
        except Exception as e: warn(f'{self.name}\n{e}')
        
        try: # calculate mean and stdev
            metrics = {'mean': {}, 'stdev': {}}
            for longShort in ('long', 'short'):
                metrics['mean'][longShort] = stats.mean(growth[longShort])
                try: metrics['stdev'][longShort] = stats.stdev(growth[longShort])
                except: metrics['stdev'][longShort] = None
            return metrics
        except Exception as e: warn(f'{self.name}\n{e}')

    def get_price(self, symbol):
        try:
            return g.assets['min'][symbol].close.iloc[-1] # TODO: secBars
        except Exception as e:
            warn(f'{symbol}\tno price data', e)
            return self.alpaca.get_last_trade(symbol).price

    def get_trade_qty(self, symbol, side, price, volumeMult=1, barFreq='min'):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # limitPrice: float or None for configured price collar
        # volumeMult: float; volume limit multiplier
        # barFreq: 'sec', 'min', or 'day'; bar frequency for checking volume limit
        # returns: int; signed # of shares to trade (positive buy, negative sell)

        # get buying power and equity
        if side == 'buy':
            equity = self.equity['long']
            buyPow = self.buyPow['long']
        elif side == 'sell':
            equity = self.equity['short']
            buyPow = self.buyPow['short']

        # check price
        if side == 'buy' and price < c.minLongPrice:
            if c.verbose: print(f'{self.name}\t{symbol}\tshare price < {c.minLongPrice}')
            return 0
        elif side == 'sell' and price < c.minShortPrice:
            if c.verbose: print(f'{self.name}\t{symbol}\tshare price < {c.minShortPrice}')
            return 0

        # set quantity
        qty = int(c.maxPosFrac * equity / price)
        reason = 'max position fraction'

        # check buying power
        if qty * price > buyPow:
            qty = int(buyPow / price)
            reason = 'buying power'
        
        # check volume
        try:
            volume = g.assets[barFreq][symbol].volume.iloc[-1]
        except Exception as e:
            warn(e)
            volume = 0
        if qty > volume * volumeMult:
            qty = volume * volumeMult
            reason = 'volume'

        # check zero
        if qty == 0: return 0

        # set sell quantity negative
        if side == 'sell': qty *= -1
        if c.verbose: print(f'{self.name}\t{symbol}\t{reason} qty limit: {qty}')

        # check for existing position
        if symbol in self.positions:
            posQty = self.positions[symbol]['qty']
            if posQty * qty > 0: # same side as position
                if abs(posQty) < abs(qty): # position is smaller than order
                    qty -= posQty # add to position
                    if c.verbose: print(f'{self.name}\t{symbol}\tadding {qty} to position of {posQty}')
                else: # position is large enough
                    if c.verbose: print(f'{self.name}\t{symbol}\tposition of {posQty} is large enough')
                    return 0
            elif posQty * qty < 0: # opposite side from position
                qty = -posQty # exit position
                if c.verbose: print(f'{self.name}\t{symbol}\texiting position of {posQty}')

        # check for existing orders
        for orderID, order in self.orders.items():
            if order['symbol'] == symbol:
                if order['qty'] * qty < 0: # opposite side
                    self.alpaca.cancel_order(orderID)
                    if c.verbose: print(f'{self.name}\t{symbol}\tcancelling opposing order {orderID}')
                else: # same side
                    if c.verbose: print(f'{self.name}\t{symbol}\talready placed order for {order["qty"]}')
                    return 0

        # TODO: check risk

        return qty

    def set_live(self, live):
        # live: bool; whether algo uses real money
        self.live = live
        if live:
            self.alpaca = alpacaAPI.alpacaLive
            self.allOrders = g.liveOrders
            self.allPositions = g.livePositions
        else:
            self.alpaca = alpacaAPI.alpacaPaper
            self.allOrders = g.paperOrders
            self.allPositions = g.paperPositions

    def set_ticking(self, ticking):
        # ticking: bool; whether algo is accessing positions or orders
        # (blocks trade updates)
        self.ticking = ticking
        print(f'{self.name}\tticking = {ticking}')
        if ticking:
            waiting = False
            if g.processingTrade:
                waiting = True
                print('Waiting for processingTrade == False')
            while g.processingTrade: pass
            if waiting: print('Done waiting')

    def update_equity(self):
        # copy buying power
        self.equity = self.buyPow.copy()

        # check positions
        for symbol, position in self.positions.items():
            qty = position['qty']
            if qty: # get position value
                longShort = 'long' if qty > 0 else 'short'
                price = self.get_price(symbol)
                self.equity[longShort] += price * abs(qty)

    def update_history(self, event):
        # event: 'start' or 'stop'
        date = get_date()
        if date not in self.history:
            self.history[date] = {}
        self.history[date][get_time()] = {
            'event': event,
            'equity': self.equity
        }

class NightAlgo(Algo):
    def tick(self):
        if sum(self.buyPow.values()) > c.minTradeBuyPow * 2:
            self.set_ticking(True)
            self.func(self)
            self.set_ticking(False)

class DayAlgo(Algo):
    def tick(self):
        self.set_ticking(True)
        self.func(self)
        self.set_ticking(False)
