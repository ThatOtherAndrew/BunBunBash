from abc import ABC, abstractmethod
import keyboard
import random
import asyncio


class DataSource(ABC):
    @abstractmethod
    async def read(self) -> float:
        pass


class RandomDataSource(DataSource):
    async def read(self) -> float:
        await asyncio.sleep(0.05)
        return random.random() * (2 if random.random() < 0.02 else 0.1)

class PeakDetector:
    def __init__(self, data_source: DataSource) -> None:
        self.sensitivity = 0.3
        self.window_length = 16
        self.window = [float() for _ in range(self.window_length)]
        self.data_source = data_source

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> float:
        new_sample = await self.data_source.read()
        if new_sample > self.sensitivity:
            print(f'\n{new_sample}', end=' ')
            self.on_peak()
        self.window.append(await self.data_source.read())
        self.window.pop(0)

        print(' '.join(f'{x:.2f}' for x in self.window), end='\r')
        return new_sample

    @staticmethod
    def on_peak():
        print('peak')


if __name__ == '__main__':
    asyncio.run(PeakDetector(RandomDataSource()).run())
