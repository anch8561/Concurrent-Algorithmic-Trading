

from Algo import Algo
from marketHours import *

class MeanReversion(Algo):
    def __init__(self, cash, maxPosFrac=0.01, numLookbackDays=7, upperLimitFrac):
        self.numLookbackDays = numLookbackDays
        tags = []
        super().__init__(cash, maxPosFrac, tags)

        self.lastRebalanceDate = "0000-00-00"

    def tick(self):
        if isNewWeekSince(self.lastRebalanceDate) and \
            getTime() > "11-00-00": self.rebalance

    def rebalance(self):
        # get stock growth during lookback window
        symbols = [asset.symbol for asset in self.assets]
        fromDate = getDate(-self.numLookbackDays)
        toDate = getDate()
        returns = []
        for symbol in symbols:
            bars = self.alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate)
            returns.append( ((bars[-1].close - bars[0].open)/bars[0].open, symbol) )
        returns = sorted(returns)

        # long
        for ii in range(10):
            # TODO: check for existing position or order

            # get quote
            symbol = returns[ii][1]
            price = self.alpaca.polygon.last_quote(symbol)

            # get quantity
            quantity = int(self.maxPosFrac * self.equity / price)
            if quantity == 0: continue
            if quantity * price > self.buyingPower:
                quantity = int(self.buyingPower / price)

            # TODO: check margins & risk

            # TODO: add and optimize parameters for limit decisions

            upperLimit = price * -1 * (returns[ii][0] / 2 + 1)
            stopPrice = price * (returns[ii][0] / 2 + 1)
            lowerLimit = price * (returns[ii][0] + 1)
            
            order = self.alpaca.submit_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day',
                order_class='bracket',
                take_profit={'limit_price':str(upperLimit)},
                stop_loss={'stop_price':str(stopPrice), 'limit_price':str(lowerLimit)}
                )
            
