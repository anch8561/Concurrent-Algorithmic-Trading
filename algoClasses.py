import config as c
import globalVariables as g
from tick_algos import get_limit_price
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

        # kwargs, name, and log
        self.name = ''
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += self.func.__name__
        self.log = getLogger(self.name)

        # state variables
        self.active = True # if algo might have open positions
        self.livePaper = 'paper' # TODO: concurrent live/paper
        self.buyPow = {'long': 0, 'short': 0} # updated continuously
        self.equity = {'long': 0, 'short': 0} # updated daily
        self.positions = {} # {symbol: {qty, basis}}
        self.pendingOrders = {'long': {}, 'short': {}} # {symbol: {algo, longShort, qty}}
        self.queuedOrders = {'long': {}, 'short': {}} # {symbol: {algo, longShort, qty}}
        self.history = {} # {date: {time: event, equity}}

        # attributes to save / load
        self.dataFields = [
            'livePaper',
            'buyPow',
            'equity',
            'positions',
            'orders',
            'history']

        # load data
        if loadData: self.load_data()

    def activate(self):
        self.active = True
        self.start()

    def deactivate(self):
        # exit all positions then stop
        # NOTE: may take multiple attempts
        noPositions = True
        for symbol, position in self.positions.items():
            if position['qty']:
                noPositions = False
                longShort = 'long' if position['qty'] > 0 else 'short'
                self.queuedOrders[longShort][symbol] = {
                    'algo': self,
                    'longShort': longShort,
                    'qty': -position['qty']}
        if noPositions:
            self.stop()
            self.active = False

    def start(self):
        if not self.active:
            self.log.exception(f'cannot start while inactive')
        else:
            self.log.info('starting')
            self.update_equity()
            self.update_history('start')
            self.save_data()
    
    def stop(self):
        if not self.active:
            self.log.exception(f'cannot stop while inactive')
        else:
            self.log.info('stopping')
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

    def get_trade_qty(self, symbol, side, price):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # price: float; limit price
        # returns: int; signed # of shares to trade

        try: # get buying power and equity
            if side == 'buy':
                equity = self.equity['long']
                buyPow = self.buyPow['long']
            elif side == 'sell':
                equity = self.equity['short']
                buyPow = self.buyPow['short']
            else:
                self.log.error(f'Unknown side: {side}')
                return 0
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
            if price == None: self.log.debug(e)
            else: self.log.exception(e)
            return 0

        try: # set quantity
            qty = int(c.maxPosFrac * equity / price)
            reason = 'max position'
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

        # check zero
        if qty == 0: return 0

        try: # set sell quantity negative
            if side == 'sell': qty *= -1
            self.log.debug(f'{symbol}\t{reason} qty limit: {qty}')
        except Exception as e:
            self.log.exception(e)
            return 0

        try: # check for position (same side)
            positionQty = self.positions[symbol]['qty']
            if positionQty * qty > 0: # same side
                if abs(positionQty) < abs(qty): # position smaller than order
                    qty -= positionQty # add to position
                    self.log.debug(f'{symbol}\tadding {qty} to position of {positionQty}')
                else: # position large enough
                    self.log.debug(f'{symbol}\tposition of {positionQty} is large enough')
                    return 0
        except Exception as e:
            self.log.exception(e)
            return 0

        except Exception as e:
            self.log.exception(e)
            return 0

        # TODO: check risk

        return qty

    def queue_order(self, symbol, side):
        try: # exit position
            positionQty = self.positions[symbol]['qty']
            if ((
                side == 'buy' and
                positionQty < 0
            ) or (
                side == 'sell' and
                positionQty > 0
            )):
                longShort = 'long' if positionQty > 0 else 'short'
                if symbol in self.pendingOrders[longShort]:
                    self.log.debug(f'Pending order to exit {symbol} {longShort}')
                else:
                    self.log.debug(f'Queuing order to exit {symbol} {longShort}')
                    self.queuedOrders[symbol] = {
                        'algo': self,
                        'longShort': longShort,
                        'qty': -positionQty}
        except Exception as e: self.log.exception(e)
        
        try: # enter position
            if ((
                side == 'buy' and
                self.buyPow['long'] > c.minTradeBuyPow
            ) or (
                side == 'sell' and
                self.buyPow['short'] > c.minTradeBuyPow
            )):
                # TODO: replace side w/ longShort
                price = get_limit_price(symbol, side)
                qty = self.get_trade_qty(symbol, side, price)
                if qty:
                    longShort = 'long' if qty > 0 else 'short'
                    if symbol in self.pendingOrders[longShort]:
                        self.log.debug(f'Pending order to enter {symbol} {longShort}')
                    else:
                        self.log.debug(f'Queuing order to enter {symbol} {longShort}')
                        self.queuedOrders[symbol] = {
                            'algo': self,
                            'longShort': longShort,
                            'qty': qty}
                        self.buyPow[longShort] -= abs(qty) * price
        except Exception as e: self.log.exception(e)

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

    def update_equity(self):
        # TODO: add pending orders
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
