from pytz import timezone
from threading import Lock

alpaca = None # alpaca_trade_api.REST
conn = None # alpaca_trade_api.StreamConn

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

orders = {} # {orderID: {symbol, qty, price, algoOrders}}
positions = {} # {symbol: {qty, basis}}

lock = Lock() # main and stream threads must acquire to access:
# assets, orders, positions, algo.buyPow, algo.orders, algo.positions
