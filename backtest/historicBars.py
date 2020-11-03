import backtest.timing as timing
from tab import tab

import alpaca_trade_api, os, pytz
from datetime import datetime
from logging import getLogger
from pandas import DataFrame, read_csv

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
        minBars = DataFrame()
        fromDate = dayBars[symbol].index[0]
        fromDateIdx = timing.get_calendar_index(calendar, fromDate.strftime('%Y-%m-%d'))
        toDateStr = dayBars[symbol].index[-1].strftime('%Y-%m-%d')
        toDateIdx = timing.get_calendar_index(calendar, toDateStr)
        toDate = timing.get_market_close(calendar, toDateIdx)
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
                fromDate = timing.get_calendar_date(calendar, fromDateIdx)
            try: newBars = newBars.drop(extendedHours)
            except Exception as e:
                if extendedHours == []: log.debug(e)
                else: log.exception(e)
            
            # add new bars
            try: minBars = minBars[:newBars.index[0]] # remove overlap
            except Exception as e: log.debug(e) # no overlap
            minBars = minBars.append(newBars)
            fromDate = minBars.index[-1]

        # save bars
        minBars.to_csv(f'backtest/bars/min_{symbol}.csv')

def init_bar_gens(barFreqs: list, symbols: list) -> dict:
    barGens = {'sec': {}, 'min': {}, 'day': {}}
    for barFreq in barFreqs:
        for symbol in symbols:
            barGens[barFreq][symbol] = {
                'buffer': None,
                'generator': read_csv(f'backtest/bars/{barFreq}_{symbol}.csv',
                    header=0, index_col=0, chunksize=1, parse_dates=True)}
    return barGens

def get_next_bars(barFreq: str, timestamp: datetime, barGens: dict, indicators: dict, assets: dict):
    # barFreq: 'sec', 'min', or 'day'
    # timestamp: expected bar index
    # barGens: dict of dict of generators;  {barFreq: {symbol: {buffer, generator}}}
    # indicators: dict of lists of indicators; {barFreq: indicators}
    # assets: dict of dict of bars; {barFreq: {symbol: bars}}
    # append next bars to assets DataFrames

    for symbol, barGen in barGens[barFreq].items():
        while True: # loop if bar index < expected
            # check buffer and get next bar
            if type(barGen['buffer']) == DataFrame:
                nextBar = barGen['buffer'] # get bar from buffer
                barGen['buffer'] = None
            else:
                nextBar = next(barGen['generator']) # get bar from generator

            # check timestamp and process bar
            if nextBar.index[0] == timestamp: # expected timestamp
                # add bar to assets
                bars = assets[barFreq][symbol].append(nextBar)
                jj = bars.columns.get_loc('ticked')
                bars.iloc[-1, jj] = False

                # get indicators
                for indicator in indicators[barFreq]:
                    jj = bars.columns.get_loc(indicator.name)
                    bars.iloc[-1, jj] = indicator.get(bars)
                
                # save bars
                assets[barFreq][symbol] = bars
                break
                
            elif nextBar.index[0] > timestamp: # future timestamp
                barGen['buffer'] = nextBar # save to buffer
                break
            else: # past timestamp
                log.error(tab(symbol, 6) + f'bar index < expected: {nextBar.index[0]} < {timestamp}')
