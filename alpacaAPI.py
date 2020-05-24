# wrapper for toggling testing state

import alpaca_trade_api as tradeapi
from credentials import *

alpaca = tradeapi.REST(*liveTest.creds)
alpacaPaper = tradeapi.REST(*paperTest.creds)
