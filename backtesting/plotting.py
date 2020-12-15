import backtesting.config as c
from indicators import Indicator
from tick_algos import get_limit_price

import importlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import patch

nyc = timezone('America/New_York')

def plot_backtest(backtestName: str, barFreq: str, algoNames: list, symbols: list, dates: list) -> tuple:
    # backtestName: directory (within results path) where backtest is stored
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
        fromDate = nyc.localize(datetime.strptime(dates[0], '%Y-%m-%d'))
        toDate = nyc.localize(datetime.strptime(dates[1], '%Y-%m-%d')) + timedelta(1)
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
                            if 'filled' in line and symbol in line:
                                # get fill and side
                                fillQty = int(line.split('/ ')[0][-6:])
                                if fillQty:
                                    bars.loc[time, 'tradeQty'] = fillQty
                                    if fillQty > 0:
                                        bars.loc[time, 'trades'] = 2
                                    else:
                                        bars.loc[time, 'trades'] = -2
                                else:
                                    time -= timedelta(minutes=1) # plot when order was submitted, not canceled
                                    algoQty = int(line.split('/ ')[1][:6])
                                    if algoQty > 0:
                                        bars.loc[time, 'trades'] = 1
                                    else:
                                        bars.loc[time, 'trades'] = -1

                                # get price
                                fillPrice = float(line.split('@ ')[1])
                                bars.loc[time, 'tradePrice'] = fillPrice

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
