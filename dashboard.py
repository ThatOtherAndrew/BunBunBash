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

app = Flask(__name__)

# Enhanced DataSource for 3-axis acceleration data
class AccelerationDataSource(DataSource):
    """3-axis acceleration data source compatible with HackMIT's async pattern"""
    
    def __init__(self):
        self.start_time = time.time()
        # Configuration parameters (similar to original app.py)
        self.ax_amplitude_primary = 0.5
        self.ax_amplitude_secondary = 0.2
        self.ax_frequency_primary = 0.5
        self.ax_frequency_secondary = 2.1
        self.ax_noise_level = 0.1
        
        self.ay_amplitude_cos = 0.3
        self.ay_amplitude_sin = 0.4
        self.ay_frequency_cos = 0.7
        self.ay_frequency_sin = 1.3
        self.ay_noise_level = 0.1
        
        self.az_base = 9.81
        self.az_variation_amplitude = 0.2
        self.az_variation_frequency = 0.3
        self.az_noise_level = 0.2
    
    async def read(self) -> Dict[str, float]:
        """Generate realistic 3-axis acceleration data"""
        await asyncio.sleep(0.1)  # 10Hz data rate
        
        current_time = time.time() - self.start_time
        
        # Generate X-axis acceleration
        ax = (self.ax_amplitude_primary * math.sin(current_time * self.ax_frequency_primary * 2 * math.pi) + 
              self.ax_amplitude_secondary * math.sin(current_time * self.ax_frequency_secondary * 2 * math.pi) + 
              random.uniform(-self.ax_noise_level, self.ax_noise_level))
        
        # Generate Y-axis acceleration
        ay = (self.ay_amplitude_cos * math.cos(current_time * self.ay_frequency_cos * 2 * math.pi) + 
              self.ay_amplitude_sin * math.sin(current_time * self.ay_frequency_sin * 2 * math.pi) + 
              random.uniform(-self.ay_noise_level, self.ay_noise_level))
        
        # Generate Z-axis acceleration
        az = (self.az_base + 
              self.az_variation_amplitude * math.sin(current_time * self.az_variation_frequency * 2 * math.pi) + 
              random.uniform(-self.az_noise_level, self.az_noise_level))
        
        return {
            'timestamp': current_time,
            'ax': round(ax, 3),
            'ay': round(ay, 3),
            'az': round(az, 3)
        }

class EnhancedPeakDetector(PeakDetector):
    """Enhanced PeakDetector with 3-axis support and callbacks"""
    
    def __init__(self, data_source: AccelerationDataSource):
        # Initialize with larger window for better peak detection
        super().__init__(data_source)
        self.window_length = 20
        self.window = []
        self.peak_threshold = 1.5
        self.detected_peaks = []
        self.peak_callback = None
        
    def set_peak_callback(self, callback: Callable):
        """Set callback for peak detection events"""
        self.peak_callback = callback
    
    async def tick(self) -> Dict[str, float]:
        """Enhanced tick method for 3-axis data"""
        data_point = await self.data_source.read()
        
        # Calculate magnitude for peak detection
        magnitude = math.sqrt(data_point['ax']**2 + data_point['ay']**2 + data_point['az']**2)
        data_point['magnitude'] = round(magnitude, 3)
        
        # Add to sliding window
        self.window.append(data_point)
        if len(self.window) > self.window_length:
            self.window.pop(0)
        
        # Peak detection on magnitude
        if len(self.window) >= 3:
            self.detect_peaks()
        
        return data_point
    
    def detect_peaks(self):
        """Detect peaks in the magnitude data"""
        if len(self.window) < 3:
            return
            
        # Check if current point is a peak
        current_idx = len(self.window) - 2  # Check second-to-last point
        if current_idx < 1:
            return
            
        current_mag = self.window[current_idx]['magnitude']
        prev_mag = self.window[current_idx - 1]['magnitude']
        next_mag = self.window[current_idx + 1]['magnitude']
        
        # Peak detection: current > neighbors and above threshold
        if (current_mag > prev_mag and current_mag > next_mag and 
            current_mag > self.peak_threshold):
            
            peak_data = self.window[current_idx].copy()
            peak_data['peak_type'] = 'magnitude'
            self.detected_peaks.append(peak_data)
            
            if self.peak_callback:
                self.peak_callback(peak_data)

# Global data storage and async components
acceleration_data = deque(maxlen=1000)
peak_detector: Optional[EnhancedPeakDetector] = None
data_source: Optional[AccelerationDataSource] = None
loop = None

def start_async_data_collection():
    """Start async data collection in background thread"""
    global peak_detector, data_source, loop
    
    def run_async_loop():
        global loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def data_collection_loop():
            while True:
                try:
                    data_point = await peak_detector.tick()
                    acceleration_data.append(data_point)
                except Exception as e:
                    print(f"Error in data collection: {e}")
                    await asyncio.sleep(0.1)
        
        loop.run_until_complete(data_collection_loop())
    
    # Initialize components
    data_source = AccelerationDataSource()
    peak_detector = EnhancedPeakDetector(data_source)
    
    # Set up peak callback
    def on_peak_detected(peak_data):
        print(f"Peak detected: {peak_data['magnitude']:.2f} at {peak_data['timestamp']:.2f}s")
    
    peak_detector.set_peak_callback(on_peak_detected)
    
    # Start background thread
    thread = threading.Thread(target=run_async_loop, daemon=True)
    thread.start()

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

@app.route('/api/data')
def get_latest_data():
    """Get the latest data point"""
    if acceleration_data:
        return jsonify(acceleration_data[-1])
    return jsonify({'error': 'No data available'})

@app.route('/api/data/history')
def get_data_history():
    """Get historical data"""
    limit = request.args.get('limit', 100, type=int)
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
    start_async_data_collection()
    return jsonify({'status': 'started'})

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

@app.route('/api/config/peak_threshold', methods=['POST'])
def update_peak_threshold():
    """Update peak detection threshold"""
    data = request.get_json()
    threshold = data.get('threshold', 1.5)
    
    if peak_detector:
        peak_detector.peak_threshold = float(threshold)
        return jsonify({'status': 'updated', 'threshold': threshold})
    
    return jsonify({'error': 'Peak detector not initialized'})

# HTML template moved to templates/dashboard.html

if __name__ == '__main__':
    print("🚀 Starting HackMIT Acceleration Dashboard...")
    print("📊 Dashboard available at: http://localhost:8080")
    print("🔍 Features: Async data generation, real-time peak detection, interactive visualization")
    
    try:
        app.run(host='0.0.0.0', port=8080, debug=True, threaded=True)
    except KeyboardInterrupt:
        print("\n⏹️  Shutting down dashboard...")
        stop_async_data_collection()
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
