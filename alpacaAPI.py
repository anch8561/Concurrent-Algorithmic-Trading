import alpaca_trade_api as tradeapi
from credentials import paper, live, paperTest, liveTest

testing = True
print(f'Testing: {testing}')

# get credentials
if testing:
    liveCreds = liveTest.creds
    paperCreds = paperTest.creds
else:
    liveCreds = live.creds
    paperCreds = paper.creds

# initialize alpaca api
alpacaLive = tradeapi.REST(*liveCreds)
alpacaPaper = tradeapi.REST(*paperCreds)

# get polygon access for old paper accounts
if testing:
    polyAccess = tradeapi.REST(*live.creds)
    alpacaLive.polygon = polyAccess.polygon
    alpacaPaper.polygon = polyAccess.polygon

# initialize StreamConn
connLive = tradeapi.StreamConn(*liveCreds, data_stream='polygon')
connPaper = tradeapi.StreamConn(*paperCreds, data_stream='polygon')
