import globalVariables as g 
from algos import intradayAlgos, overnightAlgos, multidayAlgos, allAlgos
from alpacaAPI import connLive, connPaper
from config import marketCloseTransitionMinutes
from allocate_buying_power import allocate_buying_power
from indicators import indicators
from populate_assets import populate_assets
from streaming import stream, process_all_trades, compile_day_bars
from timing import update_time, get_time, get_date
from warn import warn

import sys
from datetime import timedelta
from threading import Thread
from time import sleep

print(get_date(), get_time())

# allocate buying power
allocate_buying_power()

# FIX: no performance data
for algo in allAlgos:
    algo.buyPow['long'] = 5000
    algo.buyPow['short'] = 5000

# populate assets
populate_assets(30)

# start streaming
channels = ['account_updates', 'trade_updates']
for symbol in g.assets['min']:
    channels += [f'AM.{symbol}']
Thread(target=stream, args=(connPaper, channels)).start()

# start active algos
print('Starting active algos')
for algo in allAlgos:
    if algo.active:
        print(f'\tStarting {algo.name}')
        algo.start()

# main loop
print(get_date(), get_time())
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
            print()
            sleep(10)
            for symbol, bars in g.assets['min'].items():
                print(f'{symbol}\t{bars.index[-1]}\t{bars.ticked.iloc[-1]}')
            if any(bars['ticked'].iloc[-1] == False for bars in g.assets['min'].values()):
                closingSoon = g.TTClose <= timedelta(minutes=marketCloseTransitionMinutes)

                # tick algos
                print('Ticking algos')
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
                        compile_day_bars()

                elif state == 'night' and closingSoon:
                    for algo in overnightAlgos: algo.tick() # TODO: parallel
                    for algo in multidayAlgos: algo.tick() # TODO: parallel
                
                # set ticked
                for bars in g.assets['min'].values():
                    jj = bars.columns.get_loc('ticked')
                    bars.iloc[-1, jj] = True
                    # FIX: only mark some symbols

                # process trade update backlog
                print('Processing trade update backlog')
                process_all_trades()

                print(f'{get_time()}\tWaiting for bars')
            
            # TODO: check for new day bars (possibly in new thread)
        else:
            if marketIsOpen:
                marketIsOpen = False
                print('Market is closed')
            sleep(1)

except Exception as e: # stop active algos
    print('Stopping active algos')
    for algo in allAlgos:
        if algo.active:
            print(f'\tStopping {algo.name}')
            algo.stop()
    print(e)
