import backtesting.config as c
import backtesting.historicBars as histBars
import backtesting.results as results
import backtesting.timing as timing
import globalVariables as g
import init_logs
import tick_algos
from algoClass import Algo
from algos import init_algos
from backtesting.init_assets import init_assets
from credentials import dev
from indicators import init_indicators
from streaming import process_algo_trade
from tab import tab

import alpaca_trade_api, logging, os, shutil, sys
import pandas as pd
from argparse import ArgumentParser, RawTextHelpFormatter
from contextlib import ExitStack
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import patch

def parse_args(args):
    parser = ArgumentParser(formatter_class=RawTextHelpFormatter)
    parser.add_argument(
        'dates',
        nargs = 2,
        help = '2 dates since 2004-01-01 (must be market days)')
    parser.add_argument(
        '--name',
        default = '',
        help = 'backtest will be saved in a folder named <timestamp + name> (e.g. 2001-02-03_12:34:56_myBacktest)')
    parser.add_argument(
        '--numAssets',
        default = c.numAssets,
        type = int,
        help = f'number of tickers to use (default: {c.numAssets}, -1 means all)')
    parser.add_argument(
        '--useSavedAssets',
        action = 'store_true',
        help = 'use previously downloaded barsets')
    parser.add_argument(
        '--log',
        choices = ['debug', 'info', 'warn', 'warning', 'error', 'critical'],
        default = c.defaultLogLevel,
        help = f'logging level to display (default: {c.defaultLogLevel})')
    return parser.parse_args(args)

def init_log_formatter():
    def formatDatetime(record, datefmt=None) -> logging.Formatter:
        # pylint: disable=undefined-variable
        ct = datetime.fromtimestamp(record.created, g.nyc)

        if datefmt:
            s = ct.strftime(datefmt)
        else:
            t = ct.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs)
        
        try: s += f' [{str(g.now)[:-6]}]'
        except: pass

        return s

    fmtr = logging.Formatter(
        fmt = f'\n%(asctime)s %(name)s\n%(levelname)s: %(message)s',
        datefmt = '%Y-%m-%d %H:%M:%S')
    fmtr.formatTime = formatDatetime
    return fmtr

def activate(self):
    # pylint: disable=undefined-variable
    self.buyPow = c.buyPow
    self.active = True
    self.start()

def get_day_bars(indicators: dict):
    timestamp = timing.get_calendar_date(calendar, dateIdx)
    histBars.get_next_bars('day', timestamp, barGens, indicators, g.assets)

def get_trade_fill(symbol: str, algo: Algo) -> (int, float):
    # returns: qty, fillPrice
    qty = algo.pendingOrders[symbol]['qty']
    if algo.longShort == 'short' and qty < 0: # short enter price is NOT limit price
        limit = tick_algos.get_limit_price(symbol, 'sell') # FIX: use prev bar
    else:
        limit = algo.pendingOrders[symbol]['price']
    high = g.assets['min'][symbol].high[-1]
    low = g.assets['min'][symbol].low[-1]
    # NOTE: could be prev bar if current bar missing
    if qty > 0: # buy
        if low <= limit:
            return qty, min(high, limit)
    else: # sell
        if limit <= high:
            return qty, max(low, limit)
    return 0, 0

def process_trades(allAlgos: list):
    for algo in allAlgos:
        algo.pendingOrders = algo.queuedOrders # copy reference
        algo.queuedOrders = {} # new reference
        for symbol in algo.pendingOrders:
            fillQty, fillPrice = get_trade_fill(symbol, algo)

            algoQty = algo.pendingOrders[symbol]['qty']
            algo.log.debug(f'Filled {tab(fillQty, 6)}/ {tab(algoQty, 6)}{symbol} @ {fillPrice}')

            process_algo_trade(symbol, algo, fillQty, fillPrice)

