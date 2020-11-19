import backtesting.config as c
from algos import init_algos
from indicators import Indicator
from tick_algos import get_limit_price

import matplotlib.pyplot as plt
import pandas as pd
import importlib, ta
from datetime import datetime, timedelta
from logging import getLogger
from pytz import timezone
from unittest.mock import patch

log = getLogger()
nyc = timezone('America/New_York')

def get_dates(dates):
    fromDate = nyc.localize(datetime.strptime(dates[0], '%Y-%m-%d'))
    toDate = nyc.localize(datetime.strptime(dates[1], '%Y-%m-%d')) + timedelta(1)
    return fromDate, toDate

def get_combined_metrics(algos: list, dates: list) -> dict:
    # algos: algos to be combined
    # dates: start and end dates (YYYY-MM-DD)
    # returns: summary of daily performance of combined algos; {mean, stdev, min, max}

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
                            try:
                                growth = (1 + growth) * stopEquity / startEquity - 1
                            except Exception as e:
                                if startEquity != 0: log.exception(e)
                            startEquity = 0
                    df.loc[date, algo.name] = growth
                elif date > dates[1]: break
    except Exception as e: log.exception(e)
    
    df['combined'] = df.sum(1, min_count=len(algos))
    metrics = {}
    metrics['mean'] = df.combined.mean()
    metrics['stdev'] = df.combined.std()
    metrics['min'] = df.combined.min()
    metrics['max'] = df.combined.max()
    
    return metrics

def get_results(dates, backtestName, deltaNeutral=True):
    # init algos
    c.algoPath = c.resultsPath + backtestName + '/algos/'
    c.logPath = c.resultsPath + backtestName + '/logs/'
    with patch('algos.c', c), patch('algoClass.c', c):
        algos = init_algos(True, None)
    
    # get metrics
    metrics = pd.DataFrame(columns=['name', 'mean', 'stdev', 'min', 'max'])
    if deltaNeutral:
        for algo1 in algos['all']:
            if algo1.name[-4:] == 'long':
                name = algo1.name[:-4] + 'short'
                for algo2 in algos['all']:
                    if algo2.name == name:
                        algoMetrics = get_combined_metrics([algo1, algo2], dates)
                        algoMetrics['name'] = algo1.name[:-5]
                        metrics = metrics.append(algoMetrics, ignore_index=True)
                        break
    else:
        for algo in algos['all']:
            algoMetrics = get_combined_metrics([algo], dates)
            algoMetrics['name'] = algo.name
            metrics = metrics.append(algoMetrics, ignore_index=True)

    # exit
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    return metrics

def save_results(dates, backtestName):
    startDate = datetime.strptime(dates[0], '%Y-%m-%d')
    stopDate = datetime.strptime(dates[1], '%Y-%m-%d')

    with open(c.resultsPath + backtestName + '/results.txt', 'w', ) as f:
        metrics = get_results(dates, backtestName)

        f.write(dates[0] + ' - ' + dates[1] + '\n')
        f.write(str(metrics) + '\n\n')

        detail = None
        if stopDate - startDate > timedelta(1000): detail = 'year'
        elif stopDate - startDate > timedelta(100): detail = 'month'
        elif stopDate - startDate > timedelta(20): detail = 'week'
        if detail:
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

                results = get_results(dates, backtestName)

                f.write(dates[0] + ' - ' + dates[1] + '\n')
                f.write(str(results) + '\n\n')

                if detail == 'year':
                    startDate = startDate.replace(year=startDate.year+1, month=1, day=1) # start on Jan 1
                elif detail == 'month':
                    startDate = nextMonth - timedelta(nextMonth.day - 1) # start on first of month
                elif detail == 'week':
                    startDate += timedelta(7) - timedelta(startDate.weekday()) # start on monday

