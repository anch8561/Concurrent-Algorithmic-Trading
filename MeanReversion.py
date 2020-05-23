from Algo import Algo

import alpaca_trade_api as tradeapi
from credentials import *

alpaca = tradeapi.REST(*paper.creds)

class MeanReversion(Algo):
    def __init__(self, cash, maxPositionFraction=0.01, numLookbackDays=7):
        self.numLookbackDays = numLookbackDays
        super().__init__(cash, maxPositionFraction)

        self.lastRebalanceDate = "0000-00-00"

    def tick(self):
        if self.isNewWeekSince(self.lastRebalanceDate) and \
            self.getTime() > "11-00-00": self.rebalance

    def rebalance(self):
        # get stock growth during lookback window
        assets = alpaca.list_assets('active', 'us_equity')
        symbols = [asset.symbol for asset in assets]
        fromDate = self.getDate(-self.numLookbackDays)
        toDate = self.getDate()
        returns = []
        for symbol in symbols:
            bar = alpaca.polygon.historic_agg_v2( \
                symbol, self.numLookbackDays, 'day', fromDate, toDate)[0]
            returns.append( ((bar.close - bar.open)/bar.open, symbol) )
        returns = sorted(returns)

        # long 

    def onMarketClose(self):
        pass