if __name__ == '__main__':
    # parse arguments
    args = parse_args(sys.argv[1:])
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    if args.name:
        args.name = timestamp + '_' + args.name
    else:
        args.name = timestamp

    # create backtest dir
    path = c.resultsPath + args.name + '/'
    c.algoPath = path + 'algos/'
    c.barPath = path + 'bars/'
    c.logPath = path + 'logs/'
    try: os.mkdir(c.resultsPath)
    except: pass
    try: os.mkdir(path)
    except: pass
    shutil.copyfile('algoClass.py', path + 'algoClass.py')
    shutil.copyfile('algos.py', path + 'algos.py')
    shutil.copyfile('backtesting/config.py', path + 'config.py')

    # init logs, indicators, and algos
    with patch('algos.c', c), patch('init_logs.c', c): # file paths
        # init logs
        logFmtr = init_log_formatter()
        init_logs.init_primary_logs(args.log, 'backtest', logFmtr)
        logging.getLogger('main').setLevel(30) # warning
        log = logging.getLogger('backtest')
        log.warning(f'Backtesting from {args.dates[0]} to {args.dates[1]}')

        # init algos
        algos = init_algos(False, logFmtr)

        # init indicators
        indicators = init_indicators(algos['all'])

    # init alpaca
    alpaca = alpaca_trade_api.REST(*dev.paper)

    # init timing
    calendar = alpaca.get_calendar()
    dateStr = args.dates[0]
    dateIdx = timing.get_calendar_index(calendar, dateStr)
    if dateIdx == None:
        log.error(f'Start date {dateStr} is not a market day')
        sys.exit()
    state = 'overnight'

    # init assets
    g.assets = init_assets(alpaca, calendar, algos['all'], indicators,
        args.numAssets, args.useSavedAssets, args.dates)

    # init "streaming"
    barGens = histBars.init_bar_gens(['min', 'day'], g.assets['day'])

    # main loops
    with ExitStack() as stack:
        stack.enter_context(patch('algoClass.Algo.activate', activate))
        stack.enter_context(patch('algoClass.get_date', lambda: timing.get_assets_date(g)))
        stack.enter_context(patch('algoClass.get_time_str', lambda: timing.get_time_str(g)))
        stack.enter_context(patch('algoClass.c', c)) # algoPath, minTradeBuyPow, maxPosFrac, stopLossFrac
        stack.enter_context(patch('globalVariables.alpaca'))
        stack.enter_context(patch('globalVariables.lock'))
        stack.enter_context(patch('tick_algos.c', c)) # limitPriceFrac, marketCloseTransitionPeriod
        stack.enter_context(patch('tick_algos.streaming.compile_day_bars', get_day_bars))
        stack.enter_context(patch('tick_algos.process_queued_orders', process_trades))

        # multiday loop
        while dateStr <= args.dates[1]:
            # start 1 min after open
            g.now = timing.get_market_open(calendar, dateIdx)
            histBars.get_next_bars('min', g.now, barGens, indicators, g.assets)
            g.now, g.TTOpen, g.TTClose = timing.update_time(g.now, calendar, dateIdx)

            # intraday loop
            while g.TTClose > timedelta(0):
                # print hourly progress
                if g.now.minute == 0: log.info(f'Progress update')

                # tick algos
                state = tick_algos.tick_algos(algos, indicators, state)

                # update time
                g.now, g.TTOpen, g.TTClose = timing.update_time(g.now, calendar, dateIdx)

                # get next bars
                barTimestamp = g.now - timedelta(minutes=1)
                histBars.get_next_bars('min', barTimestamp, barGens, indicators, g.assets)

            # update date
            dateIdx += 1
            dateStr = calendar[dateIdx]._raw['date']

            # clear min bars
            for symbol, bars in g.assets['min'].items():
                g.assets['min'][symbol] = bars.drop(bars.index[1:])
    
    # results
    results.save_backtest_summary(args.dates, args.name)
