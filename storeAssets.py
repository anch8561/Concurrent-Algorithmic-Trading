# NOTE: this file is outdated and unused

import globalVariables as g
from warn import warn

def save_asset(symbol, barType):
    # symbol: e.g. 'AAPL'
    # barType: 'secBars', 'minBars', or 'dayBars'

    # check arguments
    if symbol not in g.assets:
        warn(f'symbol "{barType}" not in g.assets')
        return
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'unknown barType "{barType}"')
        return

    # save bars
    try:
        fileName = symbol + '_' + barType + '.data'
        g.assets[symbol][barType].to_csv(fileName)
    except Exception as e:
        print(e)

def save_all_assets():
    for symbol in g.assets:
        for barType in ('secBars', 'minBars', 'dayBars'):
            try:
                save_asset(symbol, barType)
            except Exception as e:
                print(e)

def load_asset(symbol, barType):
    # symbol: e.g. 'AAPL'
    # barType: 'secBars', 'minBars', or 'dayBars'

    # check arguments
    if symbol not in g.assets:
        warn(f'symbol "{barType}" not in g.assets')
        return
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'unknown barType "{barType}"')
        return
    
    # load bars
    try:
        fileName = symbol + '_' + barType + '.data'
        g.assets[symbol][barType].read_csv(fileName)
    except Exception as e:
        print(e)

def load_all_assets():
    for symbol in g.assets:
        for barType in ('secBars', 'minBars', 'dayBars'):
            try:
                load_asset(symbol, barType)
            except Exception as e:
                print(e)
