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
import math
import time
import numpy as np
from scipy import signal

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

class BiquadSection:
    """Direct Form II Transposed biquad filter section"""
    def __init__(self, b0, b1, b2, a0, a1, a2):
        self.b0 = b0 / a0
        self.b1 = b1 / a0
        self.b2 = b2 / a0
        self.a1 = a1 / a0
        self.a2 = a2 / a0
        self.s1 = 0.0
        self.s2 = 0.0
    
    def process(self, x):
        out = self.b0 * x + self.s1
        self.s1 = self.b1 * x - self.a1 * out + self.s2
        self.s2 = self.b2 * x - self.a2 * out
        return out
    
    def reset(self):
        self.s1 = 0.0
        self.s2 = 0.0


class CircularBuffer:
    """Circular buffer for RMS calculation"""
    def __init__(self, size):
        self.size = size
        self.buffer = [0.0] * size
        self.idx = 0
        self.sum_sq = 0.0
        self.filled = False
    
    def update(self, value):
        sq = value * value
        self.sum_sq += sq - self.buffer[self.idx]
        self.buffer[self.idx] = sq
        self.idx = (self.idx + 1) % self.size
        if self.idx == 0:
            self.filled = True
        n = self.size if self.filled else max(1, self.idx)
        return math.sqrt(self.sum_sq / n)


