import g
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from alpacaAPI import connLive, connPaper
from config import marketCloseTransitionMinutes
from distribute_funds import distribute_funds
from indicators import indicators
from streaming import stream
from timing import update_timing, get_date, is_new_week_since
from update_tradable_assets import update_tradable_assets

from datetime import timedelta
from threading import Thread
from time import sleep

# FIX: account reset
print('Resetting account')
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
        if (
            algo.active and
            any(algo.positions[symbol]['qty'] for symbol in algo.positions)
        ):
            oldActive = True
            algo.exit_all_positions()
        else:
            algo.stop()
    return not oldActive

# get assets
update_timing()
update_tradable_assets(True, 100)

# allocate buying power
for algo in allAlgos:
    algo.buyPow['long'] = 10000
    algo.buyPow['short'] = 10000


# stream alpaca
channels = ['account_updates', 'trade_updates']
for symbol in g.assets:
    channels += [f'AM.{symbol}'] # TODO: second bars
Thread(target=stream, args=(connPaper, channels)).start()
print(f'Streaming {len(g.assets)} tickers')

lastAllocDate = "0001-01-01"
# TODO: read date from file or prompt to coninue

# start algos
for algo in multidayAlgos: algo.start()
state = 'night' # day, night
if state == 'night':
    for algo in overnightAlgos: algo.start()
elif state == 'day':
    for algo in intradayAlgos: algo.start()


# main loop
print('Entering main loop')
while True:
    update_timing()

    # update buying power
    # if is_new_week_since(lastAllocDate):
    #     distribute_funds()

    # update symbols
    # if (
    #     lastSymbolUpdate != get_date() and # weren't updated today
    #     g.TTOpen < timedelta(hours=1) # < 1 hour until market open
    # ):
    #     update_tradable_assets()
    #     lastSymbolUpdate = get_date()

    if ( # market is open
        g.TTOpen < timedelta(0) and
        g.TTClose > timedelta(0)
    ):
        closingSoon = g.TTClose <= timedelta(minutes=marketCloseTransitionMinutes)

        # update indicators
        print('Ticking indicators')
        for ii, indicator in enumerate(indicators):
            print(f'Ticking indicator {ii+1} / {len(indicators)}\t{indicator.name}')
            indicator.tick()
        
        # update algos
        print('Ticking algos')
        if state == 'night' and not closingSoon:
            if handoff_BP(overnightAlgos, intradayAlgos): # true when done
                for algo in intradayAlgos: algo.start()
                state = 'day'
                print('Intraday algos have buying power')
            else:
                print('Transitioning to intraday algos')

        elif state == 'day' and not closingSoon:
            for algo in intradayAlgos: algo.tick() # in parallel
            for algo in multidayAlgos: algo.tick()

        elif state == 'day' and closingSoon:
            if handoff_BP(intradayAlgos, overnightAlgos): # true when done
                for algo in overnightAlgos: algo.start()
                state = 'night'
                print('Overnight algos have buying power')
            else:
                print('Transitioning to overnight algos')

        elif state == 'night' and closingSoon:
            for algo in overnightAlgos: algo.tick() # in parallel
            for algo in multidayAlgos: algo.tick()
    else:
        print('Market is closed')

    # TODO: wait remainder of 1 sec
    sleep(10)
