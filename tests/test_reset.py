import globalVariables as g
from reset import reset

from unittest.mock import patch

def test_reset(allAlgos):
    allAlgos[1].orders['a'] = 123
    allAlgos[2].positions['b'] = 456
    g.liveOrders['c'] = 789
    g.paperOrders['d'] = 987
    g.livePositions['e'] = 654
    g.paperPositions['f'] = 321
    with patch('globalVariables.alpacaLive'), \
    patch('globalVariables.alpacaPaper'):
        reset(allAlgos)
        g.alpacaLive.cancel_all_orders.assert_called_once()
        g.alpacaLive.close_all_positions.assert_called_once()
        g.alpacaPaper.cancel_all_orders.assert_called_once()
        g.alpacaPaper.close_all_positions.assert_called_once()
        for algo in allAlgos:
            assert algo.orders == {}
            assert algo.positions == {}
        assert g.liveOrders == {}
        assert g.paperOrders == {}
        assert g.livePositions == {}
        assert g.paperPositions == {}
