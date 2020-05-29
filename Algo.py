# base class for algos

from alpacaAPI import alpaca, alpacaPaper
from warn import warn
import statistics

class Algo:
    assets = {}
    paperOrders = [] # [{id, symbol, quantity, price, algo}]
    liveOrders = []
    paperPositions = {} # {symbol: quantity}
    livePositions = {}

    def __init__(self, cash=10000, maxPosFrac=0.01, tags=[], category=None):
        # paper / live
        self.alpaca = alpacaPaper # always call alpaca through self.alpaca
        self.allOrders = Algo.paperOrders # have to be careful not to break these references
        self.allPositions = Algo.paperPositions

        # state variables
        self.cash = cash # buying power NOT literal cash
        self.equity = cash # udpated daily
        self.positions = {} # {symbol: quantity}
        self.orders = [] # [{id, symbol, quantity, price}]
        #  order quantity is positive for buy and negative for sell
        #  order price is an estimate

        # properties
        self.maxPosFrac = maxPosFrac # maximum fraction of buyingPower to hold in a position (at time of order)
        self.tags = tags # e.g. 'long', 'short', 'longShort', 'intraday', 'daily', 'weekly', 'overnight'
        self.category = category # e.g. 'meanReversion', 'momentum', 'scalping', etc

        # risk metrics


        # performance metrics
        self.history = [] # [{time, prevTime, equity, prevEquity, cashFlow, growthFrac}]
        # change in equity minus cash allocations over previous equity
        # extra fields are kept for error proofing
        self.mean = 0 # average daily growth
        self.stdev = 0 # sample standard deviation of daily growth

        self.live = False # whether using real money
        self.allocFrac = 0

    def update_metrics(self):
        # TODO: check each datapoint is one market day apart
        growth = [day['growthFrac'] for day in self.history]
        self.mean = statistics.mean(growth)
        self.stdev = statistics.stdev(growth)

    def set_live(self, live):

        # check argument
        if self.live == live:
            warn(f'{self}.set_live({live}) did not change state')
            return
        
        # TODO: cancel orders
        # TODO: close positions
        # TODO: udpate account?

        # update flag and api
        self.live = live
        if live:
            self.alpaca = alpaca
            self.allOrders = Algo.liveOrders
            self.allPositions = Algo.livePositions
        else:
            self.alpaca = alpacaPaper
            self.allOrders = Algo.paperOrders
            self.allPositions = Algo.paperPositions
