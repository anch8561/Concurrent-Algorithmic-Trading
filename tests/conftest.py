import globalVariables as g
from algoClass import Algo
from indicators import Indicator, mom

import logging, os
from datetime import datetime
from importlib import reload
from pandas import DataFrame
from pytest import fixture
from pytz import timezone
from unittest.mock import Mock

logging.basicConfig(level=logging.DEBUG)

# NOTE: be careful of Mock scope
# NOTE: be careful of fixture order
# TODO: patch config
# TODO: replace patch classes w/ alpaca entities (e.g. Calendar in timing)

@fixture(autouse=True)
def reloadGlobalVariables():
    reload(g) # NOTE: reload does not update existing objects
    g.positions['AAPL'] = 0

@ fixture(autouse=True, scope='session')
def cleanup():
    yield None
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger in loggers:
        for hdlr in logger.handlers[:]:
            hdlr.close()
    for ii in range(7):
        longShort = 'short' if ii%2 else 'long'
        try: os.remove(f'logs/{ii}_min_print_{longShort}.log')
        except: pass
    try: os.remove(f'logs/min_print_short.log')
    except: pass

@fixture
def testAlgo(reloadGlobalVariables):
    testAlgo = Algo('min', print, 'short', False)
    testAlgo.positions['AAPL'] = {'qty': 0, 'basis': 0}
    return testAlgo

@fixture
def algos(reloadGlobalVariables):
    intradayAlgos = [
        Algo('min', print, 'long', False, n=0),
        Algo('min', print, 'short', False, n=1),
        Algo('min', print, 'long', False, n=2),
        Algo('min', print, 'short', False, n=3)]
    overnightAlgos = [
        Algo('min', print, 'long', False, n=4),
        Algo('min', print, 'short', False, n=5),
        Algo('min', print, 'long', False, n=6)]
    return {
        'intraday': intradayAlgos,
        'overnight': overnightAlgos,
        'all': intradayAlgos + overnightAlgos}

@fixture
def allAlgos(algos):
    return algos['all']

@fixture
def indicators():
    secInd = Indicator(2, 'sec', mom)
    minInd = Indicator(2, 'min', mom)
    dayInd = Indicator(2, 'day', mom)
    return {
        'sec': [secInd],
        'min': [minInd],
        'day': [dayInd],
        'all': [secInd, minInd, dayInd]}

@fixture
def bars(indicators):
    data = {
        'open':  [232.32, 345.67, 222.22, 525.01],
        'high':  [454.54, 456.78, 444.44, 600.02],
        'low':   [121.21, 123.45, 111.11, 500.03],
        'close': [343.43, 234.56, 333.33, 575.04],
        'vwap':  [123.12, 234.23, 345.34, 567.56],
        'volume': [9999, 8888, 7777, 5555],
        'ticked': [True, True, True, False]}
    index = [
        g.nyc.localize(datetime(2020, 2, 13, 16, 19, 11, 234567)),
        g.nyc.localize(datetime(2020, 2, 13, 16, 20, 12, 345678)),
        g.nyc.localize(datetime(2020, 2, 13, 16, 21, 10, 123456)),
        g.nyc.localize(datetime(2020, 2, 13, 16, 22, 13, 456789))]
    bars = DataFrame(data, index)

    indicator = Indicator(2, 'min', mom)
    bars[indicator.name] = None
    jj = bars.columns.get_loc(indicator.name)
    for ii in range(len(bars.index)):
        bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii+1])
    return bars
