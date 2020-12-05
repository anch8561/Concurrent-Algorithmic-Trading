import backtesting.config as c
from algos import init_algos
from indicators import Indicator
from tick_algos import get_limit_price

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import importlib, ta
from datetime import datetime, timedelta
from logging import getLogger
from pytz import timezone
from unittest.mock import patch

log = getLogger()
nyc = timezone('America/New_York')

def get_dates(dates: list) -> tuple:
    # dates: start and stop dates as strings (YY-MM-DD)
    # returns: start and stop dates as datetimes

    fromDate = nyc.localize(datetime.strptime(dates[0], '%Y-%m-%d'))
    toDate = nyc.localize(datetime.strptime(dates[1], '%Y-%m-%d')) + timedelta(1)
    return fromDate, toDate

def get_combined_algo_history(algos: list, dates: list) -> pd.Series:
    # algos: algos to be combined
    # dates: start and stop dates (YYYY-MM-DD)
    # returns: combined growth fractions of algos with date str index

    try: # get growth
        # FIX: night algos start and stop on different days
        df = pd.DataFrame()
        for algo in algos:
            history = sorted(algo.history)
            for date in history:
                if dates[0] <= date and date <= dates[1]:
                    growth = 0
                    startEquity = 0
                    for entry in algo.history[date].values():
                        if entry['event'] == 'start':
                            startEquity = entry['equity']
                        elif entry['event'] == 'stop' and startEquity:
                            stopEquity = entry['equity']
                            growth = (1 + growth) * stopEquity / startEquity - 1
                            startEquity = 0
                    df.loc[date, algo.name] = growth
                elif date > dates[1]: break
    except Exception as e: log.exception(e)
    
    return df.sum(1, min_count=len(algos))

def get_backtest_history(dates: list, backtestName: str, deltaNeutral: bool = True) -> pd.DataFrame:
    # returns: growth fractions of algos with date str index

    # init algos
    c.algoPath = c.resultsPath + backtestName + '/algos/'
    c.logPath = c.resultsPath + backtestName + '/logs/'
    with patch('algos.c', c), patch('algoClass.c', c):
        algos = init_algos(True, None)
    
    # get history
    history = pd.DataFrame()
    if deltaNeutral:
        for algo1 in algos['all']:
            if algo1.name[-5:] == '_long':
                name = algo1.name[:-5]
                for algo2 in algos['all']:
                    if algo2.name == name + '_short':
                        algoHistory = get_combined_algo_history([algo1, algo2], dates)
                        history[name] = algoHistory
                        break
    else:
        for algo in algos['all']:
            algoHistory = get_combined_algo_history([algo], dates)
            history[algo.name] = algoHistory
    return history

def get_combined_backtest_history(dates: list, backtestNames: list, deltaNeutral: bool = True) -> pd.DataFrame:
    # dates: start and stop dates as strings (YY-MM-DD)
    # backtestNames: names of folders where backtests are stored
    # returns: growth fractions of algos with date str index

    # TODO: store all backtests to combine in folder; pass folder name as arg

    history = pd.DataFrame()
    for backtestName in backtestNames:
        backtestHistory = get_backtest_history(dates, backtestName, deltaNeutral)
        history = history.append(backtestHistory)
    return history

def get_metrics(history: pd.DataFrame) -> pd.DataFrame:
    # history: growth fractions
    # returns: performance metrics; {mean, stdev, min, max}

    metrics = pd.DataFrame()
    metrics['mean'] = history.mean()
    metrics['stdev'] = history.std()
    metrics['min'] = history.min()
    metrics['max'] = history.max()
    return metrics

