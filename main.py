# Initialize indicators, algorithms, and streaming, then enter main loop.
# Allocate buying power once per week. Update assets and metrics daily.
# Tick algorithms at regular intervals.

from algoClasses import Algo
from algos import intradayAlgos, overnightAlgos, multidayAlgos
from alpacaAPI import connLive, connPaper
from config import marketCloseTransitionMinutes
from datetime import timedelta
from distribute_funds import distribute_funds
from indicators import indicators
from marketHours import get_time, get_date, get_open_time, get_close_time, is_new_week_since
from streaming import stream
from threading import Thread
from update_tradable_assets import update_tradable_assets

from time import sleep

# FIX: account reset
from alpacaAPI import alpacaPaper
alpacaPaper.cancel_all_orders()
alpacaPaper.close_all_positions()

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
            if any(algo.positions[symbol]['qty'] for symbol in algo.positions):
                algo.exit_all_positions()
            else:
                algo.update_metrics()
                algo.active = False
    return not oldActive

# TODO: read date from file or prompt to coninue
lastRebalanceDate = "0001-01-01"

state = 'night' # day, night
# TODO: load positions and check state

# get assets
update_tradable_assets(True, 100)

# allocate buying power
for algo in overnightAlgos:
    algo.buyPow['long'] = 10000
    algo.buyPow['short'] = 10000
    algo.equity['long'] = 10000
    algo.equity['short'] = 10000
for algo in intradayAlgos:
    algo.buyPow['long'] = 10000
    algo.buyPow['short'] = 10000
    algo.equity['long'] = 10000
    algo.equity['short'] = 10000


# stream alpaca
channels = ['account_updates', 'trade_updates']
for symbol in Algo.assets:
    channels += [f'AM.{symbol}'] # TODO: second bars
Thread(target=stream, args=(connPaper, channels)).start()
print(f'Streaming {len(Algo.assets)} tickers')

# main loop
print('Entering main loop')
while True:
    # update buying power
    # if is_new_week_since(lastRebalanceDate):
    #     distribute_funds()

    # get time
    time = get_time()
    Algo.TTOpen = get_open_time() - time # time til open
    Algo.TTClose = get_close_time() - time # time til close

    # update symbols
    # if (
    #     lastSymbolUpdate != get_date() and # weren't updated today
    #     Algo.TTOpen < timedelta(hours=1) # < 1 hour until market open
    # ):
    #     update_tradable_assets()
    #     lastSymbolUpdate = get_date()

    # update indicators
    print('Ticking indicators')
    for ii, indicator in enumerate(indicators):
        print(f'Ticking indicator {ii+1} / {len(indicators)}\t{indicator.name}')
        indicator.tick()
    
    # update algos
    print('Ticking algos')
    if ( # market is open and overnight positions are open
        state == 'night' and
        Algo.TTOpen < timedelta(0) and # market is open
        Algo.TTClose > timedelta(minutes=marketCloseTransitionMinutes) # not closing soon
    ):
        if handoff_BP(overnightAlgos, intradayAlgos): # true when done
            for algo in intradayAlgos: algo.active = True
            state = 'day'
            print('state = day')
        else: print('Transitioning to intraday algos')

    elif ( # market is open and overnight positions are closed
        state == 'day' and
        Algo.TTOpen < timedelta(0) and # market is open
        Algo.TTClose > timedelta(minutes=marketCloseTransitionMinutes) # not closing soon
    ):
        for algo in intradayAlgos: algo.tick() # in parallel
        for algo in multidayAlgos: algo.tick()

    elif ( # market will close soon and intraday positions are open
        state == 'day' and
        Algo.TTClose > 0 and # market is open
        Algo.TTClose <= timedelta(minutes=marketCloseTransitionMinutes) # closing soon
    ):
        if handoff_BP(intradayAlgos, overnightAlgos): # true when done
            for algo in overnightAlgos: algo.active = True
            state = 'night'
            print('state = night')
        else: print('Transitioning to overnight algos')

    elif ( # market will close soon and intraday positions are closed
        state == 'night' and
        Algo.TTClose > 0 and # market is open
        Algo.TTClose <= timedelta(minutes=marketCloseTransitionMinutes) # closing soon
    ):
        for algo in overnightAlgos: algo.tick()
    else:
        print('Market is closed')

    # TODO: wait remainder of 1 sec
    sleep(10)
