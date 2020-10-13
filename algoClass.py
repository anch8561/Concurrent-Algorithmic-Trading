import config as c
import globalVariables as g
from tick_algos import get_price, get_limit_price
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
    def __init__(self, func, longShort, loadData=True, **kwargs):
        self.func = func # function to determine when to buy and sell
        self.longShort = longShort # 'long' or 'short'; algo equity type

        # kwargs, name, and log
        self.name = ''
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += self.func.__name__ + '_' + longShort
        self.log = getLogger(self.name)

        # state variables
        self.active = True # whether algo might have open positions
        self.buyPow = 0 # updated continuously
        self.equity = 0 # updated daily
        self.positions = {} # {symbol: {qty, buyPow}}
        self.pendingOrders = {} # {symbol: {qty, price}}
        self.queuedOrders = {} # {symbol: {qty, price}}
        self.history = {} # {date: {time: event, equity}}

        # attributes to save / load
        self.dataFields = [
            'buyPow',
            'equity',
            'positions',
            'pendingOrders',
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
                self.exit_position(symbol)
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

    def update_equity(self):
        # TODO: add pending orders
        # copy buying power
        self.equity = self.buyPow

        # check positions
        for symbol, position in self.positions.items():
            positionQty = position['qty']
            if positionQty: # get position value
                price = get_price(symbol)
                try: self.equity += price * abs(positionQty)
                except Exception as e:
                    if price == None: # exit position of unknown value
                        self.log.warning(f'Exiting untracked position: {positionQty} {symbol}')
                        self.exit_position(symbol)

                        price = g.alpaca.get_last_trade(symbol).price
                        self.log.warning(f'Adding estimated value to equity: ${price * abs(positionQty)}')
                        self.equity += price * abs(positionQty)
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
    
    def get_metrics(self, numDays):
        try: # get growth # FIX: overnight algos start and stop on different days
            growth = []
            dates = sorted(self.history, reverse=True)
            for ii, date in enumerate(dates[:numDays]):
                growth.append(0)
                startEquity = 0
                for entry in self.history[date].values():
                    if entry['event'] == 'start':
                        startEquity = entry['equity']
                    elif entry['event'] == 'stop' and startEquity:
                        stopEquity = entry['equity']
                        try:
                            growth[ii] += (1 + growth[ii]) * \
                                (stopEquity - startEquity) / startEquity
                        except Exception as e:
                            if startEquity != 0: self.log.exception(e)
                        startEquity = {}
        except Exception as e: self.log.exception(e)
        
        metrics = {'mean': None, 'stdev': None}

        try: # get mean
            metrics['mean'] = stats.mean(growth)
        except Exception as e:
            self.log.exception(e)
        
        try: # get stdev
            metrics['stdev'] = stats.stdev(growth)
        except Exception as e:
            self.log.exception(e)
        
        return metrics
    
    def get_trade_qty(self, symbol, side, price):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # price: float; limit price
        # returns: int; signed # of shares to trade

        try: # max position
            qty = int(c.maxPositionFrac * self.equity / price)
            reason = 'max position'
        except Exception as e:
            self.log.exception(e); return 0

        try: # check buying power
            # TODO: shorts use max(limit, price*1.03) (must track for fills)
            if qty * price > self.buyPow:
                qty = int(self.buyPow / price)
                reason = 'buying power'
        except Exception as e:
            self.log.exception(e); return 0

        try: # set sell quantity negative
            if side == 'sell': qty *= -1
            self.log.debug(f'{symbol}\t{reason} qty limit: {qty}')
        except Exception as e:
            self.log.exception(e); return 0

        try: # check for position
            position = self.positions[symbol]['qty']
            if abs(position) < abs(qty): # position smaller than order
                qty -= position # add to position
                self.log.debug(f'{symbol}\tadding {qty} to position of {position}')
            else: # position large enough
                self.log.debug(f'{symbol}\tposition of {position} is large enough')
                return 0
        except Exception as e:
            self.log.exception(e); return 0

        # TODO: check risk

        return qty

    def queue_order(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        try: # exit position
            position = self.positions[symbol]['qty']
            if ((
                side == 'buy' and
                position < 0 # short algo
            ) or (
                side == 'sell' and
                position > 0 # long algo
            )):
                if symbol in self.pendingOrders:
                    self.log.debug(f'Pending order to exit {symbol}')
                else:
                    self.log.debug(f'Queuing order to exit {symbol}')
                    self.queuedOrders[symbol] = {
                        'qty': -position,
                        'price': get_limit_price(symbol, side)}
        except Exception as e: self.log.exception(e)
        
        try: # enter position
            if self.buyPow > c.minTradeBuyPow and (
                side == 'buy' and
                self.longShort == 'long'
            ) or (
                side == 'sell' and
                self.longShort == 'short'
            ):
                # get qty
                if side == 'sell':
                    price = get_price(symbol) * 1.03
                else:
                    price = get_limit_price(symbol, side)
                qty = self.get_trade_qty(symbol, side, price)
                if qty == 0: return

                # queue order
                if symbol in self.pendingOrders:
                    self.log.debug(f'Pending order to enter {symbol}')
                else:
                    self.log.debug(f'Queuing order to enter {symbol}')
                    self.queuedOrders[symbol] = {
                        'qty': qty,
                        'price': price}
                    self.buyPow -= abs(qty) * price
        except Exception as e:
            self.log.exception(e)

    def exit_position(self, symbol):
        # symbol: e.g. 'AAPL'
        side = 'sell' if self.longShort == 'long' else 'buy'
        self.queue_order(symbol, side)

    def tick(self):
        try: self.func(self)
        except Exception as e: self.log.exception(e)