class PeakDetector:
    # Sample rate configurations
    SAMPLE_CONFIGS = {
        1000: {  # 1kHz
            'hp_freq': 20,
            'lp_freq': 400,
            'rms_window_ms': 20,
            'tau_baseline': 1.0,
            'k_threshold': 6,
            'refractory_ms': 200
        },
        200: {  # 200Hz
            'hp_freq': 8,
            'lp_freq': 80,
            'rms_window_ms': 30,
            'tau_baseline': 1.5,
            'k_threshold': 5,
            'refractory_ms': 250
        },
        100: {  # 100Hz
            'hp_freq': 5,
            'lp_freq': 40,
            'rms_window_ms': 30,
            'tau_baseline': 5.0,  # Slower baseline adaptation
            'k_threshold': 3.0,   # Lower threshold for better sensitivity
            'refractory_ms': 150  # Shorter refractory for closer peaks
        },
        50: {  # 50Hz - typical accelerometer rate
            'hp_freq': 3,      # Lower highpass for 50Hz sampling
            'lp_freq': 20,     # Below Nyquist (25Hz)
            'rms_window_ms': 40,  # 2 samples minimum
            'tau_baseline': 2.0,   # Moderate adaptation
            'k_threshold': 2.0,    # Low threshold for 0.4 amplitude
            'refractory_ms': 100   # 100ms for rapid knocks
        },
        20: {  # 20Hz (low sample rate fallback)
            'hp_freq': 2,
            'lp_freq': 8,
            'rms_window_ms': 100,
            'tau_baseline': 3.0,
            'k_threshold': 4,
            'refractory_ms': 400
        }
    }
    
    def __init__(self, data_source: DataSource, sample_rate: float = 50, sensitivity: float = 1.0) -> None:
        """
        Initialize PeakDetector
        
        Args:
            data_source: Source of accelerometer data
            sample_rate: Expected sample rate in Hz
            sensitivity: Detection sensitivity (0.1-10.0)
                        Higher = more sensitive (lower threshold)
                        Lower = less sensitive (higher threshold)
                        1.0 = default sensitivity
        """
        self.data_source = data_source
        self.sample_rate = sample_rate
        self.sensitivity = max(0.1, min(10.0, sensitivity))  # Clamp to reasonable range
        
        # Select appropriate config based on sample rate
        config_key = min(self.SAMPLE_CONFIGS.keys(), 
                         key=lambda x: abs(x - sample_rate))
        config = self.SAMPLE_CONFIGS[config_key]
        
        # Extract configuration
        self.hp_freq = config['hp_freq']
        self.lp_freq = config['lp_freq']
        self.rms_window_ms = config['rms_window_ms']
        self.tau_baseline = config['tau_baseline']
        # Scale k_threshold inversely with sensitivity
        # sensitivity=1.0 → use default k_threshold
        # sensitivity=2.0 → halve k_threshold (more sensitive)
        # sensitivity=0.5 → double k_threshold (less sensitive)
        self.k_threshold = config['k_threshold'] / self.sensitivity
        self.refractory_ms = config['refractory_ms']
        
        # Calculate derived parameters
        self.dt = 1.0 / sample_rate
        self.rms_window_size = max(3, int(self.rms_window_ms * sample_rate / 1000))
        self.refractory_samples = int(self.refractory_ms * sample_rate / 1000)
        
        # EMA alpha for baseline
        self.alpha_baseline = 1.0 - math.exp(-self.dt / self.tau_baseline)
        
        # Design butterworth bandpass filter
        nyquist = sample_rate / 2
        if self.lp_freq < nyquist:
            sos = signal.butter(2, [self.hp_freq / nyquist, self.lp_freq / nyquist], 
                               btype='bandpass', output='sos')
        else:
            # Just highpass if lp_freq exceeds nyquist
            sos = signal.butter(2, self.hp_freq / nyquist, 
                               btype='highpass', output='sos')
        
        # Create biquad cascade
        self.biquad_sections = []
        for section in sos:
            self.biquad_sections.append(
                BiquadSection(section[0], section[1], section[2],
                            section[3], section[4], section[5])
            )
        
        # Per-device state tracking
        self.device_states = {}
        
        # Timing for sample rate estimation
        self.last_sample_time = None
        self.estimated_rate = sample_rate

    def _init_device_state(self, key: str) -> None:
        """Initialize state for a new device"""
        if key not in self.device_states:
            # Create per-device filter chain
            device_biquads = []
            for section in self.biquad_sections:
                device_biquads.append(
                    BiquadSection(section.b0, section.b1, section.b2,
                                1.0, section.a1, section.a2)
                )
            
            self.device_states[key] = {
                'biquads': device_biquads,
                'rms_buffer': CircularBuffer(self.rms_window_size),
                'baseline': 0.0,
                'variance': 0.001,  # Small initial variance
                'prev_env': 0.0,
                'prev_prev_env': 0.0,  # For slope calculation
                'samples_since_peak': self.refractory_samples,
                'sample_count': 0,
                'triggered': False  # Track if we already triggered for this impulse
            }

    async def run(self) -> None:
        while True:
            await self.tick()

    async def tick(self) -> float:
        (mag, key) = await self.data_source.read()
        
        # Track timing for sample rate estimation
        current_time = time.time()
        if self.last_sample_time is not None:
            dt_actual = current_time - self.last_sample_time
            # Update estimated sample rate with EMA
            if dt_actual > 0:
                rate_estimate = 1.0 / dt_actual
                self.estimated_rate = 0.9 * self.estimated_rate + 0.1 * rate_estimate
        self.last_sample_time = current_time

        # Initialize device state if needed
        self._init_device_state(key)
        state = self.device_states[key]
        state['sample_count'] += 1
        
        # 1. Apply bandpass filter cascade
        filtered = mag
        for biquad in state['biquads']:
            filtered = biquad.process(filtered)
        
        # 2. Calculate RMS envelope
        env = state['rms_buffer'].update(abs(filtered))
        
        # 3. Update adaptive baseline and variance (EMA)
        if state['sample_count'] > self.rms_window_size:  # Wait for buffer to fill
            err = env - state['baseline']
            state['baseline'] += self.alpha_baseline * err
            state['variance'] += self.alpha_baseline * (err * err - state['variance'])
        else:
            # Initialize baseline during warmup
            state['baseline'] = env
        
        # 4. Calculate adaptive threshold
        std = math.sqrt(max(state['variance'], 1e-6))
        threshold = state['baseline'] + self.k_threshold * std
        
        # 5. Rising edge detection for low latency
        state['samples_since_peak'] += 1
        
        # Calculate slope (rate of change)
        slope = env - state['prev_env']
        prev_slope = state['prev_env'] - state['prev_prev_env']
        
        # Detect strong rising edge
        above_threshold = env > threshold
        strong_rise = slope > (threshold - state['baseline']) * 0.3  # 30% of threshold height in one sample
        accelerating = slope > prev_slope * 1.5  # Acceleration in rise
        
        # Trigger on rising edge, not peak
        if above_threshold and (strong_rise or accelerating) and not state['triggered']:
            if state['samples_since_peak'] >= self.refractory_samples:
                # Fire immediately on rising edge
                self.on_peak(env, key, {
                    'amplitude': env,
                    'baseline': state['baseline'],
                    'threshold': threshold,
                    'snr': env / (state['baseline'] + 1e-6),
                    'slope': slope
                })
                state['samples_since_peak'] = 0
                state['triggered'] = True
        
        # Reset trigger when signal drops below threshold
        if not above_threshold:
            state['triggered'] = False
        
        # Update previous envelopes for next iteration
        state['prev_prev_env'] = state['prev_env']
        state['prev_env'] = env
        
        return mag

    @staticmethod
    def on_peak(amplitude: float, key: str, info: dict = None):
        if info:
            print(f'Peak detected! Device: {key}, Amplitude: {amplitude:.3f}, SNR: {info["snr"]:.2f}')
        else:
            print(f'Peak: {amplitude:.3f} from {key}')
        
        if os.environ.get('XDG_SESSION_TYPE') == 'wayland':
            # TODO: press the right key on wayland. nixos.. 
            subprocess.run(["ydotool", "key", "57:1", "57:0"])
        else:
            keyboard.write(key)


if __name__ == '__main__':
    # Default sensitivity=1.0, increase for more sensitive detection
    asyncio.run(PeakDetector(HTTPDataSource(), sensitivity=1.0).run())
