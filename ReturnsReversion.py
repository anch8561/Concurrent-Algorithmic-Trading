# This algo longs and shorts stocks based on their returns over the past days.
# It assumes high returns will come back down and vice versa. It holds these
# positions indefinitely.

from Algo import Algo
from marketHours import is_new_week_since, get_time, get_date
import warnings

class ReturnsReversion(Algo):
    def __init__(self, cash, maxPosFrac=0.01, numLookbackDays=7):
        self.numLookbackDays = numLookbackDays
        tags = ['long', 'short', 'overnight', 'weekly']
        super().__init__(cash, maxPosFrac, tags, 'returnsReversion')

        self.lastRebalanceDate = "0000-00-00"

    def tick(self):
        if is_new_week_since(self.lastRebalanceDate) and \
            get_time() > "11-00-00": self.rebalance

    def rebalance(self):
        # get stock growth during lookback window
        symbols = [asset.symbol for asset in self.assets]
        fromDate = get_date(-self.numLookbackDays)
        toDate = get_date()

        # TODO: replace with self.get_asset(symbol, 'dayBars', fromDate, toDate)
        assets = {}
        for symbol in symbols:
            bars = self.alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate)
            assets[symbol] = (bars[-1].close - bars[0].open)/bars[0].open
        assets = sorted(assets.items(), key=lambda x: x[1]) # now a list of tuples

        # long
        numOrders = int(1/self.maxPosFrac/2)
        for ii in range(numOrders): self.trade(assets[ii][0], 'buy')
        
        # short
        assets = [asset for asset in assets if self.assets[asset[0]]['easyToBorrow']]
        for ii in range(-1, -numOrders, -1): self.trade(assets[ii][0], 'sell')
    
    def trade(self, symbol, side):
        # symbol: e.g. 'AAPL'
        # side: 'buy' or 'sell'

        # TODO: check for existing position or order

        # get quote and quantity
        # TODO: I think this needs to be different for shorts
        price = self.alpaca.polygon.last_quote(symbol)
        quantity = int(self.maxPosFrac * self.equity / price)
        if quantity * price > self.buyingPower:
            quantity = int(self.buyingPower / price)
        if quantity == 0:
            warnings.warn(f'{self} {symbol} trade quantity is zero')
            return
        
        # TODO: check margins & risk

        order = self.alpaca.submit_order(
            symbol=symbol,
            qty=quantity,
            side=side,
            type='market', # because this is long term
            time_in_force='day'
        )
        self.orders.append(order.id)


            
