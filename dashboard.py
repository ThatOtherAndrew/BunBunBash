"""
HackMIT Dashboard - Integrates async DataSource/PeakDetector with Flask visualization
Combines HackMIT's data generation with advanced dashboard visualization
"""
from flask import Flask, jsonify, render_template, request
import asyncio
import threading
import time
import math
import random
from collections import deque
from typing import Dict, Optional, Callable

# Import HackMIT classes
from main import DataSource, PeakDetector
import socketio as socketio_client

app = Flask(__name__, static_folder='.', static_url_path='')

# Client adapter to receive data from main.py's HTTPDataSource server
class SocketIOClientDataSource(DataSource):
    """Data source that connects to main.py's HTTPDataSource via Socket.IO"""
    
    def __init__(self, port: int = 8000) -> None:
        self.port = port
        self.data_queue = asyncio.Queue()
        self.connected = False
        self.start_time = time.time()
        self.sio = None
    
    def setup_connection(self):
        """Setup Socket.IO connection to main.py server"""
        try:
            import socketio
            import threading
            
            print(f"🔌 Connecting to main.py server at http://localhost:{self.port}...")
            
            # Create Socket.IO client
            self.sio = socketio.Client()
            
            @self.sio.event
            def connect():
                print(f"✅ Connected to main.py Socket.IO server on port {self.port}")
                self.connected = True
                # Select a default key
                self.sio.emit('key', 'A')
            
            @self.sio.event
            def disconnect():
                print("❌ Disconnected from main.py server")
                self.connected = False
            
            @self.sio.event
            def data(raw_data):
                """Receive data from main.py server"""
                try:
                    import json
                    parsed = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                    if isinstance(parsed, list):
                        for item in parsed:
                            z_value = item.get('z', 0)
                            # Get key from the connection (for now default to 'A')
                            key = 'A'  # TODO: track which key this client represents
                            if loop:
                                asyncio.run_coroutine_threadsafe(self.data_queue.put((z_value, key)), loop)
                except Exception as e:
                    print(f"❌ Error processing data: {e}")
            
            # Connect in a separate thread
            def connect_thread():
                try:
                    self.sio.connect(f'http://localhost:{self.port}')
                    self.sio.wait()  # Keep connection alive
                except Exception as e:
                    print(f"⚠️ Could not connect to main.py server: {e}")
                    self.connected = False
            
            thread = threading.Thread(target=connect_thread, daemon=True)
            thread.start()
            
            # Give it a moment to connect
            time.sleep(0.5)
            
        except Exception as e:
            print(f"⚠️ Could not setup connection: {e}")
            self.connected = False
    
    def receive_data(self, data):
        """Called when data is received from main.py"""
        try:
            if isinstance(data, str):
                import json
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    print(f"📡 Received batch of {len(parsed)} data points from main.py")
                    # Process ALL data points with their keys
                    for i, item in enumerate(parsed):
                        z_value = item.get('z', 0)
                        key = item.get('key', 'A')  # Get the device key
                        print(f"   Point {i+1}/{len(parsed)}: z={z_value:.4f}, key={key}")
                        if loop:
                            asyncio.run_coroutine_threadsafe(self.data_queue.put((z_value, key)), loop)
                        else:
                            print("⚠️ Loop not available yet")
                    print(f"✅ Queued all {len(parsed)} points")
                else:
                    # Single data point
                    z_value = parsed.get('z', 0) if isinstance(parsed, dict) else parsed
                    key = parsed.get('key', 'A') if isinstance(parsed, dict) else 'A'
                    print(f"📡 Received single point: z={z_value}, key={key}")
                    if loop:
                        asyncio.run_coroutine_threadsafe(self.data_queue.put((z_value, key)), loop)
                    else:
                        print("⚠️ Loop not available yet")
        except Exception as e:
            print(f"❌ Could not process data: {e}")
    
    def setup_test_connection(self):
        """Setup connection with test data for HTTPDataSource"""
        try:
            print(f"🔌 Testing connection to main.py server at http://localhost:{self.port}...")
            self.connected = True
        except Exception as e:
            print(f"❌ Could not connect to main.py server: {e}")
    
    async def read(self) -> tuple[float, str]:
        """Read z-axis data and key from the queue"""
        z_value, key = await self.data_queue.get()
        print(f"✅ Processing z-value: {z_value:.4f}, key: {key} (Queue size: {self.data_queue.qsize()})")
        return z_value, key

