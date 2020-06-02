# This algo longs and shorts stocks based on their returns over the past days.
# It assumes high returns will come back down and vice versa. It holds these
# positions indefinitely.

from Algo import Algo
from marketHours import is_new_week_since, get_time_str, get_date_str
from warn import warn

class ReturnsReversion(Algo):
    def __init__(self, cash, maxPosFrac=0.01, numLookbackDays=7):
        self.numLookbackDays = numLookbackDays
        tags = ['longShort', 'overnight', 'weekly']
        super().__init__(cash, maxPosFrac, tags, 'returnsReversion')

        # additional attributes
        self.lastRebalanceDate = "0001-01-01"

        # additional attributes to save / load
        self.dataFields += [
            'lastRebalanceDate'
        ]
    
    def id(self):
        return f'ReturnsReversion_{self.maxPosFrac}_{self.numLookbackDays}'

    def tick(self):
        if is_new_week_since(self.lastRebalanceDate) and \
            get_time_str() > '11-00-00': self.rebalance()
            # FIX: market open

    def rebalance(self):
        print(self.id(), 'rebalancing')

        # get symbols and dates
        symbols = list(Algo.assets.keys())[:100] # FIX: first 100 are for testing
        fromDate = get_date_str(-self.numLookbackDays)
        toDate = get_date_str()

        # get asset returns during lookback window
        # NOTE: this takes a long time
        # it's okay since it only runs once per week
        # it would be good if the data could be shared between all algos that need it
        # once data has been aggregated in Algos.assets, that can be used instead
        assets = {}
        for symbol in symbols:
            try:
                bars = self.alpaca.polygon.historic_agg_v2(symbol, 1, 'day', fromDate, toDate)
                assets[symbol] = (bars[-1].close - bars[0].open)/bars[0].open
            except: pass

        # sort assets by historic returns
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
            
        # get quantity
        quantity = self.get_trade_quantity(symbol, side)
        if quantity == None: return

        # place order
        order = self.alpaca.submit_order(
            symbol=symbol,
            qty=quantity,
            side=side,
            type='market', # because this is long term
            time_in_force='day'
        )

        # save order
        order = dict(
            id = order.id,
            symbol = symbol,
            quantity = quantity,
            price = price
        )
        self.orders.append(order)
        self.allOrders.append(order) # NOTE: this may cause issues with parrallel execution

        print(self.id(), f'{side}ing {abs(quantity)} {symbol}')
