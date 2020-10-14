import globalVariables as g
from algoClass import Algo
from indicators import Indicator, momentum

import logging
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

@fixture
def testAlgo(reloadGlobalVariables):
    testAlgo = Algo(print, 'short', False)
    testAlgo.positions['AAPL'] = {'qty': 0, 'basis': 0}
    return testAlgo

@fixture
def algos(reloadGlobalVariables):
    dayAlgos = [
        Algo(print, 'long', False, n=0),
        Algo(print, 'short', False, n=1),
        Algo(print, 'long', False, n=2),
        Algo(print, 'short', False, n=3)]
    nightAlgos = [
        Algo(print, 'long', False, n=4),
        Algo(print, 'short', False, n=5),
        Algo(print, 'long', False, n=6)]
    return {
        'day': dayAlgos,
        'night': nightAlgos,
        'all': dayAlgos + nightAlgos}

@fixture
def allAlgos(algos):
    return algos['all']

@fixture
def indicators():
    secInd = Indicator(1, 'sec', momentum)
    minInd = Indicator(1, 'min', momentum)
    dayInd = Indicator(1, 'day', momentum)
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
        'volume': [9999, 8888, 7777, 5555],
        'ticked': [True, True, True, False]}
    index = [
        g.nyc.localize(datetime(2020, 2, 13, 16, 19, 11, 234567)),
        g.nyc.localize(datetime(2020, 2, 13, 16, 20, 12, 345678)),
        g.nyc.localize(datetime(2020, 2, 13, 16, 21, 10, 123456)),
        g.nyc.localize(datetime(2020, 2, 13, 16, 22, 13, 456789))]
    bars = DataFrame(data, index)

    indicator = Indicator(1, 'min', momentum)
    bars[indicator.name] = None
    jj = bars.columns.get_loc(indicator.name)
    for ii in range(len(bars.index)):
        bars.iloc[ii, jj] = indicator.get(bars.iloc[:ii+1])
    return bars
