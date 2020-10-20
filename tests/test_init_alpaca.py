import credentials
import init_alpaca

from unittest.mock import patch, Mock, call


def test_init_alpaca():
    with patch('init_alpaca.tradeapi') as tradeapi:
        init_alpaca.init_alpaca('dev')
        tradeapi.REST.assert_called_once_with(*credentials.dev.paper)
        tradeapi.StreamConn.assert_called_once_with(
            *credentials.dev.paper, data_stream='polygon')