def plot_backtest(backtestName: str, barFreq: str, symbol: str, dates: list, algoName: str) -> tuple:
    # backtestName: final directory containing backtest (algos and logs folders)
    # barFreq: for plotting price data
    # dates: start and stop date

    # FIX: "ValueError: year 72991 is out of range" on some symbols

    # suppress SettingWithCopyWarning
    pd.set_option('mode.chained_assignment', None)

    # import backtest config
    path = c.resultsPath + backtestName + '/'
    c2 = importlib.import_module(path.replace('/', '.') + 'config')
    c.barPath = path + 'bars/'
    c.logPath = path + 'logs/'

    # get price data
    bars = pd.read_csv(c.barPath + f'{barFreq}_{symbol}.csv',
        header=0, index_col=0, parse_dates=True)
    fromDate, toDate = get_dates(dates)
    data = bars.loc[fromDate:toDate]
    data.index = pd.DatetimeIndex(data.index).tz_convert(nyc) # pylint: disable=no-member
    data['trades'] = 0
    data['tradePrice'] = 0
    data['tradeQty'] = 0
    
    # get trades
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
                            data.loc[time, 'trades'] = 1
                        else:
                            data.loc[time, 'trades'] = -1
                        
                        if fillQty:
                            data.loc[time, 'trades'] *= 2

                            fillPrice = float(line.split('@ ')[1])
                            data.loc[time, 'tradePrice'] = fillPrice

                            data.loc[time, 'tradeQty'] = fillQty

                        else: # limit price
                            # NOTE: update if tick_algos.get_limit_price changes
                            if time in data.index:
                                if algoQty > 0:
                                    prevTime = time - timedelta(minutes=1)
                                    data.loc[time, 'tradePrice'] = data.close[prevTime] * (1 + c.limitPriceFrac)
                                else:
                                    prevTime = time - timedelta(minutes=1)
                                    data.loc[time, 'tradePrice'] = data.close[prevTime] * (1 - c.limitPriceFrac)
                            else:
                                print(time + ' Trade w/out bar')
    data = data.sort_index() # sort new timestamps

    # plot
    numDays = (toDate - fromDate).days
    figs = []
    for ii in range(numDays):
        # get date range
        start = fromDate + timedelta(ii)
        stop = fromDate + timedelta(ii+1)
        dayData = data.loc[start:stop]

        # format plot
        fig, axs = plt.subplots(2, sharex=True)
        figs.append(fig)
        axs[1].tick_params('x', labelrotation=45)

        # plot vwap
        dayData.vwap.plot(ax=axs[0])

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
        try: dayData.tradePrice[dayData.trades == 2].plot(style='r^', markersize=9, markeredgecolor='k', ax=axs[0])
        except: pass # plot fails if df is empty
        try: dayData.tradePrice[dayData.trades == 1].plot(style='k^', markersize=9, ax=axs[0])
        except: pass
        try: dayData.tradePrice[dayData.trades == -1].plot(style='kv', markersize=9, ax=axs[0])
        except: pass
        try: dayData.tradePrice[dayData.trades == -2].plot(style='gv', markersize=9, markeredgecolor='k', ax=axs[0])
        except: pass

        # profit
        try: profit = -100 / c.buyPow / c.maxPositionFrac * \
            (dayData.tradePrice[dayData.trades.abs() == 2] * dayData.tradeQty[dayData.trades.abs() == 2]).sum()
        except: profit = None
        
        # title
        axs[0].set_title(f'{algoName}\n{symbol}  |  {start.date()}  |  {profit:.3}%')

        # plot volume
        axs[1].bar(dayData.index, dayData.volume, 0.0005)

    # exit
    noTradesData = bars.loc[fromDate:toDate]
    noTradesData.index = pd.DatetimeIndex(noTradesData.index).tz_convert(nyc) # pylint: disable=no-member
    return figs, data, noTradesData

def plot_indicators(figs: list, data: pd.DataFrame, indicators: list):
    # figs: pyplot figures
    # data: barset
    # indicators: guess

    # add indicator columns
    for indicator in indicators:
        data[indicator.name] = None

    # plot
    fromDate = data.index[0].replace(hour=0, minute=0)
    for ii in range(len(figs)):
        # get date range
        start = fromDate + timedelta(ii)
        stop = fromDate + timedelta(ii+1)
        dayData = data.loc[start:stop]
        
        # get indicator values
        for jj in range(len(dayData)):
            for indicator in indicators:
                kk = dayData.columns.get_loc(indicator.name)
                dayData.iloc[jj, kk] = indicator.get(dayData[:jj+1])

        # plot indicators
        labels = ['vwap', 'filled buy', 'unfilled buy', 'unfilled sell', 'filled sell']
        for indicator in indicators:
            figs[ii].axes[0].plot(dayData[indicator.name], linestyle=':')
            labels.append(indicator.name)
        figs[ii].axes[0].legend(labels)
