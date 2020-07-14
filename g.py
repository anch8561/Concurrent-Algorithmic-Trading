verbose = False

TTOpen = None # timedelta; time until open (open time - current time)
TTClose = None # timedelta; time until close (close time - current time)

assets = {} # {symbol: {sec, min, day}}
# 'sec': DataFrame; past 100 second bars and indicators
# 'min': DataFrame; past 100 minute bars and indicators
# 'day': DataFrame; past 100 day bars and indicators
# e.g. assets['AAPL']['day'].columns = open, close, high, low, volume, <indicator_1>, etc

paperOrders = {} # {orderID: {symbol, qty, limit, longShort, enterExit, algo}}
liveOrders = {}

paperPositions = {} # {symbol: {qty, basis}}
livePositions = {}

tickingAlgos = False
