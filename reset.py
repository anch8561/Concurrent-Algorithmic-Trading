import globalVariables as g

from logging import getLogger

log = getLogger('main')

def reset(allAlgos):
    log.warning('Cancelling orders and closing positions')
    # reset account orders and positions
    g.alpaca.cancel_all_orders()
    g.alpaca.close_all_positions()
    
    # reset algo orders and positions
    for algo in allAlgos:
        algo.orders.clear()
        algo.positions.clear()

    # reset global orders and positions
    g.orders.clear()
    g.positions.clear()
