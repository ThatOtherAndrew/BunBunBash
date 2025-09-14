from abc import ABC, abstractmethod
import keyboard
import random
import asyncio
from quart import Quart, send_file, request, jsonify
from hypercorn.config import Config
from hypercorn.asyncio import serve
import socketio
import subprocess
import json
import os

class DataSource(ABC):
    @abstractmethod
    async def read(self) -> tuple[float, str]:
        pass


class RandomDataSource(DataSource):
    async def read(self) -> tuple[float, str]:
        await asyncio.sleep(0.05)
        return random.random() * (2 if random.random() < 0.02 else 0.1), 'a'


class HTTPDataSource(DataSource):
    def __init__(self, port: int = 8000, peak_detector=None) -> None:
        self.port = port
        self.app = Quart(__name__)
        self.data_queue = asyncio.Queue()
        self.server_started = False
        # {sid: key (A, B, C)}
        self.clients = {}
        self.peak_detector = peak_detector

        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
        self.socket_app = socketio.ASGIApp(self.sio, self.app)

        @self.app.route('/')
        async def serve_client():
            return await send_file('http_client.html')

        @self.app.route('/settings', methods=['POST'])
        async def update_settings():
            if not self.peak_detector:
                return jsonify({'error': 'Peak detector not configured'}), 400

            data = await request.get_json()
            if not data:
                return jsonify({'error': 'No JSON data provided'}), 400

            # Update threshold if provided
            if 'threshold' in data:
                try:
                    self.peak_detector.threshold = float(data['threshold'])
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid threshold value'}), 400

            # Update debounce_samples if provided
            if 'debounce_samples' in data:
                try:
                    self.peak_detector.debounce_samples = int(data['debounce_samples'])
                except (ValueError, TypeError):
                    return jsonify({'error': 'Invalid debounce_samples value'}), 400

            return jsonify({
                'threshold': self.peak_detector.threshold,
                'debounce_samples': self.peak_detector.debounce_samples
            })

        @self.sio.event
        async def connect(sid, environ):
            self.clients[sid] = 'A'

        @self.sio.event
        async def disconnect(sid):
            print(f'Client {sid} disconnected')
            del self.clients[sid]

        @self.sio.event
        async def key(sid, key):
            self.clients[sid] = key

        @self.sio.event
        async def data(sid, data):
            try:
                json_data = json.loads(data)
                # Add the key to each data point before echoing
                enriched_data = []
                for e in json_data:
                    await self.data_queue.put((e['z'], self.clients[sid]))
                    # Add the client's key to the data
                    e['key'] = self.clients[sid]
                    enriched_data.append(e)
                # Emit the enriched data with keys
                await self.sio.emit('data', json.dumps(enriched_data))
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

    async def read(self) -> tuple[float, str]:
        if not self.server_started:
            asyncio.create_task(self._start_server())
        return await self.data_queue.get()

class PeakDetector:
    def __init__(self, data_source: DataSource, threshold: float = 0.5, debounce_samples: int = 10) -> None:
        self.data_source = data_source
        self.threshold = threshold
        self.debounce_samples = debounce_samples
        self.samples_since_peak = {}

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> float:
        (new_sample, key) = await self.data_source.read()

        # Initialize counter for new devices
        if key not in self.samples_since_peak:
            self.samples_since_peak[key] = self.debounce_samples

        self.samples_since_peak[key] += 1

        if abs(new_sample) >= self.threshold and self.samples_since_peak[key] >= self.debounce_samples:
            self.on_peak(new_sample, key)
            self.samples_since_peak[key] = 0

        return new_sample

    @staticmethod
    def on_peak(sample: float, key: str):
        print('peak:', sample)
        if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
            # TODO: press the right key on wayland. nixos..
            subprocess.run(["ydotool", "key", "57:1", "57:0"])
        else:
            keyboard.write(key)


if __name__ == '__main__':
    # Pass threshold (default 0.5) and debounce_samples (default 10) as parameters
    # POST to /settings with JSON {"threshold": 0.7, "debounce_samples": 5} to update at runtime
    http_source = HTTPDataSource()
    detector = PeakDetector(http_source, threshold=0.2, debounce_samples=10)
    http_source.peak_detector = detector
    asyncio.run(detector.run())
