# base class for algos

class Algo:
    stocks = {}
    b_marginCall = False # if CashAllocation is designed right, this should never happen
    # It also might be taken care of server side

    def __init__(self, cash, maxPositionFraction):
        self.cash = cash
        self.maxPositionFraction = maxPositionFraction
        self.positions = {} # {symbol: quantity}
        self.orders = [] # [order_id]

        self.log = ''

        self.alpha = 0
        self.beta = 0
        self.allocationFraction = 0