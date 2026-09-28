import time

class AvgPrice:
    def __init__(self):
        self.data = []

    def add(self, price):
        self.data.append((time.time(), float(price)))

    def get_avg(self, seconds):
        now = time.time()
        values = [p for t, p in self.data if now - t <= seconds]

        if not values:
            return 0

        return sum(values) / len(values)