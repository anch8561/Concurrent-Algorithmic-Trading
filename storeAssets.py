# Save and load Algo.assets (must populate Algo.assets first)
from warn import warn
from Algo import Algo

def save_asset(symbol, barType):
    # symbol: e.g. 'AAPL'
    # barType: 'secBars', 'minBars', or 'dayBars'

    # check arguments
    if symbol not in Algo.assets:
        warn(f'symbol "{barType}" not in Algo.assets')
        return
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'unknown barType "{barType}"')
        return

    # save bars
    try:
        fileName = symbol + '_' + barType + '.data'
        Algo.assets[symbol][barType].to_csv(fileName)
    except Exception as e:
        print(e)

def save_all_assets():
    for symbol in Algo.assets:
        for barType in ('secBars', 'minBars', 'dayBars'):
            try:
                save_asset(symbol, barType)
            except Exception as e:
                print(e)

def load_asset(symbol, barType):
    # symbol: e.g. 'AAPL'
    # barType: 'secBars', 'minBars', or 'dayBars'

    # check arguments
    if symbol not in Algo.assets:
        warn(f'symbol "{barType}" not in Algo.assets')
        return
    if barType not in ('secBars', 'minBars', 'dayBars'):
        warn(f'unknown barType "{barType}"')
        return
    
    # load bars
    try:
        fileName = symbol + '_' + barType + '.data'
        Algo.assets[symbol][barType].read_csv(fileName)
    except Exception as e:
        print(e)

def load_all_assets():
    for symbol in Algo.assets:
        for barType in ('secBars', 'minBars', 'dayBars'):
            try:
                load_asset(symbol, barType)
            except Exception as e:
                print(e)
