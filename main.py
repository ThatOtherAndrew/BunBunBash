from abc import ABC, abstractmethod
import keyboard
import random
import asyncio
from quart import Quart, send_file
from hypercorn.config import Config
from hypercorn.asyncio import serve
import socketio
import subprocess
import json
import os

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

        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
        self.socket_app = socketio.ASGIApp(self.sio, self.app)

        @self.app.route('/')
        async def serve_client():
            return await send_file('http_client.html')

        @self.sio.event
        async def connect(sid, environ):
            print(f'Client {sid} connected')

        @self.sio.event
        async def disconnect(sid):
            print(f'Client {sid} disconnected')

        @self.sio.event
        async def data(sid, data):
            try:
                json_data = json.loads(data)
                for e in json_data:
                    await self.data_queue.put(e['z'])
            except (ValueError, TypeError, KeyError) as e:
                print(f'Error processing data: {e}')

    async def _start_server(self):
        if not self.server_started:
            self.server_started = True
            print(f'HTTPDataSource with Socket.IO listening on http://0.0.0.0:{self.port}/')
            cfg = Config()
            cfg.bind = [f"0.0.0.0:{self.port}"]
            # cfg.loglevel = "error"
            await serve(self.socket_app, cfg)

    async def read(self) -> float:
        if not self.server_started:
            asyncio.create_task(self._start_server())
        return await self.data_queue.get()

class PeakDetector:
    def __init__(self, data_source: DataSource) -> None:
        self.sensitivity = 0.1
        self.window_length = 16
        self.window = [float() for _ in range(self.window_length)]
        self.data_source = data_source

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> float:
        new_sample = await self.data_source.read()
        if new_sample >= self.sensitivity:
            self.on_peak(new_sample)
        self.window.append(await self.data_source.read())
        self.window.pop(0)

        return new_sample

    @staticmethod
    def on_peak(sample: float):
        print('peak:', sample)
        if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
            subprocess.run(["ydotool", "key", "57:1", "57:0"])
        else:
            keyboard.press('space')


if __name__ == '__main__':
    asyncio.run(PeakDetector(HTTPDataSource()).run())
