import credentials
import globalVariables as g
from init_alpaca import init_alpaca

import alpaca_trade_api as tradeapi
from unittest.mock import Mock, call

def test_init_alpaca():
    # setup
    class fakeCreds:
        live = ('abc', '123', 'web.site')
        paper = ('xyz', '890', 'site.web')
    credentials.dev = fakeCreds
    credentials.test = fakeCreds
    credentials.prod = fakeCreds

    class alpaca:
        polygon = 1234
    tradeapi.REST = Mock(return_value=alpaca)
    tradeapi.StreamConn = Mock()

    # test
    init_alpaca('dev')
    calls = [
        call(*credentials.dev.live),
        call(*credentials.dev.paper),
        call(*credentials.prod.live)]
    tradeapi.REST.assert_has_calls(calls)
    calls = [
        call(*credentials.dev.live, data_stream='polygon'),
        call(*credentials.dev.paper, data_stream='polygon')]
    tradeapi.StreamConn.assert_has_calls(calls)
