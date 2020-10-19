import config as c
import globalVariables as g
from algoClass import Algo
from algos import init_algos
from credentials import dev
from indicators import init_indicators
from init_logs import init_log_formatter, init_primary_logs
from streaming import process_algo_trade

import alpaca_trade_api, os, sys
from argparse import ArgumentParser
from datetime import datetime
from logging import getLogger
from pandas import DataFrame
from pytz import timezone
from unittest.mock import patch

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

    # init assets and "streaming"
    allSymbols = get_symbols()
    get_historic_bars(symbols, fromDate, toDate) # TODO: figure out these args

    # multiday loop
    with patch('algoClass.get_time_str', get_time_str), \
    patch('algoClass.get_date', get_date):
        while True:
            init_assets()
            while True:
                # TODO: reset between days
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

def get_symbols() -> list:
    # NOTE: uses alpaca global
    symbols = []
    alpacaAssets = alpaca.list_assets('active', 'us_equity')
    polygonTickers = alpaca.polygon.all_tickers()
    for asset in alpacaAssets:
        # check leverage (ignore marginability and shortability)
        if not any(x in asset.name.lower() for x in c.leverageStrings):
            for ticker in polygonTickers:
                if ticker.ticker == asset.symbol:
                    # ignore price, cash flow, and spread
                    symbols.append(asset.symbol)
                    break
    return symbols

def init_assets(symbols: list):
    for symbol in symbols:
        # TODO: check price, cash flow, and spread
        pass

def get_historic_bars(symbols: list, fromDateStr: str, toDateStr: str):
    # symbols: list of str
    # fromDate: e.g. '2004-01-01'
    # toDate: e.g. 2020-01-01'
    # saves csv for each symbol w/ bars from date range
    # NOTE: uses alpaca and log globals

    log.warning('Getting historic bars')

    # create bars dir if needed
    try: os.mkdir('backtest/bars')
    except Exception: pass

    # check date bounds
    if fromDateStr < '2004':
        log.error('No historic bars before 2004')
        return
    if toDateStr >= datetime.now(g.nyc).strftime('%Y-%m-%d'):
        log.error('No historic bars after yesterday')
        return

    # convert dates to market dates (inf loop if toDate not market day)
    # also allows for partial dates (e.g. '2005' -> '2005-01-01')
    calendar = alpaca.get_calendar()
    for ii, date in enumerate(calendar): # get fromDateStr or next market day
        if date._raw['date'] >= fromDateStr:
            fromDateStr = date._raw['date']
            i_fromDate = ii
            break
    for ii, date in enumerate(reversed(calendar)): # get toDateStr or prev market day
        if date._raw['date'] <= toDateStr:
            toDateStr = date._raw['date']
            i_toDate = ii
            break

    # get toDate as datetime
    toDate = g.nyc.localize(datetime.strptime(toDateStr, '%Y-%m-%d'))

    # get bars
    for ii, symbol in enumerate(symbols):
        log.info(f'Downloading asset {ii+1} / {len(symbols)}\t{symbol}')

        # reset fromDate
        fromDate = g.nyc.localize(datetime.strptime(fromDateStr, '%Y-%m-%d'))

        # get day bars
        # NOTE: will not work with start dates over 20 yrs ago
        dayBars = alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
        dayBars.to_csv(f'backtest/bars/{symbol}_day.csv')

        # get minute bars
        fromDate = dayBars.index[0]
        while fromDate < toDate:
            newBars = alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate)
            newBars = newBars.df.iloc[:5000] # remove extra toDate data
            try:
                newBars = newBars[minBars.index[-1]:][1:] # remove overlap
                minBars = minBars.append(newBars)
            except:
                minBars = newBars
            fromDate = minBars.index[-1]
            # TODO: drop extended hours
        minBars.to_csv(f'backtest/bars/{symbol}_min.csv')

def get_time_str(): pass

def get_date(): pass

def get_next_bars(symbols):
    for symbol in symbols:
        bars = DataFrame.from_csv(f'historic_bars/{symbol}.csv')

def get_next_bar(symbol):
    with open(f'historic_bars/{symbol}.csv') as bars:
        for bar in bars:
            yield bar

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
