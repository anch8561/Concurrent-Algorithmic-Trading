import credentials
import globalVariables as g
import main
import timing

import alpaca_trade_api, sys
from argparse import ArgumentParser
from datetime import datetime
from unittest.mock import patch

# pick dates or type (bull, bear, volatile, etc)
# record performance each day & stats about day (summary)

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
        help = '') # max range?
    parser.add_argument(
        '--market',
        choices = ['bull', 'bear', 'volatile']
        help = '')
    return parser.parse_args(args)

def get_historic_bars(symbols, fromDate, toDate):
    for symbol in symbols:
        realAlpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate)
        # 3000 minutes
        # 1 day = 400 minutes
        # 1 week = 2000 minues
        # extended hours?

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