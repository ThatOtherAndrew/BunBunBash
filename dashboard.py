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
    """Connects as a client to main.py's Socket.IO server to receive phone data"""
    
    def __init__(self, port=8000):
        self.data_queue = asyncio.Queue()
        self.start_time = time.time()
        self.connected = False
        self.port = port
        self.sio = None
        
    def setup_connection(self):
        """Setup Socket.IO connection - called after loop is available"""
        global loop
        self.sio = socketio_client.Client()
        
        @self.sio.event
        def connect():
            print(f"✅ Connected to main.py server on port {self.port}")
            self.connected = True
            
        @self.sio.event
        def disconnect():
            print("❌ Disconnected from main.py server")
            self.connected = False
            
        @self.sio.on('data')
        def on_data(data):
            # Forward the data to our async queue
            import json
            try:
                parsed = json.loads(data)
                if isinstance(parsed, list):
                    print(f"📡 Received batch of {len(parsed)} data points from main.py")
                    # Process ALL data points, not just the first one!
                    for i, item in enumerate(parsed):
                        z_value = item.get('z', 0)
                        print(f"   Point {i+1}/{len(parsed)}: z={z_value:.4f}")
                        if loop:
                            asyncio.run_coroutine_threadsafe(self.data_queue.put(z_value), loop)
                        else:
                            print("⚠️ Loop not available yet")
                    print(f"✅ Queued all {len(parsed)} points")
            except Exception as e:
                print(f"❌ Error parsing data: {e}")
        
        # Connect to main.py's server
        try:
            print(f"🔌 Connecting to main.py server at http://localhost:{self.port}...")
            self.sio.connect(f'http://localhost:{self.port}')
        except Exception as e:
            print(f"❌ Could not connect to main.py server: {e}")
    
    async def read(self) -> Dict[str, float]:
        """Read z-axis data from the queue"""
        z_value = await self.data_queue.get()
        print(f"✅ Processing z-value: {z_value:.4f} (Queue size: {self.data_queue.qsize()})")
        current_time = time.time() - self.start_time
        
        return {
            'timestamp': current_time,
            'ax': 0.0,
            'ay': 0.0,
            'az': round(z_value, 3)
        }

class MagnitudeDataSource(DataSource):
    """Adapter to convert 3-axis data to single magnitude for main.py PeakDetector"""
    
    def __init__(self, acceleration_source: DataSource):
        self.acceleration_source = acceleration_source
        self.latest_data = None
        
    async def read(self) -> tuple[float, str]:
        """Return magnitude from acceleration data"""
        data_point = await self.acceleration_source.read()
        self.latest_data = data_point

        # For real data, magnitude is just the z-axis value since x,y are 0
        # But we calculate properly in case we add more axes later
        magnitude = math.sqrt(data_point['ax']**2 + data_point['ay']**2 + data_point['az']**2)
        # Default to device 'A' for dashboard compatibility
        return magnitude, 'A'

class DashboardPeakAdapter:
    """Modular adapter that wraps main.py PeakDetector without inheritance"""
    
    def __init__(self, acceleration_source: DataSource):
        self.acceleration_source = acceleration_source
        self.magnitude_source = MagnitudeDataSource(acceleration_source)
        self.peak_detector = PeakDetector(self.magnitude_source)
        self.detected_peaks = []
        self.peak_callback = None
        
        # Override the on_peak method to capture peaks
        original_on_peak = self.peak_detector.on_peak
        def capture_peak(sample=None):
            if self.magnitude_source.latest_data:
                peak_data = self.magnitude_source.latest_data.copy()
                # Magnitude already calculated in latest_data
                peak_data['magnitude'] = round(math.sqrt(peak_data['ax']**2 + peak_data['ay']**2 + peak_data['az']**2), 3)
                peak_data['peak_type'] = 'magnitude'
                self.detected_peaks.append(peak_data)
                
                if self.peak_callback:
                    self.peak_callback(peak_data)
            
            # Call original method (handle both old and new signatures)
            if sample is not None:
                try:
                    original_on_peak(sample)
                except TypeError:
                    original_on_peak()
            else:
                original_on_peak()
        
        self.peak_detector.on_peak = capture_peak
        
    def set_peak_callback(self, callback: Callable):
        """Set callback for peak detection events"""
        self.peak_callback = callback
    
    async def tick(self) -> Dict[str, float]:
        """Use main.py PeakDetector directly - any changes to main.py will reflect here"""
        # This calls main.py's tick method directly
        magnitude = await self.peak_detector.tick()
        
        
        # Return the full 3-axis data with magnitude
        if self.magnitude_source.latest_data:
            data_point = self.magnitude_source.latest_data.copy()
            data_point['magnitude'] = round(magnitude, 3)
            return data_point
        
        return {'timestamp': 0, 'ax': 0, 'ay': 0, 'az': 0, 'magnitude': round(magnitude, 3)}
    
    @property
    def sensitivity(self):
        """Access main.py PeakDetector's sensitivity"""
        return self.peak_detector.sensitivity
    
    @sensitivity.setter
    def sensitivity(self, value):
        """Set main.py PeakDetector's sensitivity"""
        self.peak_detector.sensitivity = value

# Global data storage and async components
acceleration_data = deque(maxlen=1000)  # Store more data for smooth 60Hz operation
peak_detector: Optional[DashboardPeakAdapter] = None
data_source: Optional[DataSource] = None
loop = None
data_thread = None