class MultiKeyDataCollector:
    """Handles multi-key data streams from main.py"""
    
    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self.start_time = time.time()
        
    async def read(self) -> Dict[str, any]:
        """Read data and format it with timestamp and key information"""
        z_value, key = await self.data_source.read()
        current_time = time.time() - self.start_time
        
        return {
            'timestamp': current_time,
            'z_value': round(z_value, 3),
            'key': key
        }

class DashboardDataCollector:
    """Handles multi-key data collection and integrates with main.py PeakDetector"""
    
    def __init__(self, data_source: DataSource):
        self.data_source = data_source
        self.data_collector = MultiKeyDataCollector(data_source)
        # Create separate PeakDetector instances for each key
        self.peak_detectors = {}  # Will create on-demand per key
        self.detected_peaks = []
        self.peak_callback = None
        self.start_time = time.time()
        
    def set_peak_callback(self, callback):
        """Set a callback to be called when peak is detected"""
        self.peak_callback = callback
    
    async def tick(self) -> Dict[str, any]:
        """Collect data and run peak detection"""
        # Get raw data with key
        z_value, key = await self.data_source.read()
        current_time = time.time() - self.start_time
        
        # Create PeakDetector for this key if it doesn't exist
        if key not in self.peak_detectors:
            # Create a simple wrapper to feed single-key data to PeakDetector
            class SingleKeyDataSource(DataSource):
                def __init__(self, parent_collector, target_key):
                    self.parent = parent_collector
                    self.key = target_key
                    self.last_value = None
                    
                async def read(self):
                    # Return the last value for this key with the key
                    return self.last_value, self.key
            
            single_source = SingleKeyDataSource(self, key)
            self.peak_detectors[key] = {
                'source': single_source,
                'detector': PeakDetector(single_source)
            }
            
            # Override on_peak to capture peaks
            original_on_peak = self.peak_detectors[key]['detector'].on_peak
            def make_capture_peak(device_key):
                def capture_peak(sample, k=None):
                    # Use current time when peak is detected, not when detector was created
                    peak_time = time.time() - self.start_time
                    peak_data = {
                        'timestamp': peak_time,
                        'z_value': round(sample, 3),
                        'key': device_key,
                        'peak_type': 'detected',
                        'debounce_end': peak_time + DEBOUNCE_DURATION
                    }
                    self.detected_peaks.append(peak_data)
                    
                    if self.peak_callback:
                        self.peak_callback(peak_data)
                    
                    # Call original
                    if k is not None:
                        original_on_peak(sample, k)
                    else:
                        original_on_peak(sample, device_key)
                return capture_peak
            
            self.peak_detectors[key]['detector'].on_peak = make_capture_peak(key)
        
        # Update the data source for this key
        self.peak_detectors[key]['source'].last_value = z_value
        
        # Run peak detection for this key
        await self.peak_detectors[key]['detector'].tick()
        
        # Return formatted data point
        return {
            'timestamp': current_time,
            'z_value': round(z_value, 3),
            'key': key
        }
    
    @property
    def sensitivity(self):
        """Access main.py PeakDetector's sensitivity"""
        # Return the threshold_multiplier from the first detector or default
        if self.peak_detectors:
            first_key = list(self.peak_detectors.keys())[0]
            return self.peak_detectors[first_key]['detector'].threshold_multiplier
        return 1.5  # Default value from main.py
    
    @sensitivity.setter
    def sensitivity(self, value):
        """Set main.py PeakDetector's sensitivity for all detectors"""
        # Update all existing detectors
        for key in self.peak_detectors:
            self.peak_detectors[key]['detector'].threshold_multiplier = value

