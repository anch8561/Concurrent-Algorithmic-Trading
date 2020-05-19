class Algo:
    stocks = []

    def __init__(self, cash):
        self.cash = cash
        self.portfolio = []

        self.log = ''

        self.alpha = 0
        self.beta = 0
