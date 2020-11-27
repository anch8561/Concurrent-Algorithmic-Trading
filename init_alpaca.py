import credentials
import globalVariables as g

import alpaca_trade_api as tradeapi
import requests
from logging import getLogger

log = getLogger('main')

def init_alpaca(environment):
    # environment: 'dev', 'test', or 'prod'; which credentials to use

    log.warning(f'Entering {environment} environment')
    
    try: # get credentials
        creds = getattr(credentials, environment)
    except Exception as e: log.exception(e)

    # initialize tradeapi
    g.alpaca = tradeapi.REST(*creds.paper)
    g.alpaca._session.mount('https://', 
        requests.adapters.HTTPAdapter(pool_maxsize=100))

    # initialize StreamConn
    g.conn = tradeapi.StreamConn(*creds.paper, data_stream='polygon')
