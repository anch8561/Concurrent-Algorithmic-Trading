import backtesting.config as c
from algos import init_algos
from indicators import Indicator

import matplotlib.pyplot as plt
import pandas as pd
import ta
from datetime import datetime, timedelta
from pytz import timezone
from unittest.mock import patch

nyc = timezone('America/New_York')

def get_dates(dates):
    fromDate = nyc.localize(datetime.strptime(dates[0], '%Y-%m-%d'))
    toDate = nyc.localize(datetime.strptime(dates[1], '%Y-%m-%d')) + timedelta(1)
    return fromDate, toDate

def get_metrics(dates):
    # suppress SettingWithCopyWarning
    pd.set_option('mode.chained_assignment', None)

    # get numDays
    fromDate, toDate = get_dates(dates)
    numDays = (toDate - fromDate).days

    # get metrics
    metrics = pd.DataFrame()
    with patch('algos.c', c), patch('algoClass.c', c):
        algos = init_algos(True, None)
    for algo in algos['all']:
        algoMetrics = algo.get_metrics(numDays)
        algoMetrics['name'] = algo.name

        metrics = metrics.append(algoMetrics, ignore_index=True)
    
    # exit
    pd.set_option("display.max_rows", None, "display.max_columns", None)
    return metrics

def plot_backtest(barFreq, symbol, dates, algoName):
    # NOTE: assumes only 1 backtest in logs

    # get price data
    bars = pd.read_csv(c.barPath + f'{barFreq}_{symbol}.csv',
        header=0, index_col=0, parse_dates=True)
    fromDate, toDate = get_dates(dates)
    data = bars.loc[fromDate:toDate]
    data['buy'] = False # SettingWithCopyWarning
    data['sell'] = False # SettingWithCopyWarning
    
    # get trades
    time = fromDate - timedelta(1)
    with open(c.logPath + algoName + '.log') as f:
        while True:
            try: line = next(f)
            except: break

            if algoName in line:
                time = nyc.localize(datetime.strptime(line[:19], '%Y-%m-%d %H:%M:%S'))
                if (
                    time > fromDate and
                    time < toDate
                ):
                    line = next(f)
                    if symbol in line:
                        if 'enter' in line:
                            data.loc[time, 'buy'] = True
                        elif 'exit' in line:
                            data.loc[time, 'sell'] = True
                    
    
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
        axs[0].set_title(f'{algoName}\n{symbol}\n{start.date()}')
        axs[1].tick_params('x', labelrotation=45)

        # plot price and trades
        dayData.vwap.plot(ax=axs[0])
        dayData.close.plot(ax=axs[0])
        dayData.close[dayData.buy].plot(style='r^', ax=axs[0])
        dayData.close[dayData.sell].plot(style='gv', ax=axs[0])

        # plot volume
        axs[1].bar(dayData.index, dayData.volume, 0.0005)

    # exit
    return figs, data

def plot_indicators(figs: list, data: pd.DataFrame, indicatorSpecs: list):
    # figs: pyplot figures
    # data: barset
    # indicatorData: [{args: [numBars, barFreq, func], kwargs: {}}]

    # init indicators
    indicators = []
    for ii in range(len(indicatorSpecs)):
        args = indicatorSpecs[ii]['args']
        kwargs = indicatorSpecs[ii]['kwargs']
        indicators.append(Indicator(*args, *kwargs))
        data[indicators[-1].name] = None

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
        labels = ['vwap', 'close', 'buy', 'sell']
        for indicator in indicators:
            figs[ii].axes[0].plot(dayData[indicator.name], linestyle=':')
            labels.append(indicator.name)
        figs[ii].axes[0].legend(labels)
