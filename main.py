from alpacaAPI import alpaca, alpacaPaper
from distribute_funds import distribute_funds
from marketHours import get_time, get_date, get_open_time, is_new_week_since
from get_tradable_assets import get_tradable_assets
from config import minAllocBP

# import algo classes
# from LongShort import LongShort
# from MeanReversion import MeanReversion
from ReturnsReversion import ReturnsReversion

# initialize algos
# longShort = LongShort(minAllocBP, 0.01)
# meanReversion = MeanReversion(minAllocBP, 0.01, 7)
returnsReversion7 = ReturnsReversion(minAllocBP, 0.01, 7)
returnsReversion30 = ReturnsReversion(minAllocBP, 0.01, 30)
returnsReversion90 = ReturnsReversion(minAllocBP, 0.01, 90)
algos = [returnsReversion7, returnsReversion30, returnsReversion90]

# TODO: dataStreaming

lastRebalanceDate = "0001-01-01"
# TODO: read date from file or prompt to coninue
get_tradable_assets(algos)
while True:
    # if is_new_week_since(lastRebalanceDate): distribute_funds(algos)

    # get tradable assets
    if (
        get_time(1) < get_open_time() and # no more than 1 hr before market open
        Algo.lastSymbolUpdate != get_date() # haven't udpated today
    ): 
        get_tradable_assets()


    # if after market close:
    #     for algo in algos:
    #         algo.update_metrics()

    # write data from bar and order update buffers to Algo.assets, orders, positions
    
    for algo in algos: algo.tick() # in parallel

    # write data from algos.orders to Algo.orders, positions

    # wait remainder of 1 sec

