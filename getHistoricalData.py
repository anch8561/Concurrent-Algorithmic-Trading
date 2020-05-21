import alpaca_trade_api as tradeapi
from credentials import *

paperApi = tradeapi.REST(*paper.creds)
liveApi = tradeapi.REST(*live.creds)


x = liveApi.polygon.all_tickers()
print(x[0])


x = liveApi.polygon.historic_agg_v2('TSLA', 1, 'minute', '2018-02-02', '2018-02-03')
print(len(x))
print(x[0])
print(x[1])
print(x[-1])
