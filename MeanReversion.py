from Algo import Algo

class MeanReversion(Algo):
    def __init__(self, cash, maxPositionFraction, numLookbackDays):
        self.numLookbackDays = numLookbackDays
        super().__init__(cash, maxPositionFraction)
    def tick(self):
        pass
