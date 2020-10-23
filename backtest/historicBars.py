import backtestTiming as timing

import alpaca_trade_api, os, pytz
import pandas as pd
from datetime import datetime
from logging import getLogger

log = getLogger('backtest')

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
        minBars = pd.DataFrame()
        fromDate = dayBars[symbol].index[0]
        toDate = dayBars[symbol].index[-1]
        fromDateIdx = timing.get_calendar_index(calendar, fromDate.strftime('%Y-%m-%d'))
        while fromDate < toDate:
            print(f'Downloading minutes from {fromDate.date()}')
            # download bars
            newBars = alpaca.polygon.historic_agg_v2(symbol, 1, 'minute', fromDate, toDate)
            newBars = newBars.df[:5000] # remove extra toDate data

            # drop extended hours
            extendedHours = []
            while fromDate < newBars.index[-1]:
                # get market open and close
                marketOpen = timing.get_market_open(calendar, fromDateIdx)
                marketClose = timing.get_market_close(calendar, fromDateIdx)
                
                # get extended hours
                for timestamp in newBars.index:
                    if timestamp.date() == fromDate.date():
                        if timestamp < marketOpen or timestamp > marketClose:
                            extendedHours.append(timestamp)
                    elif timestamp.date() > fromDate.date():
                        break

                # get next market day
                fromDateIdx += 1
                fromDate = timing.get_date(calendar, fromDateIdx)
            newBars = newBars.drop(extendedHours)
            
            # add new bars
            try: minBars = minBars[:newBars.index[0]] # remove overlap
            except Exception as e: log.debug(e) # no overlap
            minBars = minBars.append(newBars)
            fromDate = minBars.index[-1]
            # FIX: may not get full final day

        # save bars
        minBars.to_csv(f'backtest/bars/min_{symbol}.csv')

def bar_gen(symbol: str, barFreq: str) -> pd.DataFrame:
    with pd.read_csv(f'backtesting/{barFreq}_{symbol}.csv',
        header = 0, index_col = 0, parse_dates = True) as csvFile:
        for bar in csvFile:
            yield bar

def init_bar_gens(barFreqs: list, symbols: list) -> dict:
    barGens = {'sec': {}, 'min': {}, 'day': {}}
    for barFreq in barGens:
        for symbol in symbols:
            barGens[barFreq][symbol] = {
                'buffer': None,
                'generator': bar_gen(symbol, barFreq)}
    return barGens

def get_next_bars(barFreq: str, timestamp: datetime, barGens: dict, assets: dict):
    # barFreq: 'sec', 'min', or 'day'
    # timestamp: expected bar index
    # barGens: dict of dict of generators;  {barFreq: {symbol: {buffer, generator}}}
    # assets: dict of dict of bars; {barFreq: {symbol: bars}}
    # append next bars to assets DataFrames

    for symbol, barGen in barGens[barFreq].items():
        # get next bar from buffer or generator
        if barGen['buffer']:
            nextBar = barGen['buffer']
            barGen['buffer'] = None
        else:
            nextBar = next(barGen)

        # check timestamp and append or store
        if nextBar.index[0] == timestamp:
            assets[barFreq][symbol].append(nextBar, inplace=True)
        elif nextBar.index[0] > timestamp:
            barGen['buffer'] = nextBar
        else:
            log.error(f'Bar index < expected: {nextBar.index[0]} < {timestamp}')
