import backtest.historicBars as histBars
import backtest.timing as timing
import backtest.config as c
import globalVariables as g
import tick_algos
from algoClass import Algo
from algos import init_algos
from backtest.init_assets import init_assets
from credentials import dev
from indicators import init_indicators
from init_logs import init_log_formatter, init_primary_logs
from streaming import process_algo_trade

import alpaca_trade_api, os, sys
import pandas as pd
from argparse import ArgumentParser, RawTextHelpFormatter
from datetime import datetime, timedelta
from logging import getLogger
from pytz import timezone
from unittest.mock import patch

def parse_args(args):
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        '--dates',
        default = ['2004-01-02', '2019-12-31'],
        nargs = 2,
        help = '2 dates since 2004-01-01 (default: 2004-01-02 2019-12-31, must be market days)')
    parser.add_argument(
        '--getAssets',
        action = 'store_true',
        help = 'download historic barsets (default: already downloaded)')
    parser.add_argument(
        '--log',
        choices = ['debug', 'info', 'warn', 'warning', 'error', 'critical'],
        default = c.defaultLogLevel,
        help = f'logging level to display (default: {c.defaultLogLevel})')
    parser.add_argument( # unused
        '--market',
        choices = ['bull', 'bear', 'volatile', 'stagnant', 'rally', 'crash', 'black swan'],
        help =
            'bull:       10 day SMA > 20 day SMA\n' + \
            'bear:       10 day SMA < 20 day SMA\n' + \
            'volatile:   weeks with stdev (from 5 day SMA) > 1%%\n' + \
            'stagnant:   weeks with stdev (from 5 day SMA) < 1%%\n' + \
            'rally:      weeks with gains over 5%%\n' + \
            'crash:      weeks with drops over 5%%\n' + \
            'black swan: days with deltas over 5%%\n') # estimates subject to change
    parser.add_argument(
        '--numAssets',
        default = c.numAssets,
        type = int,
        help = f'number of tickers to use (default: {c.numAssets}, -1 means all)')
    return parser.parse_args(args)

def get_day_bars(indicators: dict):
    timestamp = timing.get_calendar_date(calendar, dateIdx)
    histBars.get_next_bars('day', timestamp, barGens, indicators, g.assets)

def get_trade_fill(symbol: str, algo: Algo) -> (int, float):
    # returns: qty, fillPrice
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

def process_trades(allAlgos: list):
    for algo in allAlgos:
        algo.pendingOrders = algo.queuedOrders
        algo.queuedOrder = {}
        # FIX: short enter algo price is NOT limit price
        for symbol in algo.pendingOrders:
            fillQty, fillPrice = get_trade_fill(symbol, algo)
            process_algo_trade(symbol, algo, fillQty, fillPrice)

if __name__ == '__main__':
    # parse arguments
    args = parse_args(sys.argv[1:])

    # create backtest dir if needed
    try: os.mkdir('backtest')
    except Exception: pass

    # init logs
    logFmtr = init_log_formatter()
    init_primary_logs(args.log, 'backtest', logFmtr)
    log = getLogger('backtest')

    # init indicators and algos
    indicators = init_indicators()
    algos = init_algos(False, logFmtr)
    for algo in algos['all']: algo.buyPow = c.buyPow

    # init alpaca and timing
    alpaca = alpaca_trade_api.REST(*dev.paper)
    calendar = alpaca.get_calendar()
    dateStr = args.dates[0]
    dateIdx = timing.get_calendar_index(calendar, dateStr)
    state = 'night'

    # init assets and "streaming"
    init_assets(alpaca, calendar, algos['all'], indicators,
        args.getAssets, args.numAssets, args.dates)
    barGens = histBars.init_bar_gens(['min', 'day'], g.assets['day'])

    # main loops
    with patch('algoClass.get_time_str', lambda: timing.get_time_str(g)), \
    patch('algoClass.get_date', lambda: timing.get_assets_date(g)), \
    patch('globalVariables.alpaca'), \
    patch('globalVariables.lock'), \
    patch('tick_algos.c', c), \
    patch('tick_algos.log', log), \
    patch('tick_algos.streaming.compile_day_bars', get_day_bars), \
    patch('tick_algos.process_queued_orders', process_trades):
        # multiday loop
        while dateStr <= args.dates[1]:
            # update time
            g.now = timing.get_market_open(calendar, dateIdx)
            g.now, g.TTOpen, g.TTClose = timing.update_time(g.now, calendar, dateIdx)

            # intraday loop
            while g.TTClose > timedelta(0):
                histBars.get_next_bars('min', g.now, barGens, indicators, g.assets)
                process_trades(algos['all'])
                state = tick_algos.tick_algos(algos, indicators, state)
                g.now, g.TTOpen, g.TTClose = timing.update_time(g.now, calendar, dateIdx)

            # update date
            dateIdx += 1
            dateStr = calendar[dateIdx]._raw['date']

            # clear min bars
            for bars in g.assets['min'].values():
                bars = bars[0:0] # FIX: iloc[-1] error