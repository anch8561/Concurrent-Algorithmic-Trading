from pytz import timezone

alpacaLive = None # alpaca trade api REST object with live credentials
alpacaPaper = None # alpaca trade api REST object with paper credentials
connLive = None # alpaca trade api StreamConn object with live credentials
connPaper = None # alpaca trade api StreamConn object with paper credentials

nyc = timezone('America/New_York')
now = None # datetime
lastBarReceivedTime = None # datetime when last bar was received in streaming
TTOpen = None # timedelta until today's market open (or next market open if today is not a market day)
TTClose = None # timedelta until today's market close (or next market close if today is not a market day)

assets = {'sec': {}, 'min': {}, 'day': {}} # dict of dicts of dataframes {barFreq: symbol: df}
# 'sec': dict of dataframes; second bars and indicators for each symbol
# 'min': dict of dataframes; minute bars and indicators for each symbol
# 'day': dict of dataframes; day bars and indicators for each symbol
# e.g. assets['day']['AAPL'].columns = open, close, high, low, volume, <indicator_1>, etc

liveOrders = {} # {orderID: {symbol, qty, limit, longShort, enterExit, algo}}
paperOrders = {}
livePositions = {} # {symbol: {qty, basis}}
paperPositions = {}

processingTrade = False
