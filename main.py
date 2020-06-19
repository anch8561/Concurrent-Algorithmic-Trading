# Initialize indicators, algorithms, and streaming, then enter main loop.
# Allocate buying power once per week. Update assets and metrics daily.
# Tick algorithms at regular intervals.

# initialize indicators
from indicators import DayReturn, DayVolume
indicators = []
dayIndicators = [
    DayReturn,
    DayVolume
]
for indicator in dayIndicators:
    for days in (1, 2, 3, 5, 10, 20):
        indicators.append(indicator(days))

# initialize algos
from Algo import Algo
from config import minAllocBP
intradayAlgos = []
overnightAlgos = [
    Algo( # overnight hold
        BP = minAllocBP,
        enterIndicators = [
            DayReturn(5).name,
            'dayVolume5'],
        exitIndicators = None,
        timeframe = 'overnight',
        equityStyle = 'longShort',
        tickFreq = 'min')
]
multidayAlgos = []
algos = intradayAlgos + overnightAlgos + multidayAlgos

# TODO: dataStreaming


# TODO: read date from file or prompt to coninue
lastRebalanceDate = "0001-01-01"

# main loop
from marketHours import get_time, get_date, get_open_time, get_close_time, is_new_week_since
from datetime import timedelta
from distribute_funds import distribute_funds
from get_tradable_assets import get_tradable_assets
while True:
    # get buying power
    if is_new_week_since(lastRebalanceDate):
        distribute_funds(algos)

    # get time
    time = get_time()
    openTimedelta = time - get_open_time()
    closeTimedelta = time - get_close_time()

    # get symbols
    if (
        lastSymbolUpdate != get_date() and
        openTimedelta > timedelta(hours=-1)
    ):
        get_tradable_assets(algos)
        lastSymbolUpdate = get_date()

    # get bars and orders

    # get indicators

    # tick algos
    if (
        openTimedelta > timedelta(0) and
        closeTimedelta < timedelta(hours=-1)
    ):
        for algo in overnightAlgos:
            if algo.positions:
                algo.overnight_exit()
            else:
                algo.update_metrics()



    for algo in intradayAlgos: algo.tick() # in parallel
    for algo in multidayAlgos: algo.tick()

    # get allOrders and allPositions

    # wait remainder of 1 sec

