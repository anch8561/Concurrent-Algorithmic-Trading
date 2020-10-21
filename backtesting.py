import backtest.historicBars as histBars
import config as c
import globalVariables as g
from algoClass import Algo
from algos import init_algos
from credentials import dev
from indicators import init_indicators
from init_logs import init_log_formatter, init_primary_logs
from streaming import process_algo_trade

import alpaca_trade_api, os, sys
import pandas as pd
from argparse import ArgumentParser
from datetime import datetime
from logging import getLogger
from pytz import timezone
from unittest.mock import patch

def parse_args(args):
    parser = ArgumentParser()
    parser.add_argument(
        'dates',
        default = [2004, 2020],
        nargs = 2,
        help = 'e.g. 2004-01-01 (earliest date)')
    parser.add_argument(
        '--log',
        choices = ['debug', 'info', 'warn', 'warning', 'error', 'critical'],
        default = c.defaultLogLevel,
        help = f'logging level to display (default {c.defaultLogLevel})')
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
    parser.add_argument(
        '--numAssets',
        default = c.numAssets,
        type = int,
        help = f'number of symbols to stream (default {c.numAssets}, -1 means all)')
    return parser.parse_args(args) 

def init_assets(
    alpaca: alpaca_trade_api.REST,
    calendar: list,
    allAlgos: list,
    numAssets: int,
    dates: (str, str)):

    # create bars dir if needed
    try: os.mkdir('backtest/bars')
    except Exception: pass

    # get symbols and day bars
    symbols = []
    dayBars = {}
    alpacaAssets = alpaca.list_assets('active', 'us_equity')
    for ii, asset in enumerate(alpacaAssets):
        log.info(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}')
        # check leverage (ignore marginability and shortability)
        if not any(x in asset.name.lower() for x in c.leverageStrings):
            try: # check price, cash flow, and spread
                bars = alpaca.polygon.historic_agg_v2(asset.symbol, 1, 'day', *dates).df
                if (
                    all(bars.low > c.minSharePrice) and
                    all(bars.volume * bars.close > c.minDayCashFlow) and
                    all((bars.high - bars.low) / bars.low > c.minDaySpread)
                ):
                    # save day bars
                    dayBars[asset.symbol] = bars
                    bars.to_csv(f'backtest/bars/day_{asset.symbol}.csv')
            except Exception as e: log.exception(e)
        if len(symbols) == numAssets: break

    # get min bars
    histBars.get_historic_min_bars(alpaca, calendar, dayBars)

    # add symbols to assets and positions
    for symbol in dayBars:
        for assets in g.assets.values(): # all bar frequencies
            assets[symbol] = pd.DataFrame()
        for algo in allAlgos:
            algo.positions[symbol] = {'qty': 0, 'basis': 0}

def get_time_str(assets: dict):
    symbol = list(assets.keys())[0]
    return assets['day'][symbol].index[-1].strftime('%H:%M:%S.%f')

def get_date(assets: dict) -> str:
    symbol = list(assets.keys())[0]
    return assets['day'][symbol].index[-1].strftime('%Y-%m-%d')

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
    for ii, date in enumerate(calendar):
        if date._raw['date'] >= args.dates[0]: # current or next market day
            todayIdx = ii
            break

    # init assets and "streaming"
    symbols = get_symbols(args.numAssets)
    assets = init_assets(symbols)
    barGens = histBars.init_bar_gens(['min', 'day'], symbols)

    # main loops
    with patch('algoClass.get_time_str', get_time_str), \
    patch('algoClass.get_date', get_date):
        while True: # multiday loop
            new_day(args.numAssets)
            while True: # intraday loop
                # TODO: reset between days
                histBars.get_next_bars('min', assets, barGens)
                process_trades(algos['all'])
                tick_indicators(indicators)
                tick_algos(algos)
