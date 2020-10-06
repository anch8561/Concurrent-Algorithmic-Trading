import globalVariables as g
from reset import reset

from unittest.mock import patch

def test_reset(allAlgos):
    # setup
    allAlgos[1].orders['a'] = 123
    allAlgos[2].positions['b'] = 456
    g.orders['c'] = 987
    g.positions['d'] = 321

    # test
    with patch('globalVariables.alpacaLive'), \
    patch('globalVariables.alpacaPaper'):
        reset(allAlgos)
        g.alpaca.cancel_all_orders.assert_called_once()
        g.alpaca.close_all_positions.assert_called_once()

        for algo in allAlgos:
            assert algo.orders == {}
            assert algo.positions == {}

        assert g.orders == {}
        assert g.positions == {}
