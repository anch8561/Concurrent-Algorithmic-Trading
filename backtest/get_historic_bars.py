import alpaca_trade_api, os
from datetime import datetime
from logging import getLogger
from pytz import timezone

nyc = timezone('America/New_York')
log = getLogger('backtest')

def get_historic_bars(alpaca: alpaca_trade_api.REST, calendar: list, symbols: list, fromDateStr: str, toDateStr: str):
    # calendar: alpaca.get_calendar()
    # symbols: list of str
    # fromDate: e.g. '2004-01-01'
    # toDate: e.g. 2020-01-01'
    # saves csv for each symbol w/ bars from date range
    # NOTE: uses alpaca and log globals

    log.warning('Getting historic bars')

    # create bars dir if needed
    try: os.mkdir('backtest/bars')
    except Exception: pass

    # check date bounds
    if fromDateStr < '2004':
        log.error('No historic bars before 2004')
        return
    if toDateStr >= datetime.now(nyc).strftime('%Y-%m-%d'):
        log.error('No historic bars after yesterday')
        return

    # convert dates to market dates (inf loop if toDate not market day)
    # also allows for partial dates (e.g. '2005' -> '2005-01-01')
    for ii, date in enumerate(calendar): # get fromDateStr or next market day
        if date._raw['date'] >= fromDateStr:
            fromDateStr = date._raw['date']
            fromDateIdx = ii
            break
    for date in reversed(calendar): # get toDateStr or prev market day
        if date._raw['date'] <= toDateStr:
            toDateStr = date._raw['date']
            break

    # get toDate as datetime
    toDate = nyc.localize(datetime.strptime(toDateStr, '%Y-%m-%d'))

    # get bars
    for ii, symbol in enumerate(symbols):
        log.info(f'Downloading asset {ii+1} / {len(symbols)}\t{symbol}')

        # reset fromDate
        fromDate = nyc.localize(datetime.strptime(fromDateStr, '%Y-%m-%d'))

        # get day bars
        # NOTE: will not work with start dates over 20 yrs ago
        dayBars = alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate).df
        dayBars.to_csv(f'backtest/bars/day_{symbol}.csv')

        # get minute bars
        fromDate = dayBars.index[0]
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
            
            try: # add new bars
                newBars = newBars[minBars.index[-1]:][1:] # remove overlap
                minBars = minBars.append(newBars)
            except:
                minBars = newBars
            
            fromDate = minBars.index[-1]

        # save bars
        minBars.to_csv(f'backtest/bars/min_{symbol}.csv')