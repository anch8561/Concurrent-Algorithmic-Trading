import backtesting.config as c
from algos import init_algos

import json, os
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Literal, Union

def load_history(filePath: str):
    with open(filePath, 'r') as f:
        data = json.load(f)
    return data['history']

def get_combined_history(
    histories: List[
        Dict[
            str, # date
            Dict[
                Literal['event', 'equity'],
                Union[
                    Literal['start', 'stop'], # event
                    float]]]], # equity
    dates: List[str] = []
) -> pd.Series:
    '''
    histories: list of algo histories; [{date: {'event', 'equity'}}]
        date: str; (YYYY-MM-DD)
        'event': 'start' or 'stop'
        'equity': float
    dates: list; start and stop date strings (YYYY-MM-DD); empty means all dates
    returns: pd.Series; combined growth fractions of algos with date str index
    '''

    # check dates
    if dates == []: dates = ['0', '9']

    # get growth
    # FIX: night algos start and stop on different days
    df = pd.DataFrame()
    for column, history in enumerate(histories):
        dateKeys = sorted(history)
        for date in dateKeys:
            if dates[0] <= date and date <= dates[1]:
                growth = 0
                startEquity = 0
                for entry in history[date].values():
                    if entry['event'] == 'start':
                        startEquity = entry['equity']
                    elif entry['event'] == 'stop' and startEquity:
                        stopEquity = entry['equity']
                        growth = (1 + growth) * stopEquity / startEquity - 1
                        startEquity = 0
                df.loc[date, column] = growth
            elif date > dates[1]: break
    
    return df.sum(1, min_count=len(histories))

def get_backtest_history(backtestDir: str, dates: list = [], deltaNeutral: bool = True) -> pd.DataFrame:
    # backtestDir: directory (within results path) where backtest is stored
    # dates: start and stop date strings (YYYY-MM-DD)
    # deltaNeutral: whether to combine long and short versions of algos
    # returns: growth fractions of algos with date str index
    
    algoPath = c.resultsPath + backtestDir + '/algos/'
    algoFileNames = os.listdir(algoPath)
    
    # get history
    history = pd.DataFrame()
    if deltaNeutral:
        for fileName1 in algoFileNames:
            if fileName1[-10:] == '_long.json':
                name = fileName1[:-10]
                for fileName2 in algoFileNames:
                    if fileName2 == name + '_short.json':
                        algoHistories = [ # load files
                            load_history(algoPath + fileName1),
                            load_history(algoPath + fileName2)]
                        algoHistory = get_combined_history(algoHistories, dates) # combine and filter dates
                        history[name] = algoHistory
                        break
    else:
        for fileName in algoFileNames:
            algoHistories = [load_history(algoPath + fileName)] # load file
            algoHistory = get_combined_history(algoHistories, dates) # filter dates
            algoName = fileName[:-5]
            history[algoName] = algoHistory
    return history

def get_combined_backtest_history(backtestDir: str, dates: list = [], deltaNeutral: bool = True) -> pd.DataFrame:
    # backtestDir: all backtests (subdirectories) in this directory (within results path) will be combined
    # dates: start and stop date strings (YYYY-MM-DD)
    # deltaNeutral: whether to combine long and short versions of algos
    # returns: growth fractions of algos with date str index

    # append slash to backtestDir if needed
    if backtestDir and backtestDir[-1] != '/':
        backtestDir += '/'

    # collect histories
    history = pd.DataFrame()
    backtestSubdirs = os.listdir(c.resultsPath + backtestDir)
    for backtestSubdir in backtestSubdirs:
        try: # expects all subdirectories to be backtests
            path = backtestDir + backtestSubdir
            backtestHistory = get_backtest_history(path, dates, deltaNeutral)
            history = history.append(backtestHistory)
        except Exception as e: print(e)
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

def save_backtest_summary(backtestDir: str, dates: list = [], deltaNeutral: bool = True):
    # backtestDir: directory (within results path) where backtest is stored
    # dates: start and stop date strings (YYYY-MM-DD)
    # deltaNeutral: whether to combine long and short versions of algos

    with open(c.resultsPath + backtestDir + '/results.txt', 'w', ) as f:
        # get history, dates, and metrics
        if dates == []: # get dates
            history = get_backtest_history(backtestDir)
            dates = [history.index[0], history.index[-1]]
        else:
            history = get_backtest_history(backtestDir, dates)
        startDate = datetime.strptime(dates[0], '%Y-%m-%d')
        stopDate = datetime.strptime(dates[1], '%Y-%m-%d')
        metrics = get_metrics(history)

        f.write(dates[0] + ' - ' + dates[1] + '\n')
        f.write(metrics.to_string() + '\n\n')

        # get periodic summaries
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

                history = get_backtest_history(backtestDir, dates)
                metrics = get_metrics(history)

                f.write(dates[0] + ' - ' + dates[1] + '\n')
                f.write(metrics.to_string() + '\n\n')

                if detail == 'year':
                    startDate = startDate.replace(year=startDate.year+1, month=1, day=1) # start on Jan 1
                elif detail == 'month':
                    startDate = nextMonth - timedelta(nextMonth.day - 1) # start on first of month
                elif detail == 'week':
                    startDate += timedelta(7) - timedelta(startDate.weekday()) # start on monday