def start_async_data_collection(use_real_data=True, port=5000):
    """Start async data collection in background thread
    
    Args:
        use_real_data: If True, use HTTPDataSource. If False, use simulated data.
        port: Port for HTTPDataSource when using real data
    """
    global peak_detector, data_source, loop, data_thread
    
    # Don't start multiple threads
    if data_thread and data_thread.is_alive():
        return
    
    def run_async_loop():
        global loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def data_collection_loop():
            print(f"🔄 Starting {'real' if use_real_data else 'simulated'} data collection...")
            if use_real_data:
                print(f"📡 Waiting for data on port {port}...")
            while True:
                try:
                    data_point = await peak_detector.tick()
                    acceleration_data.append(data_point)
                    # No sleep needed - HTTPDataSource will block until data arrives
                    if not use_real_data:
                        await asyncio.sleep(0.016)  # Only sleep for simulated data
                except Exception as e:
                    print(f"❌ Error in data collection: {e}")
                    import traceback
                    traceback.print_exc()
                    await asyncio.sleep(0.1)
        
        loop.run_until_complete(data_collection_loop())
    
    # Initialize components
    if use_real_data:
        data_source = SocketIOClientDataSource(port=port)
        data_source.setup_connection()  # Setup connection after loop exists
    else:
        data_source = SimulatedDataSource()
    peak_detector = DashboardPeakAdapter(data_source)
    
    # Set up peak callback
    def on_peak_detected(peak_data):
        pass
        # print(f"Peak detected: {peak_data['magnitude']:.2f} at {peak_data['timestamp']:.2f}s")
    
    peak_detector.set_peak_callback(on_peak_detected)
    
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

@app.route('/api/data/latest')
def get_latest_data():
    """Get the latest data point"""
    if acceleration_data:
        return jsonify(acceleration_data[-1])
    return jsonify({'error': 'No data available', 'timestamp': 0})

@app.route('/api/data/since/<timestamp>')
def get_data_since(timestamp):
    """Get all data points since a given timestamp - handles variable rates"""
    try:
        timestamp = float(timestamp)
    except (ValueError, TypeError):
        timestamp = 0.0
        
    if not acceleration_data:
        return jsonify([])
    
    # Find all points newer than the given timestamp
    new_points = [d for d in acceleration_data if d.get('timestamp', 0) > timestamp]
    return jsonify(new_points[-100:])  # Limit to last 100 to prevent huge responses

@app.route('/api/data/history')
def get_data_history():
    """Get historical data"""
    limit = request.args.get('limit', 500, type=int)
    data_list = list(acceleration_data)[-limit:]
    return jsonify(data_list)

@app.route('/api/peaks')
def get_detected_peaks():
    """Get detected peaks"""
    if peak_detector:
        return jsonify(peak_detector.detected_peaks[-50:])  # Last 50 peaks
    return jsonify([])

@app.route('/api/stats')
def get_statistics():
    """Get data statistics"""
    if not acceleration_data:
        return jsonify({'error': 'No data available'})
    
    data_list = list(acceleration_data)
    magnitudes = [d['magnitude'] for d in data_list if 'magnitude' in d]
    
    if magnitudes:
        stats = {
            'total_points': len(data_list),
            'current_magnitude': magnitudes[-1] if magnitudes else 0,
            'avg_magnitude': sum(magnitudes) / len(magnitudes),
            'max_magnitude': max(magnitudes),
            'detected_peaks': len(peak_detector.detected_peaks) if peak_detector else 0
        }
    else:
        stats = {
            'total_points': len(data_list),
            'current_magnitude': 0,
            'avg_magnitude': 0,
            'max_magnitude': 0,
            'detected_peaks': 0
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
    global acceleration_data
    acceleration_data.clear()
    if peak_detector:
        peak_detector.detected_peaks.clear()
        # Reset data source start time
        data_source.start_time = time.time()
    return jsonify({'status': 'cleared'})

@app.route('/api/control/threshold', methods=['POST'])
def update_threshold():
    """Update peak detection threshold"""
    global peak_detector
    
    if peak_detector:
        data = request.get_json()
        threshold = data.get('threshold', 1.5)
        # Update threshold logic here if needed
        return jsonify({'status': 'updated', 'threshold': threshold})
    
    return jsonify({'error': 'Peak detector not initialized'})

@app.route('/api/sensitivity', methods=['POST'])
def update_sensitivity():
    """Update PeakDetector sensitivity from main.py"""
    global peak_detector
    
    if peak_detector:
        data = request.get_json()
        sensitivity = data.get('sensitivity', 10.0)
        
        # Update the main.py PeakDetector sensitivity directly
        peak_detector.sensitivity = sensitivity
        
        return jsonify({'status': 'updated', 'sensitivity': sensitivity})
    
    return jsonify({'error': 'Peak detector not initialized'})

# HTML template moved to templates/dashboard.html

# Keep original simulated source for testing
class SimulatedDataSource(DataSource):
    """Simulated 3-axis acceleration data for testing without real device"""
    
    def __init__(self):
        self.start_time = time.time()
    
    async def read(self) -> Dict[str, float]:
        """Generate simulated data for testing"""
        await asyncio.sleep(0.016)
        current_time = time.time() - self.start_time
        
        # Simple sine wave for testing
        z_value = 9.81 + 0.5 * math.sin(current_time * 2 * math.pi)
        
        return {
            'timestamp': current_time,
            'ax': 0.0,
            'ay': 0.0,
            'az': round(z_value, 3)
        }

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
