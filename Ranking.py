from Algo import Algo

class Ranking:
    def __init__(self, indicator):
        self.name = indicator.name

    def tick(self):
        Algo.rankings[self.name] = \
            sorted(list(Algo.assets.keys()),
            key=lambda symbol: Algo.assets[symbol][self.name][-1])
