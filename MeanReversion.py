from Algo import Algo
from marketHours import *

class MeanReversion(Algo):
    def __init__(self, cash, maxPositionFraction=0.01, numLookbackDays=7):
        self.numLookbackDays = numLookbackDays
        super().__init__(cash, maxPositionFraction)

        self.lastRebalanceDate = "0000-00-00"

    def tick(self):
        if isNewWeekSince(self.lastRebalanceDate) and \
            getTime() > "11-00-00": self.rebalance

    def rebalance(self):
        # get stock growth during lookback window
        assets = self.alpaca.list_assets('active', 'us_equity')
        symbols = [asset.symbol for asset in assets]
        fromDate = getDate(-self.numLookbackDays)
        toDate = getDate()
        returns = []
        for symbol in symbols:
            bars = self.alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate)
            returns.append( ((bars[-1].close - bars[0].open)/bars[0].open, symbol) )
        returns = sorted(returns)

        # long
        for ii in range(10):
            symbol = returns[ii][1]
            price = self.alpaca.polygon.last_quote(symbol)
            quantity = int(self.maxPositionFraction * self.equity / price)
            order = self.alpaca.submit_order(
                symbol=symbol,
                qty=quantity,
                side='buy',
                type='market',
                time_in_force='day',
                order_class='bracket',
                take_profit={limit_price:limit},
                stop_loss={stop_price:'295.50', limit_price:'295.50'}
                )
            
