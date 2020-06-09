# This algo trades based on the difference between price and moving average.
# When the difference is greater than 1 STD, an order is placed with exits at
# the mean and 2 STDs

from Algo import Algo
from marketHours import get_time, get_date, get_open_time, get_close_time, get_n_market_days_ago, is_new_week_since
from warn import warn
from ta import 

class ReturnsReversion(Algo):
    def __init__(self, cash, maxPosFrac=0.01, numLookbackDays=5):
        # TODO: check arguments
        self.numLookbackDays = numLookbackDays
        super().__init__(
            cash = cash,
            BPCalc = 'overnight',
            equityStyle = 'longShort',
            tickFreq = 'hour',
            maxPosFrac = maxPosFrac
        )

        # additional attributes
        self.lastRebalanceDate = "0001-01-01"

        # additional attributes to save / load
        self.dataFields += [
            'lastRebalanceDate'
        ]
    
    def id(self):
        return f'MeanReversion_{self.maxPosFrac}_{self.numLookbackDays}'

    def tick(self):
        if (
            is_new_week_since(self.lastRebalanceDate) and
            get_time(-1) > get_open_time() and
            get_time(1) < get_close_time()
        ):
            self.rebalance()

    def rebalance(self):
        print(self.id(), 'rebalancing')

        # get mean & std

        # sort by distance from mean

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

        try:
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
        except:
            warn(f'{self.id()} order failed: {side}ing {abs(quantity)} {symbol}')
