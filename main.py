# Initialize indicators, algorithms, and streaming, then enter main loop.
# Allocate buying power once per week. Update assets and metrics daily.
# Tick algorithms at regular intervals.

import threading
from algoClasses import Algo
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from alpacaAPI import connLive, connPaper
from config import marketCloseTransitionMinutes
from datetime import timedelta
from distribute_funds import distribute_funds
from indicators import indicators
from marketHours import get_time, get_date, get_open_time, get_close_time, is_new_week_since
from streaming import stream
from update_tradable_assets import update_tradable_assets


# TODO: read date from file or prompt to coninue
lastRebalanceDate = "0001-01-01"

state = 'night' # day, night
# TODO: load positions and check state

# get assets
update_tradable_assets(allAlgos, True, 10) # FIX: debugging

# stream alpaca
channels = ['account_updates', 'trade_update']
alpacaLiveStream = threading.Thread(target=stream(connLive, channels))
alpacaLiveStream.start()
alpacaPaperStream = threading.Thread(target=stream(connPaper, channels))
alpacaPaperStream.start()

# stream polygon
channels = []
for symbol in Algo.assets.keys():
    channels += [f'A.{symbol}' , f'AM.{symbol}']
polygonStream = threading.Thread(target=stream(connLive, channels))
polygonStream.start()

def main_loop():
    # update buying power
    # if is_new_week_since(lastRebalanceDate):
    #     distribute_funds(intradayAlgos, overnightAlgos, multidayAlgos)

    # get time
    time = get_time()
    Algo.TTOpen = get_open_time() - time # time til open
    Algo.TTClose = get_close_time() - time # time til close

    # update symbols
    # if (
    #     lastSymbolUpdate != get_date() and # weren't updated today
    #     Algo.TTOpen < timedelta(hours=1) # < 1 hour until market open
    # ):
    #     update_tradable_assets(allAlgos)
    #     lastSymbolUpdate = get_date()

    # update indicators
    for indicator in indicators: indicator.tick()
    
    # update algos
    if ( # market is open and overnight positions are open
        state == 'night' and
        Algo.TTOpen < timedelta(0) and
        Algo.TTClose > timedelta(minutes=marketCloseTransitionMinutes)
    ):
        print('Transitioning to intraday algos')
        if handoff_BP(overnightAlgos, intradayAlgos): # true when done
            for algo in intradayAlgos: algo.active = True
            state = 'day'
            print('state = day')

    elif ( # market is open and overnight positions are closed
        state == 'day' and
        Algo.TTClose > timedelta(minutes=marketCloseTransitionMinutes)
    ):
        for algo in intradayAlgos: algo.tick() # in parallel
        for algo in multidayAlgos: algo.tick()

    elif ( # market will close soon and intraday positions are open
        state == 'day' and
        Algo.TTClose <= timedelta(minutes=marketCloseTransitionMinutes)
    ):
        print('Transitioning to overnight algos')
        if handoff_BP(intradayAlgos, overnightAlgos): # true when done
            for algo in overnightAlgos: algo.active = True
            state = 'night'
            print('state = night')

    elif ( # market will close soon and intraday positions are closed
        state == 'night' and
        Algo.TTClose <= timedelta(minutes=marketCloseTransitionMinutes)
    ):
        for algo in overnightAlgos: algo.tick()

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

# enter loop
from streaming import stream
stream()
