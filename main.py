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
from update_tradable_assets import update_tradable_assets
state = 'night' # day, night
# TODO: load positions and check state
while True:
    # update buying power
    if is_new_week_since(lastRebalanceDate):
        distribute_funds(algos)

    # update time
    time = get_time()
    TTOpen = get_open_time() - time # time til open
    TTClose = get_close_time() - time # time til close

    # update symbols
    if (
        lastSymbolUpdate != get_date() and # weren't updated today
        TTOpen < timedelta(hours=1) # < 1 hour until market open
    ):
        update_tradable_assets(algos)
        lastSymbolUpdate = get_date()

    # TODO: update bars and orders

    # update indicators
    for indicator in indicators:
        for symbol in Algo.assets:
            indicator.tick(symbol)

    # update algos
    if ( # market is open and overnight positions are open
        state == 'night' and
        TTOpen < timedelta(0) and
        TTClose > timedelta(minutes=10)
    ):
        if handoff_BP(overnightAlgos, intradayAlgos): # true when done
            for algo in intradayAlgos: algo.active = True
            state = 'day'

    elif ( # market is open and overnight positions are closed
        state == 'day' and
        TTClose > timedelta(minutes=10)
    ):
        for algo in intradayAlgos: algo.tick(TTOpen, TTClose) # in parallel
        for algo in multidayAlgos: algo.tick(TTOpen, TTClose)

    elif ( # market will close soon and intraday positions are open
        state == 'day'
    ):
        if handoff_BP(intradayAlgos, overnightAlgos): # true when done
            for algo in overnightAlgos: algo.active = True
            state = 'night'

    elif ( # market will close soon and intraday positions are closed
        state == 'night'
    ):
        for algo in overnightAlgos: algo.overnight_enter()

    # TODO: update allOrders and allPositions

    # TODO: wait remainder of 1 sec

def handoff_BP(oldAlgos, newAlgos):
    # oldAlgos: list of algos to get BP from
    # newAlgos: list of algos to give BP to
    # returns: bool; whether handoff is complete
    
    # exit positions and update metrics
    oldActive = False
    for algo in oldAlgos:
        if algo.active:
            oldActive = True
            if algo.positions:
                algo.exit_all_positions()
            else:
                algo.update_metrics()
                algo.active = False
    return not oldActive
