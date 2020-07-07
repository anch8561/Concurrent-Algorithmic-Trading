import alpacaAPI, g
from config import maxPosFrac, limitPriceFrac, minLongPrice, minShortPrice, minTradeBuyPow
from timing import get_timestamp, get_date
from warn import warn
import os
import json
import pandas as pd
import statistics as stats

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
        self.active = True # if algo has open positions or needs its metrics updated
        self.buyPow = {'long': 0, 'short': 0} # updated continuously
        self.equity = {'long': 0, 'short': 0} # updated daily
        self.positions = {} # {symbol: {qty, basis}}
        self.orders = {} # {orderID: {symbol, qty, limit, longShort}}
        # qty is positive for buy/long and negative for sell/short

        # risk and performance metrics
        self.history = pd.DataFrame()
        self.mean = {'long': 0, 'short': 0} # average daily growth
        self.stdev = {'long': 0, 'short': 0} # sample standard deviation of daily growth
        self.allocFrac = 0
        self.longShortFrac = 0.5 # float; 0 is all shorts; 1 is all longs

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

    def start(self):
        self.update_equity()
        self.update_history('start')
        self.save_data()
        self.active = True
    
    def stop(self):
        self.update_equity()
        self.update_history('stop')
        self.save_data()
        self.active = False

    def update_equity(self):
        # check orders
        if len(self.orders):
            warn(f'{self.name} cannot update equity with open orders')
            return

        # copy buying power
        self.Equity = self.buyPow.copy()

        # check positions
        for position in self.positions:
            qty = position['qty']
            if qty:
                # warn about position
                symbol = position['symbol']
                warn(f'{self.name} still holding {qty} shares of {symbol}')

                # get position value
                price = self.get_price(symbol)
                longShort = 'long' if qty > 0 else 'short'
                self.equity[longShort] += price * abs(qty)

    def update_history(self, event):
        # event: 'start' or 'stop'

        index = pd.MultiIndex.from_arrays(
            [[get_date()], [get_timestamp()]],
            names=['date', 'timestamp'])
        
        snapshot = pd.DataFrame(dict(
            date = get_date(),
            timestamp = get_timestamp(),
            event = event,
            live = self.live,
            longEquity = self.equity['long'],
            shortEquity = self.equity['short']
        ), index)

        self.history = self.history.append(snapshot)

    def get_metrics(self, numDays):
        # get dates
        levelVals = self.history.index.get_level_values('date')
        dates = []
        for date in reversed(levelVals):
            if date not in dates:
                dates.append(date)
            if len(dates) == numDays: break

        # get equity growth
        growth = {'long': [], 'short': []}
        for ii, date in enumerate(dates):
            day = self.history.loc[date]
            growth['long'][ii] = 0
            growth['short'][ii] = 0
            for _, row in day.iterrows():
                if row.event == 'start':
                    startEquity = {
                        'long': row.longEquity,
                        'short': row.shortEquity
                    }
                elif row.event == 'stop':
                    stopEquity = {
                        'long': row.longEquity,
                        'short': row.shortEquity
                    }
                    for longShort in ('long', 'short'):
                        growth[longShort][ii] += (1 + growth[longShort][ii]) * \
                            (stopEquity[longShort] - startEquity[longShort]) / startEquity[longShort]
        
        # calculate mean and stdev
        metrics = {'mean': {}, 'stdev': {}}
        for longShort in ('long', 'short'):
            metrics['mean'][longShort] = stats.mean(growth[longShort])
            metrics['stdev'][longShort] = stats.stdev(growth[longShort])
        
        return metrics

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

    def enter_position(self, symbol, side):
        # symbol: e.g. 'AAPL'
        
        if side == 'sell' and not g.assets[symbol]['easyToBorrow']: return

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

    def exit_all_positions(self):
        for symbol, position in self.positions.items():
            if position['qty']:
                self.exit_position(symbol)

    def get_price(self, symbol):
        try:
            return g.assets[symbol]['minBars'].iloc[-1].close # TODO: secBars
        except Exception as e:
            warn(e)
            return 0

    def get_limit_price(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        price = self.get_price(symbol)

        if side == 'buy':
            price *= 1 + limitPriceFrac
        elif side == 'sell':
            price *= 1 - limitPriceFrac
        else: warn(f'{self.name} unknown side "{side}"')

        return price

    def get_trade_qty(self, symbol, side, price, volumeMult=1, barType='minBars'):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'
        # limitPrice: float or None for configured price collar
        # volumeMult: float; volume limit multiplier
        # barType: 'secBars', 'minBars', or 'dayBars'; bar type for checking volume limit
        # returns: int; signed # of shares to trade (positive buy, negative sell)

        # get buying power and equity
        if side == 'buy':
            equity = self.equity['long']
            buyPow = self.buyPow['long']
        elif side == 'sell':
            equity = self.equity['short']
            buyPow = self.buyPow['short']

        # check price
        if side == 'buy' and price < minLongPrice:
            print(f'{self.name}\t{symbol}\tshare price < {minLongPrice}')
            return 0
        elif side == 'sell' and price < minShortPrice:
            print(f'{self.name}\t{symbol}\tshare price < {minShortPrice}')
            return 0

        # set quantity
        qty = int(maxPosFrac * equity / price)
        print(f'{self.name}\t{symbol}\tqty: {qty}')

        # check buying power
        if qty * price > buyPow:
            qty = int(buyPow / price)
            print(f'{self.name}\t{symbol}\tbuyPow qty limit: {qty}')
        
        # check volume
        try:
            volume = g.assets[symbol][barType].iloc[-1].volume
        except Exception as e:
            warn(e)
            volume = 0
        if qty > volume * volumeMult:
            qty = volume * volumeMult
            print(f'{self.name}\t{symbol}\tvolume qty limit: {qty}')

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
                    print(f'{self.name}\t{symbol}\tadding {qty} to position of {posQty}')
                else: # position is large enough
                    print(f'{self.name}\t{symbol}\tposition of {posQty} is large enough')
                    return 0
            elif posQty * qty < 0: # opposite side from position
                qty = -posQty # exit position
                print(f'{self.name}\t{symbol}\texiting position of {posQty}')

        # check for existing orders
        for orderID, order in self.orders.items():
            if order['symbol'] == symbol:
                if order['qty'] * qty < 0: # opposite side
                    self.cancel_order(orderID)
                    print(f'{self.name}\t{symbol}\tcancelling opposing order {orderID}')
                else: # same side
                    print(f'{self.name}\t{symbol}\talready placed order for {order["qty"]}')
                    return 0

        # TODO: check risk

        return qty

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
                print(f'{self.name}\t{symbol}\texiting global position of {qty}')
        else:
            allPosQty = 0

        # check allOrders for opposing short
        if qty > 0 and allPosQty == 0: # buying from zero position
            for orderID, order in self.allOrders.items():
                if order['symbol'] == symbol and order['qty'] < 0: # pending short
                    print(f'{self.name}\t{symbol}\topposing global order {orderID}')
                    return

        # get side
        side = 'buy' if qty > 0 else 'sell'

        try:
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
        except Exception as e: print(e)

    def cancel_order(self, orderID):
        self.alpaca.cancel_order(orderID)
        self.orders.pop(orderID)
        self.allOrders.pop(orderID)

    def save_data(self):
        # get data
        data = {}
        for field in self.dataFields:
            data[field] = self.__getattribute__(field)
        
        # write data
        fileName = self.name + '.data'
        if os.path.exists(fileName):
            with open(fileName, 'w') as f:
                try:
                    json.dump(data, f)
                    f.close()
                except Exception as e:
                    print(e)

    def load_data(self):
        # read data
        fileName = self.name + '.data'
        if os.path.exists(fileName):
            with open(fileName, 'r') as f:
                try:
                    data = json.load(f)
                    f.close()
                except Exception as e:
                    print(e)
             
            # set data
            for field in self.dataFields:
                self.__setattr__(field, data[field])  

class NightAlgo(Algo):
    def tick(self):
        if sum(self.buyPow.values()) > 2 * minTradeBuyPow:
            self.func(self)

class DayAlgo(Algo):
    def tick(self):
        self.func(self)
