import credentials
import globalVariables as g
from warn import warn

import alpaca_trade_api as tradeapi

def init_alpaca(environment):
    # environment: 'dev', 'test', or 'prod'; which credentials to use
    
    try: # get credentials
        creds = getattr(credentials, environment)
    except Exception as e: warn(e)

    # initialize tradeapi
    g.alpacaLive = tradeapi.REST(*creds.live)
    g.alpacaPaper = tradeapi.REST(*creds.paper)

    # get polygon access for old paper accounts
    polyAccess = tradeapi.REST(*credentials.prod.live)
    g.alpacaLive.polygon = polyAccess.polygon
    g.alpacaPaper.polygon = polyAccess.polygon

    # initialize StreamConn
    g.connLive = tradeapi.StreamConn(*creds.live, data_stream='polygon')
    g.connPaper = tradeapi.StreamConn(*creds.paper, data_stream='polygon')
