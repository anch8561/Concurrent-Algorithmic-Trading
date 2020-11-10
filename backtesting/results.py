import config as c

import matplotlib.pyplot as plt
import ta
from datetime import datetime, timedelta
from pandas import DataFrame, read_csv
from pytz import timezone

nyc = timezone('America/New_York')

def plot_backtest(barFreq, algoName, symbol, dates):
    # get price data
    bars = read_csv(c.barPath + f'{barFreq}_{symbol}.csv',
        header=0, index_col=0, parse_dates=True)
    fromDate = nyc.localize(datetime.strptime(dates[0], '%Y-%m-%d'))
    toDate = nyc.localize(datetime.strptime(dates[1], '%Y-%m-%d')) + timedelta(1)
    plotData = bars.loc[fromDate:toDate]
    plotData['buy'] = False # SettingWithCopyWarning
    plotData['sell'] = False # SettingWithCopyWarning
    
    # get trades
    time = fromDate - timedelta(1)
    with open(c.logPath + 'debug.log') as f:
        while True:
            try: line = next(f)
            except: break

            # check for timestamp
            split = line.split('Time: ')
            if len(split) == 2:
                time = nyc.localize(datetime.strptime(split[1][:19], '%Y-%m-%d %H:%M:%S'))
                
            # check for trade
            # FIX: assumes only 1 backtest in logs
            elif (
                time > fromDate and
                time < toDate and
                algoName in line
            ):
                line = next(f)
                if symbol in line:
                    if 'enter' in line:
                        plotData.loc[time, 'buy'] = True
                    elif 'exit' in line:
                        plotData.loc[time, 'sell'] = True
                    
    
    # plot
    numDays = (toDate - fromDate).days
    figs = []
    for ii in range(numDays):
        # get date range
        start = fromDate + timedelta(ii)
        stop = fromDate + timedelta(ii+1)
        data = plotData.loc[start:stop]

        # format plot
        fig, axs = plt.subplots(2, sharex=True)
        figs.append(fig)
        axs[0].set_title(f'{algoName}\n{symbol}\n{start.date()}')
        axs[1].tick_params('x', labelrotation=45)

        # plot price and trades
        data.vwap.plot(style='b', ax=axs[0])
        data.close[data.buy].plot(style='r^', ax=axs[0])
        data.close[data.sell].plot(style='gv', ax=axs[0])

        # plot volume
        axs[1].bar(data.index, data.volume, 0.0005)

    # exit
    return figs, plotData

def plot_indicators(figs, plotData):
    EMA_5 = ta.trend.ema_indicator(plotData.close, 3)
    EMA_10 = ta.trend.ema_indicator(plotData.close, 5)
    figs[ii].axes[0].plot(EMA_5, color='k', linestyle=':')
    figs[ii].axes[0].plot(EMA_10, color='k', linestyle='-')

fig, plotData = plot_backtest('min', '3_5_min_crossover_long', 'AAP', ['2020-10-26', '2020-10-26'])
# plot_indicators(fig, plotData)
plt.show()