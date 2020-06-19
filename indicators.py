# functions to be used for enter and exit indications

from Algo import Algo

# TODO: confirm indices have correct timestamps

class DayReturn:
    def __init__(self, days):
        self.days = days
        self.name = 'dayReturn' + str(days)
    def tick(self, symbol):
        openPrice = Algo.assets[symbol]['dayBars'].iloc[-self.days].open
        closePrice = Algo.assets[symbol]['dayBars'].iloc[-1].close
        print(Algo.assets[symbol]['dayBars'].iloc[-1])
        return (closePrice - openPrice) / openPrice

class DayVolume:
    def __init__(self, days):
        self.days = days
        self.name = 'dayVolume' + str(days)
    def tick(self, symbol):
        volume = 0
        for day in range(self.days):
            volume += Algo.assets[symbol]['dayBars'].iloc[-day].volume
        Algo.assets[symbol][self.name] = volume













