import credentials
import globalVariables as g
from init_alpaca import init_alpaca

import alpaca_trade_api as tradeapi

def test_init_alpaca():
    # get test account id
    init_alpaca('dev')
    testID = g.alpacaLive.get_account().id

    # get real account id
    creds = getattr(credentials, 'dev')
    realID = tradeapi.REST(*creds.live).get_account().id

    # compare id
    assert testID == realID

    # NOTE: does not test polygon access or StreamConn