# Global data storage and async components
# Store data separately for each key (A, B, C)
multi_key_data = {}  # {'A': deque(), 'B': deque(), 'C': deque()}
all_data = []
data_collector = None
data_source = None
data_thread = None
loop = None

# Configuration
DEBOUNCE_DURATION = 0.2  # 200ms debounce period in seconds

def start_async_data_collection(use_real_data=True, port=8000):
    """Start async data collection in background thread
    
{{ ... }}
    Args:
        use_real_data: If True, use HTTPDataSource. If False, use simulated data.
        port: Port for HTTPDataSource when using real data
    """
    global data_collector, data_source, loop, data_thread
    
    # Don't start multiple threads
    if data_thread and data_thread.is_alive():
        return
    
    # Initialize components BEFORE starting the loop
    if use_real_data:
        # For real data, directly connect to main.py's data queue
        # We don't generate test data - we wait for real phone data
        data_source = RealPhoneDataSource(port=port)
    else:
        data_source = SimulatedDataSource()
    data_collector = DashboardDataCollector(data_source)
    
    def run_async_loop():
        global loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def data_collection_loop():
            global multi_key_data, all_data
            print(f"🔄 Starting {'real' if use_real_data else 'simulated'} data collection...")
            if use_real_data:
                print(f"📡 Waiting for data on port {port}...")
            while True:
                try:
                    data_point = await data_collector.tick()
                    
                    # Store data in key-specific deques
                    key = data_point.get('key', 'A')
                    if key not in multi_key_data:
                        multi_key_data[key] = deque(maxlen=1000)
                    
                    multi_key_data[key].append(data_point)
                    all_data.append(data_point)
                    # No sleep needed - HTTPDataSource will block until data arrives
                    if not use_real_data:
                        await asyncio.sleep(0.016)  # Only sleep for simulated data
                except Exception as e:
                    print(f"❌ Error in data collection: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(0.1)
        
        loop.run_until_complete(data_collection_loop())
    
    # Set up peak callback
    def on_peak_detected(peak_data):
        print(f"Peak detected: {peak_data['z_value']:.3f} on key {peak_data['key']} at {peak_data['timestamp']:.2f}s")
    
    data_collector.set_peak_callback(on_peak_detected)
    
    # Start background thread
    data_thread = threading.Thread(target=run_async_loop, daemon=True)
    data_thread.start()

def stop_async_data_collection():
    """Stop async data collection"""
    global loop
    if loop and not loop.is_closed():
        loop.call_soon_threadsafe(loop.stop)

# Flask Routes
@app.route('/')
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/api/data/receive', methods=['POST'])
def receive_data_from_main():
    """Endpoint to receive data from main.py (if using HTTP polling instead of Socket.IO)"""
    global data_source
    
    data = request.get_json()
    if data and data_source and isinstance(data_source, SocketIOClientDataSource):
        # Forward data to the data source
        data_source.receive_data(json.dumps(data))
        return jsonify({'status': 'received'})
    
    return jsonify({'error': 'Data source not ready'}), 503

@app.route('/api/debug/queue')
def debug_queue():
    """Debug endpoint to check data queue status"""
    if data_source and isinstance(data_source, SocketIOClientDataSource):
        return jsonify({
            'connected': data_source.connected,
            'queue_size': data_source.data_queue.qsize() if hasattr(data_source, 'data_queue') else 0,
            'has_data': len(all_data) > 0
        })
    return jsonify({'error': 'No data source'})

@app.route('/api/data/latest')
def get_latest_data():
    """Get the latest data point for each key"""
    latest_data = {}
    for key, data_deque in multi_key_data.items():
        if data_deque:
            latest_data[key] = data_deque[-1]
    
    if latest_data:
        return jsonify(latest_data)
    return jsonify({'error': 'No data available', 'timestamp': 0})

@app.route('/api/data/since/<timestamp>')
def get_data_since(timestamp):
    """Get all data points since a given timestamp for all keys"""
    try:
        timestamp = float(timestamp)
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid timestamp'})
        
    result = {}
    for key, data_deque in multi_key_data.items():
        if data_deque:
            # Find all points newer than the given timestamp
            new_points = [d for d in data_deque if d.get('timestamp', 0) > timestamp]
            result[key] = new_points[-100:]  # Limit to last 100 per key
    
    return jsonify(result)

@app.route('/api/data/history')
def get_data_history():
    """Get historical data for all keys"""
    try:
        limit = request.args.get('limit', 500, type=int)
        result = {}
        
        if multi_key_data:
            for key, data_deque in multi_key_data.items():
                if data_deque:
                    result[key] = list(data_deque)[-limit:]
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in get_data_history: {e}")
        return jsonify({'error': 'Internal server error', 'message': str(e)}), 500

@app.route('/api/peaks')
def get_detected_peaks():
    """Get detected peaks for all keys"""
    if data_collector:
        return jsonify(data_collector.detected_peaks[-50:])  # Last 50 peaks
    return jsonify([])

@app.route('/api/stats')
def get_stats():
    """Get data statistics for all keys"""
    if not all_data:
        return jsonify({'error': 'No data available'})
    
    stats = {
        'total_points': len(all_data),
        'detected_peaks': len(data_collector.detected_peaks) if data_collector else 0,
        'keys': {}
    }
    
    # Per-key statistics
    for key, data_deque in multi_key_data.items():
        if data_deque:
            data_list = list(data_deque)
            z_values = [d['z_value'] for d in data_list if 'z_value' in d]
            if z_values:
                stats['keys'][key] = {
                    'points': len(data_list),
                    'current_value': z_values[-1] if z_values else 0,
                    'avg_value': sum(z_values) / len(z_values),
                    'max_value': max(z_values),
                    'min_value': min(z_values)
                }
    
    return jsonify(stats)

@app.route('/api/control/start', methods=['POST'])
def start_data_collection():
    """Start data collection"""
    data = request.get_json() or {}
    use_real = data.get('use_real_data', True)
    port = data.get('port', 5000)
    start_async_data_collection(use_real_data=use_real, port=port)
    return jsonify({'status': 'started', 'mode': 'real' if use_real else 'simulated', 'port': port})

@app.route('/api/control/stop', methods=['POST'])
def stop_data_collection():
    """Stop data collection"""
    stop_async_data_collection()
    return jsonify({'status': 'stopped'})

@app.route('/api/data/clear', methods=['POST'])
def clear_data():
    """Clear all data"""
    global multi_key_data, all_data
    for data_deque in multi_key_data.values():
        data_deque.clear()
    all_data.clear()
    
    if data_collector:
        data_collector.detected_peaks.clear()
        # Reset data collector start time
        data_collector.data_collector.start_time = time.time()
    return jsonify({'status': 'cleared'})

@app.route('/api/control/threshold', methods=['POST'])
def update_threshold():
    """Update peak detection threshold"""
    global data_collector
    
    if data_collector:
        data = request.get_json()
        threshold = data.get('threshold', 1.5)
        # Update threshold in the main.py PeakDetector
        data_collector.peak_detector.threshold_multiplier = threshold
        return jsonify({'status': 'updated', 'threshold': threshold})
    
    return jsonify({'error': 'Data collector not initialized'})

@app.route('/api/sensitivity', methods=['POST'])
def update_sensitivity():
    """Update peak detection sensitivity"""
    global data_collector
    
    if data_collector:
        data = request.get_json()
        sensitivity = data.get('sensitivity', 10.0)
        
        # Update the main.py PeakDetector threshold multiplier
        data_collector.peak_detector.threshold_multiplier = sensitivity
        
        return jsonify({'status': 'updated', 'sensitivity': sensitivity})
    
    return jsonify({'error': 'Data collector not initialized'})

# HTML template moved to templates/dashboard.html

# Real phone data source - connects to existing main.py server
class RealPhoneDataSource(DataSource):
    """Connects to main.py server and waits for real phone data"""
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.start_time = time.time()
        self.data_queue = asyncio.Queue()
        self.connected = False
        self.setup_connection()
    
    def setup_connection(self):
        """Connect to main.py server to receive phone data"""
        import socketio
        import threading
        
        self.sio = socketio.Client()
        
        @self.sio.event
        def connect():
            print(f"📱 Connected to main.py, waiting for real phone data on port {self.port}")
            self.connected = True
        
        @self.sio.event
        def disconnect():
            print("❌ Disconnected from main.py")
            self.connected = False
        
        @self.sio.event
        def data(raw_data):
            """Receive data echoed by main.py from phones"""
            print(f"📡 Raw data received: {raw_data[:100] if isinstance(raw_data, str) else raw_data}")
            try:
                import json
                parsed = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                if isinstance(parsed, list):
                    for item in parsed:
                        # Get the actual data from phones
                        z_value = item.get('z', 0)
                        # Check if the key is included in the data
                        key = item.get('key', 'A')  # Get key if sent by main.py
                        # Normalize key to uppercase for consistency
                        key = key.upper() if isinstance(key, str) else key
                        print(f"📡 Parsed: z={z_value:.3f}, key={key}")
                        if loop:
                            # Queue the data with the actual key
                            asyncio.run_coroutine_threadsafe(
                                self.data_queue.put((z_value, key)), loop)
                        else:
                            print("⚠️ Loop not ready yet")
            except Exception as e:
                print(f"❌ Error processing phone data: {e}")
        
        def connect_thread():
            try:
                self.sio.connect(f'http://localhost:{self.port}')
                # Register with a key to receive broadcasts from main.py
                # We'll still parse the actual keys from the data
                self.sio.emit('key', 'A')  # Need to register to receive broadcasts
                self.sio.wait()
            except Exception as e:
                print(f"⚠️ Could not connect to main.py: {e}")
        
        thread = threading.Thread(target=connect_thread, daemon=True)
        thread.start()
        time.sleep(0.5)
    
    async def read(self) -> tuple[float, str]:
        """Wait for real phone data"""
        # This will block until real data arrives from a phone
        z_value, key = await self.data_queue.get()
        print(f"📱 Real data: z={z_value:.3f}, key={key}")
        return z_value, key

# Keep original simulated source for testing
class SimulatedDataSource(DataSource):
    """Simulated multi-key data for testing without real device"""
    
    def __init__(self):
        self.start_time = time.time()
        self.keys = ['A', 'B', 'C']
        self.key_index = 0
    
    async def read(self) -> tuple[float, str]:
        """Generate simulated multi-key data for testing"""
        await asyncio.sleep(0.016)
        current_time = time.time() - self.start_time
        
        # Rotate through keys
        key = self.keys[self.key_index]
        self.key_index = (self.key_index + 1) % len(self.keys)
        
        # Different sine waves for different keys
        base_value = 0.5
        if key == 'A':
            z_value = base_value + 0.3 * math.sin(current_time * 2 * math.pi)
        elif key == 'B':
            z_value = base_value + 0.2 * math.sin(current_time * 3 * math.pi + math.pi/4)
        else:  # key == 'C'
            z_value = base_value + 0.4 * math.sin(current_time * 1.5 * math.pi + math.pi/2)
        
        return round(z_value, 3), key

if __name__ == '__main__':
    print("🚀 Starting HackMIT Acceleration Dashboard...")
    print("📊 Dashboard available at: http://localhost:8080")
    print("📡 Ready to receive real data from HTTPDataSource on port 5000")
    print("💡 Send POST to /api/control/start with {use_real_data: true, port: 5000}")
    
    # Don't auto-start, let client control via API
    
    try:
        app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down dashboard...")
        stop_async_data_collection()
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
