import pandas as pd

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