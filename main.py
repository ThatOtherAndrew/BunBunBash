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
    async def read(self) -> tuple[float, str]:
        pass


class RandomDataSource(DataSource):
    async def read(self) -> tuple[float, str]:
        await asyncio.sleep(0.05)
        return random.random() * (2 if random.random() < 0.02 else 0.1), 'a'


class HTTPDataSource(DataSource):
    def __init__(self, port: int = 8000) -> None:
        self.port = port
        self.app = Quart(__name__)
        self.data_queue = asyncio.Queue()
        self.server_started = False
        # {sid: key (A, B, C)}
        self.clients = {}

        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
        self.socket_app = socketio.ASGIApp(self.sio, self.app)

        @self.app.route('/')
        async def serve_client():
            return await send_file('http_client.html')

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
    def __init__(self, data_source: DataSource) -> None:
        self.data_source = data_source

        # Configuration parameters
        self.window_length = 32
        self.baseline_window_length = 64
        self.threshold_multiplier = 1.5
        self.min_peak_height = 0.1
        self.debounce_samples = 6
        self.smoothing_factor = 0.15
        self.variance_window_length = 32

        # Per-device state tracking
        self.device_states = {}

    def _init_device_state(self, key: str) -> None:
        """Initialize state for a new device"""
        if key not in self.device_states:
            self.device_states[key] = {
                'window': [0.0 for _ in range(self.window_length)],
                'baseline_window': [0.0 for _ in range(self.baseline_window_length)],
                'variance_window': [0.0 for _ in range(self.variance_window_length)],
                'samples_since_peak': self.debounce_samples,
                'smoothed_value': 0.0
            }

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> float:
        (new_sample, key) = await self.data_source.read()

        # Initialize device state if needed
        self._init_device_state(key)
        device_state = self.device_states[key]

        # Update smoothed value for this device
        device_state['smoothed_value'] = (self.smoothing_factor * new_sample +
                                        (1 - self.smoothing_factor) * device_state['smoothed_value'])

        # Update windows for this device
        device_state['window'].append(device_state['smoothed_value'])
        device_state['window'].pop(0)

        device_state['baseline_window'].append(device_state['smoothed_value'])
        device_state['baseline_window'].pop(0)

        device_state['variance_window'].append(device_state['smoothed_value'])
        device_state['variance_window'].pop(0)

        # Calculate thresholds for this device
        baseline = sum(device_state['baseline_window']) / len(device_state['baseline_window'])

        variance_mean = sum(device_state['variance_window']) / len(device_state['variance_window'])
        variance = sum((x - variance_mean) ** 2 for x in device_state['variance_window']) / len(device_state['variance_window'])
        std_dev = variance ** 0.5

        dynamic_threshold = baseline + (self.threshold_multiplier * std_dev)
        absolute_threshold = max(dynamic_threshold, self.min_peak_height)

        device_state['samples_since_peak'] += 1

        # Check for peak detection for this device
        if (device_state['smoothed_value'] > absolute_threshold and
            device_state['samples_since_peak'] >= self.debounce_samples):

            recent_max = max(device_state['window'][-3:])
            if recent_max == device_state['smoothed_value']:
                self.on_peak(device_state['smoothed_value'], key)
                device_state['samples_since_peak'] = 0

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
    # Default sensitivity=1.0, increase for more sensitive detection
    asyncio.run(PeakDetector(HTTPDataSource()).run())
