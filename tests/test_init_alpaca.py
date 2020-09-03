import credentials
import init_alpaca

from unittest.mock import patch, Mock, call


def test_init_alpaca():
    # setup
    class tradeapi:
        class alpaca:
            polygon = 1234
        REST = Mock(return_value=alpaca)
        StreamConn = Mock()

    # test
    with patch('init_alpaca.tradeapi', tradeapi):
        init_alpaca.init_alpaca('dev')

        # REST
        calls = [
            call(*credentials.dev.live),
            call(*credentials.dev.paper),
            call(*credentials.prod.live)]
        tradeapi.REST.assert_has_calls(calls)
        assert tradeapi.REST.call_count == 3

        # StreamConn
        calls = [
            call(*credentials.dev.live, data_stream='polygon'),
            call(*credentials.dev.paper, data_stream='polygon')]
        tradeapi.StreamConn.assert_has_calls(calls)
        assert tradeapi.StreamConn.call_count == 2
