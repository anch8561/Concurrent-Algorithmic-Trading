from alpacaAPI import alpaca, alpacaPaper
from distribute_funds import distribute_funds
from marketHours import is_new_week_since
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

lastRebalanceDate = "0000-00-00"
# TODO: read date from file or prompt to coninue
while True:
    # if is_new_week_since(lastRebalanceDate): distribute_funds(algos)

    # if before market open:
    #     Algo.update_assets()

    # if after market close:
    #     for algo in algos:
    #         algo.update_metrics()

    for algo in algos: algo.tick()

