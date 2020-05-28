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
        # get stock growth during lookback window
        symbols = self.assets.keys()
        fromDate = get_date_str(-self.numLookbackDays)
        toDate = get_date_str()

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

        # check arguments
        if symbol not in self.assets:
            warn(f'{self.id()} symbol "{symbol}" is not recognized')
            return
        if side not in ('buy', 'sell'):
            warn(f'{self.id()} trading side "{side}" is not recognized')
            return
        
        print(self.id(), f'{side}ing {symbol}')

        # get quote and quantity
        price = self.alpaca.polygon.last_quote(symbol)
        quantity = int(self.maxPosFrac * self.equity / price)
        if quantity * price > self.buyingPower:
            quantity = int(self.buyingPower / price)
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

        # TODO: check global positions for zero crossing
        alpacaPositions = self.alpaca.list_positions()
        positions = {}
        for position in alpacaPositions:
            positions[position.symbol] = position.qty
        if symbol in positions:
            if (position[symbol] + quantity) * position[symbol] < 0: # if trade will swap position
                quantity = -position[symbol]

        # NOTE: this could exceed 200 api calls per min

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
        self.orders.append(dict(
            id = order.id,
            symbol = symbol,
            quantity = quantity,
            price = price
        ))

        print(self.id(), f'placed order for {quantity} of {symbol}')
            
