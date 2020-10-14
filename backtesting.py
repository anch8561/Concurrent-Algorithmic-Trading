import credentials
import globalVariables as g
import main
import timing

import alpaca_trade_api, sys
from argparse import ArgumentParser
from datetime import datetime
from pandas import DataFrame
from pytz import timezone
from unittest.mock import patch

# test individual algos and/or whole system

# record performance each day & stats about day (summary)

# events (https://en.wikipedia.org/wiki/List_of_stock_market_crashes_and_bear_markets)

# detect on major indices (and/or individual stocks)
# bull / bear (MAX), volatile / stagnant (?), crash (?), black swan (daily high-low spread)

# bear markets
# 2007-10-11 to 2009-03
# 2008-09-16 to ?
# 2011-05-02 to 2011-10-04
# 2015-08-18 to 2015-08-21
# 2018-09-20 to 2018-12-24
# 2020-02-24 to 2020-03-23

# black swan
# 2010-05-06

if __name__ == '__main__':
    # parse arguments
    parse_args(sys.argv[1:])

    # init backtest logs

    # init / patch alpaca and timing
    realAlpaca = alpaca_trade_api.REST(*credentials.dev.paper)

    # init algos

    # init indicators and assets

    # main loop (including "streaming")



def parse_args(args):
    parser = ArgumentParser()
    parser.add_argument(
        '--dates',
        nargs = 2,
        help = 'e.g. 2004-01-01 (earliest date)')
    parser.add_argument(
        '--market',
        choices = ['bull', 'bear', 'volatile', 'stagnant', 'rally', 'crash', 'black swan'],
        help = 'bull: 10 day SMA > 20 day SMA\n' + \
            'bear: 10 day SMA < 20 day SMA\n' + \
            'volatile: weeks with stdev (from 5 day SMA) > 1%\n' + \
            'stagnant: weeks with stdev (from 5 day SMA) < 1%\n' + \
            'rally: weeks with gains over 5%\n' + \
            'crash: weeks with drops over 5%\n' + \
            'black swan: days with deltas over 5%\n') # estimates subject to change
    return parser.parse_args(args)




def get_historic_bars(symbols, fromDate, toDate):
    # symbols: list of str
    # fromDate: str; e.g. '2004-01-01'
    # toDate: str; e.g. 2020-01-01'

    fromDate = g.nyc.localize(datetime.strptime(fromDate, '%Y-%m-%d'))
    toDate = g.nyc.localize(datetime.strptime(toDate, '%Y-%m-%d'))

    bars = {}
    while fromDate < toDate:
        for symbol in symbols:
            bars[symbol] = DataFrame()
            newBars = alpaca.polygon.historic_agg_v2('AAPL', 1, 'minute', fromDate, toDate)
            newBars = newBars.df.iloc[:5000] # remove extra toDate data
            bars[symbol] = bars[symbol].append(newBars).drop_duplicates()
            # TODO: drop extended hours
        fromDate = bars[symbols[0]].index[-1]
    # bars.to_csv('test.txt')

def get_next_minute_bars(): pass

def process_trades(): pass

# patching main and streaming is inefficient (not worth less code)
# elements of main:
# initialize everything (daily vs once?)
# get bars, tick algos, process trades

class Alpaca:
    def __init__(self):
        self.calendar = realAlpaca.get_calendar()
        self.order_id = 0
        self.orders = {}

    def cancel_order(self, order_id):
        # NOTE: may not need it
        self.orders.pop(order_id)

    def get_calendar(self):
        return self.calendar

    def get_last_trade(self, symbol):
        # NOTE: may not need it
        class trade:
            price = 0 # TODO: get price
        return trade
    
    def submit_order(self, symbol, qty, side, type, time_in_force, limit_price):
        self.order_id += 1
        self.orders[self.order_id] = {
            'symbol': symbol,
            'qty': qty,
            'side': side,
            'type': type,
            'time_in_force': time_in_force,
            'limit_price': limit_price}
        return self.order_id


# patch streaming.py (not streamconn)

class datetimeOverride(datetime):
    def set_time(self, time):
        self.time = g.nyc.localize(datetime(1996, 2, 13, 12, 34, 56))
    def now(self, tz):
        return self.time

class streamingOverride:
    def stream(conn, allAlgos, indicators):


# run main each day in calendar
datetimeOverride.set_time(startDate)

i_today += 1
time = 
datetimeOverride.set_time(time)
with patch('main.timing.datetime', datetimeOverride), \
    patch('main.streaming', streamingOverride):
    main()


time = timing.get_market_open()
datetime_override.set_time(time)