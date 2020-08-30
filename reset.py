import globalVariables as g
from algos import allAlgos

from logging import getLogger

log = getLogger()

def reset():
    log.warning('Cancelling orders and closing positions')
    # reset account orders and positions
    for alpaca in (g.alpacaLive, g.alpacaPaper):
        alpaca.cancel_all_orders()
        alpaca.close_all_positions()
    
    # reset algo orders and positions
    for algo in allAlgos:
        algo.orders = {}
        algo.positions = {}

    # reset global orders and positions
    g.liveOrders = {}
    g.paperOrders = {}

    g.livePositions = {}
    g.paperPositions = {}
