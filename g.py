TTOpen = None # timedelta; time until open (open time - current time)
TTClose = None # timedelta; time until close (close time - current time)

assets = {'sec': {}, 'min': {}, 'day': {}} # dict of dicts of dataframes {barFreq: symbol: df}
# 'sec': dict of dataframes; past 100 second bars and indicators for each symbol
# 'min': dict of dataframes; past 100 minute bars and indicators for each symbol
# 'day': dict of dataframes; past 100 day bars and indicators for each symbol
# e.g. assets['day']['AAPL'].columns = open, close, high, low, volume, <indicator_1>, etc

paperOrders = {} # {orderID: {symbol, qty, limit, longShort, enterExit, algo}}
liveOrders = {}

paperPositions = {} # {symbol: {qty, basis}}
livePositions = {}

tickingAlgos = False
