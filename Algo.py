# base class for algos

from alpacaAPI import alpaca, alpacaPaper
import warnings

class Algo:
    stocks = {}

    def __init__(self, cash=10000, maxPositionFraction=0.01):
        # state variables
        self.alpaca = alpacaPaper # always call alpaca through this (changes with profitability)
        self.cash = cash
        self.equity = cash
        self.maxPositionFraction = maxPositionFraction
        self.positions = {} # {symbol: quantity}
        self.orders = [] # [order_id]

        self.log = ''

        # risk metrics


        # performance metrics
        self.profitable = False # whether using real money
        self.alpha = 0
        self.beta = 0
        self.allocationFraction = 0
    
    def set_profitable(self, profitable):
        if self.profitable == profitable:
            warnings.warn(f'{self}.set_profitable({profitable}) did not change state')
            return
        
        # cancel orders
        # close positions
        # udpate account?

        # update flag and api
        self.profitable = profitable
        if profitable: self.alpaca = alpaca
        else: self.alpaca = alpacaPaper

