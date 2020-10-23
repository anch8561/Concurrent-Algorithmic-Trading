import backtest.historicBars as histBars
import backtest.backtestTiming as timing
import config as c
import globalVariables as g
from algoClass import Algo
from algos import init_algos
from credentials import dev
from indicators import init_indicators
from init_logs import init_log_formatter, init_primary_logs
from streaming import process_algo_trade

import alpaca_trade_api, os, shutil, sys
import pandas as pd
from argparse import ArgumentParser, RawTextHelpFormatter
from datetime import datetime, timedelta
from logging import getLogger
from pytz import timezone
from statistics import mean
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

def init_assets(
    alpaca: alpaca_trade_api.REST,
    calendar: list,
    allAlgos: list,
    getAssets: bool,
    numAssets: int,
    dates: (str, str)):

    dayBars = {}
    if getAssets:
        # delete old barsets
        try: shutil.rmtree('backtest/bars')
        except Exception: pass
        os.mkdir('backtest/bars')

        # download day bars and choose assets
        alpacaAssets = alpaca.list_assets('active', 'us_equity')
        for ii, asset in enumerate(alpacaAssets):
            log.info(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}\n' + \
                f'Found {len(dayBars.keys())} / {numAssets}')
            # check leverage (ignore marginability and shortability)
            if not any(x in asset.name.lower() for x in c.leverageStrings):
                try: # check age, price, cash flow, and spread
                    bars = alpaca.polygon.historic_agg_v2(asset.symbol, 1, 'day', *dates).df
                    if (
                        bars.index[0].strftime('%Y-%m-%d') == dates[0] and
                        bars.low[-1] > c.minSharePrice and
                        mean(bars.volume * bars.close) > c.minDayCashFlow and
                        mean((bars.high - bars.low) / bars.low) > c.minDaySpread
                    ):
                        # save day bars
                        dayBars[asset.symbol] = bars
                        bars.to_csv(f'backtest/bars/day_{asset.symbol}.csv')
                except Exception as e:
                    if len(bars.index): log.exception(e)
                    else:  log.debug(e)
            if len(dayBars.keys()) == numAssets: break

        # download min bars
        histBars.get_historic_min_bars(alpaca, calendar, dayBars)
    else:
        # read day bars
        fileNames = os.listdir('backtest/bars')
        for name in fileNames:
            if name[:3] == 'day':
                symbol = name[4:-4]
                dayBars[symbol] = pd.read_csv(f'backtest/bars/{name}',
                    header = 0, index_col = 0, parse_dates = True)
                if len(dayBars.keys()) == numAssets: break

    # add symbols to assets and positions
    for symbol in dayBars:
        for assets in g.assets.values(): # all bar frequencies
            assets[symbol] = pd.DataFrame()
        for algo in allAlgos:
            algo.positions[symbol] = {'qty': 0, 'basis': 0}

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

def process_trades(allAlgos: list):
    for algo in allAlgos:
        algo.pendingOrders = algo.queuedOrders
        algo.queuedOrder = {}
        # FIX: short enter algo price is NOT limit price
        for symbol in algo.pendingOrders:
            fillQty, fillPrice = get_trade_fill(symbol, algo)
            process_algo_trade(symbol, algo, fillQty, fillPrice)

def tick_indicators(indicators: dict):
    for bars in g.assets['min'].values():
        for indicator in indicators:
            jj = bars.columns.get_loc(indicator.name)
            bars.iloc[-1, jj] = indicator.get(bars)

def tick_algos(algos: dict):
    for algo in algos:
        algo.tick()

if __name__ == '__main__':
    # parse arguments
    args = parse_args(sys.argv[1:])

    # create backtest dir if needed
    try: os.mkdir('backtest')
    except Exception: pass

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

    # init alpaca and "timing"
    alpaca = alpaca_trade_api.REST(*dev.paper)
    calendar = alpaca.get_calendar()
    dateIdx = timing.get_calendar_index(calendar, args.dates[0])

    # init assets and "streaming"
    init_assets(alpaca, calendar, algos['all'],
        args.getAssets, args.numAssets, args.dates)
    barGens = histBars.init_bar_gens(['min', 'day'], g.assets['day'])

    # main loops
    with patch('algoClass.get_time_str', timing.get_time_str), \
    patch('algoClass.get_date', lambda: timing.get_assets_date(g.assets)):
        dateStr = args.dates[0]
        while dateStr < args.dates[1]: # multiday loop
            # TODO: reset between days
            date = timing.get_market_open(calendar, dateIdx)
            histBars.get_next_bars('day', date, barGens, g.assets)
            while g.TTClose > timedelta(0): # intraday loop
                histBars.get_next_bars('min', g.now, barGens, g.assets)
                process_trades(algos['all'])
                tick_indicators(indicators)
                tick_algos(algos)
                update_time()
            dateIdx += 1
