import g 
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from alpacaAPI import connLive, connPaper
from config import marketCloseTransitionMinutes
from distribute_funds import distribute_funds
from indicators import indicators
from populate_assets import populate_assets
from streaming import stream, process_all_trades
from timing import update_time
from warn import warn

from datetime import timedelta
from threading import Thread
from time import sleep

# allocate buying power
distribute_funds()

# FIX: no performance data
for algo in allAlgos:
    algo.buyPow['long'] = 5000
    algo.buyPow['short'] = 5000

# populate assets
populate_assets(10)

# start streaming
channels = ['account_updates', 'trade_updates']
for symbol in g.assets['min']:
    channels += [f'AM.{symbol}']
Thread(target=stream, args=(connPaper, channels)).start()

# start active algos
print('Starting active algos')
for algo in allAlgos:
    if algo.active:
        print(f'Starting {algo.name}')
        algo.start()

# main loop
print('Entering main loop')
marketIsOpen = True
state = 'night'
try:
    while True:
        update_time()

        if ( # market is open
            g.TTOpen < timedelta(0) and
            g.TTClose > timedelta(0)
        ):
            if not marketIsOpen:
                marketIsOpen = True
                print('Market is open')

            # check for new minute bars
            if all(bars['ticked'].iloc[-1] == False for bars in g.assets['min'].values()):
                closingSoon = g.TTClose <= timedelta(minutes=marketCloseTransitionMinutes)

                # tick algos
                if state == 'night' and not closingSoon:
                    print('Deactivating overnight algos')
                    for algo in overnightAlgos: algo.deactivate()
                    
                    if not any(algo.active for algo in overnightAlgos):
                        print('Activating intraday algos')
                        for algo in intradayAlgos: algo.activate()
                        state = 'day'

                elif state == 'day' and not closingSoon:
                    for algo in intradayAlgos: algo.tick() # TODO: parallel

                elif state == 'day' and closingSoon:
                    print('Deactivating intraday algos')
                    for algo in intradayAlgos: algo.deactivate()
                    
                    if not any(algo.active for algo in intradayAlgos):
                        print('Activating overnight algos')
                        for algo in overnightAlgos: algo.activate()
                        state = 'night'

                elif state == 'night' and closingSoon:
                    for algo in overnightAlgos: algo.tick() # TODO: parallel
                
                # set ticked
                for bars in g.assets['min'].values():
                    jj = bars.columns.get_loc('ticked')
                    bars.iloc[-1, jj] = True

                # process trade updates
                process_all_trades()

                print('Waiting for bars')
            
            # TODO: check for new day bars (possibly in new thread)
        else:
            if marketIsOpen:
                marketIsOpen = False
                print('Market is closed')
            sleep(1)

except KeyboardInterrupt: # stop active algos
    print('Stopping active algos')
    for algo in allAlgos:
        if algo.active:
            print(f"Stopping {algo.name}")
            algo.stop()
            pass #Remove pass to require two "Ctrl-C"s to exit
