import alpaca_trade_api, os
import pandas as pd
from datetime import datetime
from logging import getLogger
from pytz import timezone

nyc = timezone('America/New_York')
log = getLogger('backtest')

def get_calendar_index(calendar: list, date: str) -> int:
    # calendar: alpaca.get_calendar()
    # date: e.g. '1996-02-13'
    for ii, day in enumerate(calendar):
        if day._raw['date'] == date:
            return ii

def get_historic_min_bars(
    alpaca: alpaca_trade_api.REST,
    calendar: list,
    dayBars: dict):
    # calendar: alpaca.get_calendar()
    # dayBars: get_historic_day_bars()
    # saves csv for each symbol w/ minute bars from day bar date range

    log.warning('Getting historic minute bars')
    for ii, symbol in enumerate(dayBars.keys()):
        log.info(f'Downloading asset {ii+1} / {len(dayBars.keys())}\t{symbol}')
        fromDate = dayBars[symbol].index[0]
        toDate = dayBars[symbol].index[-1]
        fromDateIdx = get_calendar_index(calendar, fromDate)
        while fromDate < toDate:
            # download bars
            newBars = alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate)
            newBars = newBars.df[:5000] # remove extra toDate data

            # drop extended hours
            extendedHours = []
            while fromDate < newBars.index[-1]:
                # get market open and close
                marketOpen = datetime.combine(
                    date = fromDate,
                    time = calendar[fromDateIdx].open,
                    tzinfo = fromDate.tzinfo)
                marketClose = datetime.combine(
                    date = fromDate,
                    time = calendar[fromDateIdx].close,
                    tzinfo = fromDate.tzinfo)
                
                # get extended hours
                for timestamp in newBars.index:
                    if timestamp.date() == fromDate.date():
                        if timestamp < marketOpen or timestamp > marketClose:
                            extendedHours.append(timestamp)
                    elif timestamp.date() > fromDate.date():
                        break

                # get next market day
                fromDateIdx += 1
                fromDateStr = calendar[fromDateIdx]._raw['date']
                fromDate = nyc.localize(datetime.strptime(fromDateStr, '%Y-%m-%d'))
            newBars = newBars.drop(extendedHours)
            
            # add new bars
            minBars = minBars[:newBars.index[0]].append(newBars)
            fromDate = minBars.index[-1]
            # FIX: may not get full final day

        # save bars
        minBars.to_csv(f'backtest/bars/min_{symbol}.csv')

def bar_gen(symbol: str, barFreq: str) -> pd.DataFrame:
    csvFile = pd.read_csv(
        f'backtesting/{barFreq}_{symbol}.csv',
        header = 0,
        index_col = 0,
        parse_dates = True)
    for bar in csvFile:
        yield bar

def init_bar_gens(barFreqs: list, symbols: list) -> dict:
    barGens = {'sec': {}, 'min': {}, 'day': {}}
    for barFreq in barGens:
        for symbol in symbols:
            barGens[barFreq][symbol] = bar_gen(symbol, barFreq)
    return barGens

def get_next_bars(barFreq: str, assets: dict, barGens: dict):
    # barFreq: 'sec', 'min', or 'day'
    # assets: dict of dict of bars; {day, min, sec} -> {symbol: bars}
    # barGens: dict of dict of generators;  {day, min, sec} -> {symbol: gen}
    # append next bars to assets DataFrames
    for symbol, barGen in barGens[barFreq].items():
        assets[barFreq][symbol].append(next(barGen), inplace=True)
