alpacaLive = None # alpaca trade api REST object with live credentials
alpacaPaper = None # alpaca trade api REST object with paper credentials
connLive = None # alpaca trade api StreamConn object with live credentials
connPaper = None # alpaca trade api StreamConn object with paper credentials

TTOpen = None # timedelta until today's market open (or next market open if today is not a market day)
TTClose = None # timedelta until today's market close (or next market close if today is not a market day)

lastBarReceivedTime = None # datetime when last bar was received in streaming

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
