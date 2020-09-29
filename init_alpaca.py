import credentials
import globalVariables as g

import alpaca_trade_api as tradeapi
from logging import getLogger

log = getLogger('main')

def init_alpaca(environment):
    # environment: 'dev', 'test', or 'prod'; which credentials to use

    log.warning(f'Entering {environment} environment')
    
    try: # get credentials
        creds = getattr(credentials, environment)
    except Exception as e: log.exception(e)

    # initialize tradeapi
    g.alpacaLive = tradeapi.REST(*creds.live)
    g.alpacaPaper = tradeapi.REST(*creds.paper)

    # initialize StreamConn
    g.connLive = tradeapi.StreamConn(*creds.live, data_stream='polygon')
    g.connPaper = tradeapi.StreamConn(*creds.paper, data_stream='polygon')
