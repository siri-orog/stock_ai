import time

class ETQCalculator:
    def __init__(self):
        self.data = []

    def add(self, qty):
        self.data.append((time.time(), int(qty)))

    def get_etq(self, seconds):
        now = time.time()
        return sum(int(q) for t, q in self.data if now - t <= seconds)