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
                await self.sio.emit('data', data)
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
        self.window_length = 32
        self.window = [0.0 for _ in range(self.window_length)]
        self.data_source = data_source
        
        self.baseline_window_length = 64
        self.baseline_window = [0.0 for _ in range(self.baseline_window_length)]
        
        self.threshold_multiplier = 1.5
        self.min_peak_height = 0.1
        
        self.debounce_samples = 6
        self.samples_since_peak = self.debounce_samples
        
        self.smoothing_factor = 0.15
        self.smoothed_value = 0.0
        
        self.variance_window = [0.0 for _ in range(32)]

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> float:
        new_sample = abs(await self.data_source.read())
        
        self.smoothed_value = (self.smoothing_factor * new_sample + 
                               (1 - self.smoothing_factor) * self.smoothed_value)
        
        self.window.append(self.smoothed_value)
        self.window.pop(0)
        
        self.baseline_window.append(self.smoothed_value)
        self.baseline_window.pop(0)
        
        self.variance_window.append(self.smoothed_value)
        self.variance_window.pop(0)
        
        baseline = sum(self.baseline_window) / len(self.baseline_window)
        
        variance_mean = sum(self.variance_window) / len(self.variance_window)
        variance = sum((x - variance_mean) ** 2 for x in self.variance_window) / len(self.variance_window)
        std_dev = variance ** 0.5
        
        dynamic_threshold = baseline + (self.threshold_multiplier * std_dev)
        absolute_threshold = max(dynamic_threshold, self.min_peak_height)
        
        self.samples_since_peak += 1
        
        if (self.smoothed_value > absolute_threshold and 
            self.samples_since_peak >= self.debounce_samples):
            
            recent_max = max(self.window[-3:])
            if recent_max == self.smoothed_value:
                self.on_peak(self.smoothed_value)
                self.samples_since_peak = 0

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
