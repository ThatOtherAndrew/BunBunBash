from abc import ABC, abstractmethod
import keyboard
import random
import asyncio


class DataSource(ABC):
    @abstractmethod
    async def read(self) -> list[float]:
        ...


class RandomDataSource(DataSource):
    async def read(self) -> list[float]:
        await asyncio.sleep(0.1)
        return [random.random() * (2 if random.random() < 0.02 else 0.1)]


class PeakDetector:
    def __init__(self, data_source: DataSource) -> None:
        self.window_length = 10
        self.window = [float() for _ in range(self.window_length)]
        self.data_source = data_source

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> list[float]:
        self.window.extend(await self.data_source.read())
        self.window = self.window[-self.window_length:]
        print(' '.join(f'{x:.1f}' for x in self.window), end='\r')
        return self.window

    @staticmethod
    def on_peak():
        print('space')
        keyboard.press_and_release('space')


if __name__ == '__main__':
    asyncio.run(PeakDetector(RandomDataSource()).run())
