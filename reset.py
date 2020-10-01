import globalVariables as g

from logging import getLogger

log = getLogger('main')

def reset(allAlgos):
    log.warning('Cancelling orders and closing positions')
    # reset account orders and positions
    for alpaca in (g.alpacaLive, g.alpacaPaper):
        alpaca.cancel_all_orders()
        alpaca.close_all_positions()
    
    # reset algo orders and positions
    for algo in allAlgos:
        algo.orders.clear()
        algo.positions.clear()

    # reset global orders and positions
    g.liveOrders.clear()
    g.paperOrders.clear()

    g.livePositions.clear()
    g.paperPositions.clear()
