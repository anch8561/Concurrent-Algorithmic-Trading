# wrapper for toggling testing state

import alpaca_trade_api as tradeapi
from credentials import *

testing = True

if testing:
    liveCreds = liveTest.creds
    paperCreds = paperTest.creds
else:
    liveCreds = live.creds
    paperCreds = paper.creds

alpaca = tradeapi.REST(*liveCreds)
alpacaPaper = tradeapi.REST(*paperCreds)

conn = tradeapi.StreamConn(*liveCreds) # might need different endpoint
connPaper = tradeapi.StreamConn(*paperCreds)