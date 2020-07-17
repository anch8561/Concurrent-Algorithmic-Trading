TTOpen = None # timedelta; time until open (open time - current time)
TTClose = None # timedelta; time until close (close time - current time)
lastBarReceivedTime = None

assets = {'sec': {}, 'min': {}, 'day': {}} # dict of dicts of dataframes {barFreq: symbol: df}
# 'sec': dict of dataframes; second bars and indicators for each symbol
# 'min': dict of dataframes; minute bars and indicators for each symbol
# 'day': dict of dataframes; day bars and indicators for each symbol
# e.g. assets['day']['AAPL'].columns = open, close, high, low, volume, <indicator_1>, etc

paperOrders = {} # {orderID: {symbol, qty, limit, longShort, enterExit, algo}}
liveOrders = {}

paperPositions = {} # {symbol: {qty, basis}}
livePositions = {}

processingTrade = False
