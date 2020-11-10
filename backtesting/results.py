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
    plotData = bars.close.loc[fromDate:toDate].to_frame('price')
    plotData['buy'] = False
    plotData['sell'] = False
    
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
                        plotData.buy.loc[time] = True
                    elif 'exit' in line:
                        plotData.sell.loc[time] = True
                    
    
    # plot
    plotData.price.plot(style='b')
    plotData.price[plotData.buy].plot(style='r^')
    plotData.price[plotData.sell].plot(style='gv')

    # exit
    return plotData

def plot_indicators(plotData):
    EMA_5 = ta.trend.ema_indicator(plotData.price, 3)
    EMA_10 = ta.trend.ema_indicator(plotData.price, 5)
    plt.plot(EMA_5, color='k', linestyle=':')
    plt.plot(EMA_10, color='k', linestyle='-')

plotData = plot_backtest('min', '3_5_min_crossover_long', 'AAP', ['2020-10-26', '2020-10-26'])
plot_indicators(plotData)
plt.show()