import backtesting.config as c
import backtesting.historicBars as histBars
import backtesting.timing as timing

import alpaca_trade_api, os, shutil, sys
from datetime import datetime
from logging import getLogger
from pandas import DataFrame
from statistics import mean

log = getLogger('backtest')

def init_assets(
    alpaca: alpaca_trade_api.REST,
    calendar: list,
    allAlgos: list,
    indicators: dict,
    dates: (str, str),
    barPath: str,
    numAssets: int,
    symbols: list,
    savedBarPath: str) -> dict:

    # create barPath
    os.mkdir(barPath)

    # get symbols
    if savedBarPath:
        # get downloaded symbols
        downloadedSymbols = []
        fileNames = os.listdir(savedBarPath)
        for name in fileNames:
            if name[:3] == 'day':
                downloadedSymbols.append(name[4:-4])
                shutil.copyfile(savedBarPath + name, barPath + name)
                name = 'min' + name[3:]
                shutil.copyfile(savedBarPath + name, barPath + name)
                if len(downloadedSymbols) == numAssets: break
        
        # check all symbols are downloaded
        if symbols:
            for symbol in symbols:
                if symbol not in downloadedSymbols:
                    log.exception(f'cannot find {symbol} barset')
                    sys.exit()
        else:
            symbols = downloadedSymbols
        
        # TODO: check barset dates
    else:
        # download day bars
        log.warning('Getting historic day bars')
        toDate = timing.nyc.localize(datetime.strptime(dates[1], '%Y-%m-%d'))
        dayBars = {}
        if symbols: 
            for symbol in symbols:
                bars = alpaca.polygon.historic_agg_v2(symbol, 1, 'day', *dates).df[:toDate]
                dayBars[symbol] = bars
                bars.to_csv(barPath + f'day_{symbol}.csv')
        else:
            alpacaAssets = alpaca.list_assets('active', 'us_equity')
            for ii, asset in enumerate(alpacaAssets):
                log.info(f'Checking asset {ii+1} / {len(alpacaAssets)}\t{asset.symbol}\n' + \
                    f'Found {len(dayBars.keys())} / {numAssets}')
                # check leverage (ignore marginability and shortability)
                if not any(x in asset.name.lower() for x in c.leverageStrings):
                    try: # check age, price, cash flow, and spread
                        bars = alpaca.polygon.historic_agg_v2(asset.symbol, 1, 'day', *dates).df[:toDate]
                        if (
                            bars.index[0].strftime('%Y-%m-%d') == dates[0] and
                            bars.low[-1] > c.minSharePrice and
                            mean(bars.volume * bars.close) > c.minDayCashFlow and
                            mean((bars.high - bars.low) / bars.low) > c.minDaySpread
                        ):
                            # save day bars
                            dayBars[asset.symbol] = bars
                            bars.to_csv(barPath + f'day_{asset.symbol}.csv')
                    except Exception as e:
                        if len(bars.index): log.exception(e)
                        else:  log.debug(e)
                if len(dayBars.keys()) == numAssets: break
            symbols = list(dayBars.keys())

        # download min bars
        histBars.get_historic_min_bars(alpaca, calendar, dayBars, barPath)

    # add symbols to assets and positions
    assets = {'sec': {}, 'min': {}, 'day': {}}
    for symbol in symbols:
        # add zero positions
        for algo in allAlgos:
            algo.positions[symbol] = {'qty': 0, 'basis': 0}

        # init sec bars
        columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
        for indicator in indicators['sec']: columns.append(indicator.name)
        data = dict.fromkeys(columns)
        data['ticked'] = True
        assets['sec'][symbol] = DataFrame(data, [datetime(1,1,1)])

        # init min bars
        columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
        for indicator in indicators['min']: columns.append(indicator.name)
        data = dict.fromkeys(columns)
        data['ticked'] = True
        assets['min'][symbol] = DataFrame(data, [datetime(1,1,1)])
        
        # init day bars
        columns = ['open', 'high', 'low', 'close', 'volume', 'ticked']
        for indicator in indicators['day']: columns.append(indicator.name)
        data = dict.fromkeys(columns)
        data['ticked'] = True
        assets['day'][symbol] = DataFrame(data, [datetime(1,1,1)])
    
    # exit
    return assets