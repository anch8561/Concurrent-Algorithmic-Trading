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

        self.lastRebalanceDate = "0001-01-01"
    
    def id(self):
        return f'ReturnsReversion{self.numLookbackDays}:'

    def tick(self):
        if is_new_week_since(self.lastRebalanceDate) and \
            get_time_str() > '11-00-00': self.rebalance()

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

        # check arguments
        if symbol not in Algo.assets:
            warn(f'{self.id()} symbol "{symbol}" is not recognized')
            return
        if side not in ('buy', 'sell'):
            warn(f'{self.id()} trading side "{side}" is not recognized')
            return

        # get quote and quantity
        # TODO: get price from Algo.assets
        price = self.alpaca.polygon.last_quote(symbol).bidprice
        quantity = int(self.maxPosFrac * self.equity / price)
        if quantity * price > self.cash:
            quantity = int(self.cash / price)
        if quantity == 0: return
        if side == 'sell': quantity *= -1 # set quantity negative for sell

        # check for existing position
        if symbol in self.positions:
            if self.positions[symbol] * quantity > 0: # same side as position
                if abs(self.positions[symbol]) > abs(quantity): # position is large enough
                    return
                elif abs(self.positions[symbol]) > abs(quantity): # add to position
                    quantity -= self.positions[symbol]
                else: # quantity == position
                    return
            elif self.positions[symbol] * quantity < 0: # opposite side from position
                quantity = -self.positions[symbol] # exit position
                # TODO: queue this same trade again
        
        # TODO: check risk
        # TODO: check for leveraged ETFs
        # TODO: check volume

        # TODO: check global positions for zero crossing
        positions = {}
        if self.live: allPositions = Algo.livePositions
        else: allPositions = Algo.paperPositions
        for position in allPositions:
            positions[position.symbol] = position.qty
        if symbol in positions:
            if (position[symbol] + quantity) * position[symbol] < 0: # if trade will swap position
                quantity = -position[symbol]

        # TODO: check global orders
        # for existing or [short sell (buy) & short buy (sell)]

        # place order
        order = self.alpaca.submit_order(
            symbol=symbol,
            qty=abs(quantity),
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
            
