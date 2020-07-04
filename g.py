TTOpen = None # timedelta; time until open (open time - current time)
TTClose = None # timedelta; time until close (close time - current time)

assets = {} # {symbol: {easyToBorrow, secBars, minBars, dayBars, <various indicators>}}
# 'shortable': bool; whether easy_to_borrow on alpaca
# 'secBars': pd.dataframe; past 10k second bars
# 'minBars': pd.dataframe; past 1k minute bars
# 'dayBars': pd.dataframe; past 100 day bars

paperOrders = {} # {orderID: {symbol, qty, limit, longShort, enterExit, algo}}
liveOrders = {}

paperPositions = {} # {symbol: {qty, basis}}
livePositions = {}

# streaming buffers
writing = False
secBars = []
minBars = []
orderUpdates = []
