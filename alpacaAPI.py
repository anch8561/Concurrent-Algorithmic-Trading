# wrapper for toggling testing state

import alpaca_trade_api as tradeapi
from credentials import *

testing = True

# get credentials
if testing:
    liveCreds = liveTest.creds
    paperCreds = paperTest.creds
else:
    liveCreds = live.creds
    paperCreds = paper.creds

# initialize alpaca api
alpaca = tradeapi.REST(*liveCreds)
alpacaPaper = tradeapi.REST(*paperCreds)

# get polygon access for old paper accounts
if testing:
    polyAccess = tradeapi.REST(*live.creds)
    alpaca.polygon = polyAccess.polygon
    alpacaPaper.polygon = polyAccess.polygon

# initialize StreamConn
conn = tradeapi.StreamConn(paper.apiKey, paper.secretKey, paperPoly.endpoint)
connPaper = tradeapi.StreamConn(paper.apiKey, paper.secretKey, paperPoly.endpoint)