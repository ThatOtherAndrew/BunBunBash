from abc import ABC, abstractmethod
import keyboard
import random
import asyncio
from quart import Quart, request, jsonify, send_file
import threading
import logging
from hypercorn.config import Config
from hypercorn.asyncio import serve

class DataSource(ABC):
    @abstractmethod
    async def read(self) -> float:
        pass


class RandomDataSource(DataSource):
    async def read(self) -> float:
        await asyncio.sleep(0.05)
        return random.random() * (2 if random.random() < 0.02 else 0.1)


class HTTPDataSource(DataSource):
    def __init__(self, port: int = 8000) -> None:
        self.port = port
        self.app = Quart(__name__)
        self.data_queue = asyncio.Queue()
        self.server_started = False

        @self.app.route('/')
        async def serve_client():
            return await send_file('http_client.html')

        @self.app.route('/data', methods=['POST'])
        async def handle_data():
            try:
                json_data = await request.get_json()
                value = float(json_data)
                await self.data_queue.put(value)
                return jsonify({'status': 'success'})
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid JSON or non-numeric value'}), 400

    async def _start_server(self):
        if not self.server_started:
            self.server_started = True
            print(f'HTTPDataSource listening on http://0.0.0.0:{self.port}/')
            cfg = Config()
            cfg.bind = [f"0.0.0.0:{self.port}"]
            cfg.loglevel = "error"
            await serve(self.app, cfg)

    async def read(self) -> float:
        if not self.server_started:
            asyncio.create_task(self._start_server())
        return await self.data_queue.get()

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
    asyncio.run(PeakDetector(HTTPDataSource()).run())