def save_backtest_summary(dates: list, backtestName: str, deltaNeutral: bool = True):
    startDate = datetime.strptime(dates[0], '%Y-%m-%d')
    stopDate = datetime.strptime(dates[1], '%Y-%m-%d')

    with open(c.resultsPath + backtestName + '/results.txt', 'w', ) as f:
        history = get_backtest_history(dates, backtestName)
        metrics = get_metrics(history)

        f.write(dates[0] + ' - ' + dates[1] + '\n')
        f.write(str(metrics) + '\n\n')

        detail = None
        if stopDate - startDate > timedelta(1000): detail = 'year'
        elif stopDate - startDate > timedelta(100): detail = 'month'
        elif stopDate - startDate > timedelta(20): detail = 'week'
        if detail:
            dates = ['', ''] # new dates object
            while startDate < stopDate:
                if detail == 'year':
                    dates[0] = startDate.strftime('%Y-%m-%d') # start on startDate
                    dates[1] = startDate.replace(month=12, day=31) # end on Dec 31
                elif detail == 'month':
                    dates[0] = startDate.strftime('%Y-%m-%d') # start on startDate
                    nextMonth = startDate.replace(day=28) + timedelta(4)
                    dates[1] = nextMonth - timedelta(nextMonth.day) # end on last day of month
                elif detail == 'week':
                    dates[0] = startDate.strftime('%Y-%m-%d') # start on startDate
                    dates[1] = startDate + timedelta(4) - timedelta(startDate.weekday()) # end on friday

                if dates[1] > stopDate: dates[1] = stopDate # end on stopDate
                dates[1] = dates[1].strftime('%Y-%m-%d')

                history = get_backtest_history(dates, backtestName)
                metrics = get_metrics(history)

                f.write(dates[0] + ' - ' + dates[1] + '\n')
                f.write(str(metrics) + '\n\n')

                if detail == 'year':
                    startDate = startDate.replace(year=startDate.year+1, month=1, day=1) # start on Jan 1
                elif detail == 'month':
                    startDate = nextMonth - timedelta(nextMonth.day - 1) # start on first of month
                elif detail == 'week':
                    startDate += timedelta(7) - timedelta(startDate.weekday()) # start on monday

def plot_backtest(backtestName: str, barFreq: str, algoNames: list, symbols: list, dates: list) -> tuple:
    # backtestName: final directory containing backtest (algos and logs folders)
    # barFreq: for plotting price data
    # algoNames: list of algo.name strings
    # symbols: ticker strings
    # dates: start and stop date stings ('YYYY-MM-DD')
    # returns:
    #   figures: dict; {algo: {symbol: {date: figure}}}
    #   barsets: dict; {symbol: DataFrame}

    # TODO: empty list to plot all

    # suppress SettingWithCopyWarning
    pd.set_option('mode.chained_assignment', None)

    # import backtest config
    path = c.resultsPath + backtestName + '/'
    c2 = importlib.import_module(path.replace('/', '.') + 'config')
    c.barPath = path + 'bars/'
    c.logPath = path + 'logs/'

    # get barsets
    barsets = {} # {symbol: DataFrame}
    for symbol in symbols:
        # read csv
        bars = pd.read_csv(c.barPath + f'{barFreq}_{symbol}.csv',
            header=0, index_col=0, parse_dates=True)
        
        # filter to dates
        fromDate, toDate = get_dates(dates)
        bars.index = pd.DatetimeIndex(bars.index).tz_convert(nyc) # pylint: disable=no-member
        bars = bars.loc[fromDate:toDate]

        # save bars
        barsets[symbol] = bars

    # get trades and plot
    figures = {} # {symbol: {date: {algo: figure}}}
    for algoName in algoNames:
        figures[algoName] = {}

        for symbol in symbols:
            figures[algoName][symbol] = {}

            # get trades
            bars = barsets[symbol].copy()
            bars['trades'] = 0
            bars['tradePrice'] = 0
            bars['tradeQty'] = 0
            with open(c.logPath + algoName + '.log') as f, patch('tick_algos.c', c2):
                while True:
                    try: line = next(f)
                    except: break

                    if algoName in line:
                        time = nyc.localize(datetime.strptime(line[21:40], '%Y-%m-%d %H:%M:%S'))
                        if fromDate < time and time < toDate:
                            line = next(f)
                            if 'Filled' in line and symbol in line:
                                fillQty = int(line[14:20])
                                algoQty = int(line[22:28])

                                if algoQty > 0:
                                    bars.loc[time, 'trades'] = 1
                                else:
                                    bars.loc[time, 'trades'] = -1
                                
                                if fillQty:
                                    bars.loc[time, 'trades'] *= 2

                                    fillPrice = float(line.split('@ ')[1])
                                    bars.loc[time, 'tradePrice'] = fillPrice

                                    bars.loc[time, 'tradeQty'] = fillQty

                                else: # limit price
                                    # TODO: use tick_algos.get_limit_price
                                    if time in bars.index:
                                        if algoQty > 0:
                                            prevTime = time - timedelta(minutes=1)
                                            bars.loc[time, 'tradePrice'] = bars.close[prevTime] * (1 + c.limitPriceFrac)
                                        else:
                                            prevTime = time - timedelta(minutes=1)
                                            bars.loc[time, 'tradePrice'] = bars.close[prevTime] * (1 - c.limitPriceFrac)
                                    else:
                                        print(time + ' Trade w/out bar')   
                        elif time > toDate: break
            bars = bars.sort_index() # sort new timestamps

            # plot
            numDays = (toDate - fromDate).days
            for ii in range(numDays):
                # get date range
                start = fromDate + timedelta(ii)
                stop = fromDate + timedelta(ii+1)
                dayData = bars.loc[start:stop]

                # new figure
                fig, axs = plt.subplots(2, sharex=True)
                figures[algoName][symbol][start.strftime('%Y-%m-%d')] = fig

                # plot vwap
                axs[0].plot(dayData.vwap, label='vwap')

                # plot ohlc
                hl_height = dayData.high - dayData.low
                oc_height = abs(dayData.open - dayData.close)
                oc_bottom = dayData[['open', 'close']].min(axis=1)
                up = dayData.open < dayData.close
                down = dayData.open > dayData.close
                axs[0].bar(dayData.index[up],   hl_height[up],   0.0001, dayData.low[up],   color='g')
                axs[0].bar(dayData.index[down], hl_height[down], 0.0001, dayData.low[down], color='r')
                axs[0].bar(dayData.index[up],   oc_height[up],   0.0005, oc_bottom[up],     color='g')
                axs[0].bar(dayData.index[down], oc_height[down], 0.0005, oc_bottom[down],   color='r')

                # plot trades
                try:
                    trades = dayData.tradePrice[dayData.trades == 2]
                    axs[0].plot(trades, 'r^', markersize=9, markeredgecolor='k', label='filled buy')
                except: pass # plot fails if trades series is empty
                try:
                    trades = dayData.tradePrice[dayData.trades == 1]
                    axs[0].plot(trades, 'k^', markersize=9, label='unfilled buy')
                except: pass
                try:
                    trades = dayData.tradePrice[dayData.trades == -1]
                    axs[0].plot(trades, 'kv', markersize=9, label='unfilled sell')
                except: pass
                try:
                    trades = dayData.tradePrice[dayData.trades == -2]
                    axs[0].plot(trades, 'gv', markersize=9, markeredgecolor='k', label='filled sell')
                except: pass

                # profit
                try: profit = -100 / c.buyPow / c.maxPositionFrac * \
                    (dayData.tradePrice[dayData.trades.abs() == 2] * dayData.tradeQty[dayData.trades.abs() == 2]).sum()
                except: profit = None
                
                # plot volume
                axs[1].bar(dayData.index, dayData.volume, 0.0005, label='volume')
                
                # format plot
                axs[0].set_title(f'{algoName}\n{symbol}  |  {start.date()}  |  {profit:.3}%')
                dateFmtr = mdates.DateFormatter('%H:%M', nyc)
                axs[1].xaxis.set_major_formatter(dateFmtr)
                axs[1].tick_params('x', labelrotation=45)
                axs[0].grid(True)
                axs[1].grid(True)
                axs[0].legend()
                axs[1].legend()

    # exit
    return figures, barsets

