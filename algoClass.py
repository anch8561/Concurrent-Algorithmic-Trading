import config as c
import globalVariables as g
from tab import tab
from tick_algos import get_price, get_limit_price
from timing import get_time_str, get_date

import json
import statistics as stats
from alpaca_trade_api.rest import APIError
from logging import getLogger
from types import FunctionType

class Algo:
    def __init__(self, barFreq: str, func: FunctionType, longShort: str, loadData: bool, **kwargs):
        self.barFreq = barFreq # 'sec', 'min', or 'day'; size of market data aggregates used
        self.func = func # function to determine when to buy and sell
        self.longShort = longShort # 'long' or 'short'; algo equity type

        # kwargs, name, and log
        self.name = ''
        for key, val in kwargs.items():
            self.__setattr__(key, val)
            self.name += str(val) + '_'
        self.name += barFreq + '_' + self.func.__name__ + '_' + longShort
        self.log = getLogger(self.name)

        # input validation
        if longShort not in ('long', 'short'):
            self.log.critical(f'Unknown longShort {longShort}')
        if barFreq not in g.assets:
            self.log.critical(f'Unknown barFreq {barFreq}')

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
            fileName = c.algoPath + self.name + '.json'
            with open(fileName, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e: self.log.exception(e)

    def load_data(self):
        try: # read data
            fileName = c.algoPath + self.name + '.json'
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

    def update_history(self, event: str):
        # event: 'start' or 'stop'

        if event not in ('start', 'stop'):
            self.log.error(f'Unknown event {event}')
            return

        date = get_date()
        if date not in self.history:
            self.history[date] = {}
        self.history[date][get_time_str()] = {
            'event': event,
            'equity': self.equity}
    
    def get_metrics(self, numDays: int) -> dict:
        # numDays: positive number of past days to evaluate
        # returns: {mean, stdev}
        
        try: # get growth # FIX: night algos start and stop on different days
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
            if len(growth): self.log.exception(e)
            else:
                self.log.debug(e)
                self.log.info('No performance data')
        
        try: # get stdev
            metrics['stdev'] = stats.stdev(growth)
        except Exception as e:
            if len(growth) < 2: self.log.debug(e)
            else: self.log.exception(e)
        
        return metrics
    
    def get_trade_qty(self, symbol: str, side: str, price: float) -> int:
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # price: limit price
        # returns: signed # of shares to trade

        if side not in ('buy', 'sell'):
            self.log.error(f'Unknown side {side}')
            return 0
        
        if price == None: return 0

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
            self.log.debug(tab(symbol, 6) + f'{reason} qty limit: {qty}')
        except Exception as e:
            self.log.exception(e); return 0

        try: # check for position
            position = self.positions[symbol]['qty']
            if abs(position) < abs(qty): # position smaller than order
                qty -= position # add to position
                self.log.debug(tab(symbol, 6) + 'Have ' + tab(position, 6) + 'Ordering ' + qty)
            else: # position large enough
                self.log.debug(tab(symbol, 6) + f'position of {position} is large enough')
                return 0
        except Exception as e:
            self.log.exception(e); return 0

        # TODO: check risk

        return qty

    def queue_order(self, symbol: str, side: str):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        if side not in ('buy', 'sell'):
            self.log.error(f'Unknown side {side}')
            return

        try: # exit position
            position = self.positions[symbol]['qty']
            if (
                side == 'buy' and
                position < 0 # short algo
            ) or (
                side == 'sell' and
                position > 0 # long algo
            ):
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
                    price = get_price(symbol) # possibly None
                    price = round(price * 1.03, 2)
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
            if price == None:
                self.log.debug(e)
            else:
                self.log.exception(e)

    def exit_position(self, symbol: str):
        # symbol: e.g. 'AAPL'
        side = 'sell' if self.longShort == 'long' else 'buy'
        self.queue_order(symbol, side)

    def tick(self):
        try: self.func(self)
        except Exception as e: self.log.exception(e)
