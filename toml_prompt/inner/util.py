import random


class Random(random.Random):
    def __init__(self, seed: int | None):
        super().__init__(seed)
        self.count = 0

    def set_count(self, count: int):
        print(f"RandomCount: {self.count} -> {count}")
        assert count >= self.count
        _rands = [self.random() for _i in range(self.count, count)]
        self.count = 0

    def random(self) -> float:
        self.count += 1
        return super().random()
