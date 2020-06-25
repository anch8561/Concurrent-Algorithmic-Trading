# Initialize indicators, algorithms, and streaming, then enter main loop.
# Allocate buying power once per week. Update assets and metrics daily.
# Tick algorithms at regular intervals.

from algoClasses import Algo
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from config import marketCloseTransitionMinutes
from datetime import timedelta
from distribute_funds import distribute_funds
from indicators import indicators
from marketHours import get_time, get_date, get_open_time, get_close_time, is_new_week_since
from update_tradable_assets import update_tradable_assets

# TODO: dataStreaming


# TODO: read date from file or prompt to coninue
lastRebalanceDate = "0001-01-01"

# main loop

state = 'night' # day, night
# TODO: load positions and check state
while True:
    # update buying power
    if is_new_week_since(lastRebalanceDate):
        distribute_funds(intradayAlgos, overnightAlgos, multidayAlgos)

    # get time
    time = get_time()
    TTOpen = get_open_time() - time # time til open
    TTClose = get_close_time() - time # time til close

    # update symbols
    if (
        lastSymbolUpdate != get_date() and # weren't updated today
        TTOpen < timedelta(hours=1) # < 1 hour until market open
    ):
        update_tradable_assets(allAlgos)
        lastSymbolUpdate = get_date()

    # TODO: update bars and orders

    # update indicators
    for indicator in indicators: indicator.tick()
    
    # update algos
    if ( # market is open and overnight positions are open
        state == 'night' and
        TTOpen < timedelta(0) and
        TTClose > timedelta(minutes=marketCloseTransitionMinutes)
    ):
        if handoff_BP(overnightAlgos, intradayAlgos): # true when done
            for algo in intradayAlgos: algo.active = True
            state = 'day'

    elif ( # market is open and overnight positions are closed
        state == 'day' and
        TTClose > timedelta(minutes=marketCloseTransitionMinutes)
    ):
        for algo in intradayAlgos: algo.tick(TTOpen, TTClose) # in parallel
        for algo in multidayAlgos: algo.tick(TTOpen, TTClose)

    elif ( # market will close soon and intraday positions are open
        state == 'day' and
        TTClose <= timedelta(minutes=marketCloseTransitionMinutes)
    ):
        if handoff_BP(intradayAlgos, overnightAlgos): # true when done
            for algo in overnightAlgos: algo.active = True
            state = 'night'

    elif ( # market will close soon and intraday positions are closed
        state == 'night' and
        TTClose <= timedelta(minutes=marketCloseTransitionMinutes)
    ):
        for algo in overnightAlgos: algo.tick()

    # TODO: update allOrders and allPositions

    # TODO: wait remainder of 1 sec

def handoff_BP(oldAlgos, newAlgos):
    # oldAlgos: list of algos to get BP from
    # newAlgos: list of algos to give BP to
    # returns: bool; whether handoff is complete
    
    # exit positions and update metrics
    # FIX: need partial handoff in case an algo can't exit a position
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
