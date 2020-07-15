import g 
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from alpacaAPI import connLive, connPaper
from config import marketCloseTransitionMinutes
from distribute_funds import distribute_funds
from indicators import indicators
from streaming import stream, process_all_trades
from timing import update_timing, get_date, is_new_week_since
from update_tradable_assets import update_tradable_assets
from warn import warn

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

# start algos
for algo in multidayAlgos: algo.start()
state = 'day' # day, night
if state == 'night':
    for algo in overnightAlgos: algo.start()
elif state == 'day':
    for algo in intradayAlgos: algo.start()

# main loop
lastAllocUpdate = None
lastSymbolUpdate = None
marketIsOpen = True

try:
    print('Entering main loop')
    while True:
        update_timing()

        # update buying power allocation
        if (
            lastAllocUpdate != get_date() and # wasn't updated today
            g.TTOpen < timedelta(hours=1) # < 1 hour until market open:
        ):
            # stop algos
            g.tickingAlgos = True
            activeAlgos = []
            for algo in allAlgos:
                if algo.active:
                    activeAlgos.append(algo)
                    algo.stop()
            
            # allocate buying power
            distribute_funds()
            lastAllocUpdate = get_date()
            for algo in allAlgos: # FIX: no performance data
                algo.buyPow['long'] = 5000
                algo.buyPow['short'] = 5000
            
            # restart algos
            for algo in activeAlgos: algo.start()
            g.tickingAlgos = False

        # update tradable assets
        if (
            lastSymbolUpdate != get_date() and # weren't updated today
            g.TTOpen < timedelta(hours=1) # < 1 hour until market open
        ):
            # update symbols
            update_tradable_assets(10)
            lastSymbolUpdate = get_date()

            # update channels
            channels = ['account_updates', 'trade_updates']
            for symbol in g.assets['min']:
                channels += [f'AM.{symbol}']
            
            # start new stream thread
            streamThread = Thread(target=stream, args=(connPaper, channels))
            streamThread.start()
            # NOTE: need way to update asset channels if not restarting main each day
        
        # tick algos
        if ( # market is open
            g.TTOpen < timedelta(0) and
            g.TTClose > timedelta(0)
        ):
            marketIsOpen = True
            if all(bars['ticked'].iloc[-1] == False for bars in g.assets['min'].values()): # new bars
                closingSoon = g.TTClose <= timedelta(minutes=marketCloseTransitionMinutes)

                # block trade updates
                g.tickingAlgos = True
                while g.processingTrade: pass

                # tick algos
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
                
                # update assets
                for bars in g.assets['min'].values():
                    jj = bars.columns.get_loc('ticked')
                    bars.iloc[-1, jj] = True
                
                # unblock trade updates
                g.tickingAlgos = False
                process_all_trades()

                print('Waiting for bars')
        else:
            if marketIsOpen:
                marketIsOpen = False
                print('Market is closed')
            sleep(1)

except KeyboardInterrupt:
    for algo in allAlgos:
        if algo.active:
            print(f"Stopping: {algo}")
            algo.stop()
            pass #Remove pass to require two "Ctrl-C"s to exit