def plot_indicators(figures: dict, barsets: dict, indicators: list, subplot: int = 0, invisibleIndicators: list = []):
    # figures: {algo: {symbol: {day: figure}}}
    # barsets: {symbol: DataFrame}
    # indicators: indicators to plot
    # subplot: figure.axes index (0: overlay, 1: oscillator)
    # invisibleIndicators: indicator dependencies (not plotted)

    for symbol, bars in barsets.items():
        # add indicator columns
        for indList in (invisibleIndicators, indicators):
            for indicator in indList:
                bars[indicator.name] = None

        # plot
        fromDate = bars.index[0].replace(hour=0, minute=0)
        for algo in figures.keys():
            for ii, date in enumerate(figures[algo][symbol].keys()):
                fig = figures[algo][symbol][date]

                # get date range
                start = fromDate + timedelta(ii)
                stop = fromDate + timedelta(ii+1)
                dayData = bars.loc[start:stop]
                
                # get indicator values
                for iii in range(len(dayData)):
                    for indList in (invisibleIndicators, indicators):
                        for indicator in indList:
                            jjj = dayData.columns.get_loc(indicator.name)
                            dayData.iloc[iii, jjj] = indicator.get(dayData[:iii+1])

                # format plot
                if subplot:
                    fig.axes[subplot].clear()
                    dateFmtr = mdates.DateFormatter('%H:%M', nyc)
                    fig.axes[subplot].xaxis.set_major_formatter(dateFmtr)
                    fig.axes[subplot].tick_params('x', labelrotation=45)
                    fig.axes[subplot].grid(True)

                # plot indicators
                for indicator in indicators:
                    fig.axes[subplot].plot(dayData[indicator.name], linestyle=':', label=indicator.name)
                fig.axes[subplot].legend()
