import config as c
import globalVariables as g
from algoClass import Algo
from algos import init_algos
from credentials import dev
from indicators import init_indicators
from init_logs import init_log_formatter, init_primary_logs
from streaming import process_algo_trade

import alpaca_trade_api, sys
from argparse import ArgumentParser
from datetime import datetime
from logging import getLogger
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
    args = parse_args(sys.argv[1:])

    # update paths
    c.logPath = 'backtest/' + c.logPath
    c.algoPath = 'backtest/' + c.algoPath

    # init logs
    logFmtr = init_log_formatter()
    init_primary_logs(args.log, 'backtest', logFmtr)
    log = getLogger('backtest')

    # init indicators and algos
    indicators = init_indicators()
    algos = init_algos(False, logFmtr)
    for algo in algos['all']: algo.buyPow = 1e5

    # init assets and "streaming"
    bars = get_historic_bars(symbols, fromDate, toDate) # TODO: figure out these args

    # main loop
    with patch('algoClass.get_time_str', get_time_str), \
    patch('algoClass.get_date', get_date):
        while True:
            # reset between days
            get_next_bars()
            process_trades()
            tick_indicators(indicators)
            tick_algos(algos)


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
    alpaca = alpaca_trade_api.REST(*dev.paper)
    while fromDate < toDate:
        for symbol in symbols:
            bars[symbol] = DataFrame()
            newBars = alpaca.polygon.historic_agg_v2('AAPL', 1, 'minute', fromDate, toDate)
            newBars = newBars.df.iloc[:5000] # remove extra toDate data
            bars[symbol] = bars[symbol].append(newBars).drop_duplicates()
            # TODO: drop extended hours
            # TODO: replace drop_duplicates
        fromDate = bars[symbols[0]].index[-1]
    # bars.to_csv('test.txt')

def get_time_str(): pass

def get_date(): pass

def get_next_bars(): pass

def get_trade_fill(symbol: str, algo: Algo) -> (int, float):
    qty = algo.pendingOrders[symbol]['qty']
    limit = algo.pendingOrders[symbol]['price']
    high = g.assets[symbol].high[-1]
    low = g.assets[symbol].low[-1]
    if qty > 0: # buy
        if low <= limit:
            return qty, min(high, limit)
    else: # sell
        if limit <= high:
            return qty, max(low, limit)
    return 0, 0

def process_trades(algos):
    for algo in algos:
        algo.pendingOrders = algo.queuedOrders
        algo.queuedOrder = {}
        # FIX: short enter algo price is NOT limit price
        for symbol in algo.pendingOrders:
            fillQty, fillPrice = get_trade_fill(symbol, algo)
            process_algo_trade(symbol, algo, fillQty, fillPrice)

def tick_indicators(indicators):
    for indicator in indicators:
        jj = bars.columns.get_loc(indicator.name)
        bars.iloc[-1, jj] = indicator.get(bars)

def tick_algos(algos):
    for algo in algos:
        algo.tick()
