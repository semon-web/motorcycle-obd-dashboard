"""
🏍️ Motorcycle OBD2 Dashboard Backend
Real-time telemetry monitoring system
"""

from flask import Flask, render_template, jsonify
from flask_cors import CORS
import threading
import time
import json
from datetime import datetime
from collections import deque

# Try to import OBD2 library (optional for testing)
try:
    import obd
    OBD_AVAILABLE = True
except ImportError:
    OBD_AVAILABLE = False
    print("⚠️  python-obd not installed. Using mock data.")

app = Flask(__name__)
CORS(app)

# ============================================
# 📊 DATA STORAGE
# ============================================

class MotorcycleData:
    def __init__(self):
        self.current = {
            'rpm': 0,
            'speed': 0,
            'coolant_temp': 0,
            'intake_temp': 0,
            'throttle_pos': 0,
            'engine_load': 0,
            'fuel_level': 0,
            'o2_voltage': 0,
            'maf_flow': 0,
            'ignition_timing': 0,
            'fuel_pressure': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        # Historical data for charts (last 100 readings)
        self.history = {
            'rpm': deque(maxlen=100),
            'speed': deque(maxlen=100),
            'coolant_temp': deque(maxlen=100),
            'intake_temp': deque(maxlen=100),
            'throttle_pos': deque(maxlen=100),
            'engine_load': deque(maxlen=100),
        }
        
        self.is_connected = False
        self.connection = None
        self.lock = threading.Lock()

motorcycle_data = MotorcycleData()

# ============================================
# 🔌 OBD2 CONNECTION MANAGEMENT
# ============================================

def connect_obd2():
    """Try to connect to OBD2 dongle"""
    if not OBD_AVAILABLE:
        return False
    
    try:
        motorcycle_data.connection = obd.OBD()
        if motorcycle_data.connection.is_connected():
            motorcycle_data.is_connected = True
            print("✅ OBD2 Connected!")
            return True
    except Exception as e:
        print(f"❌ OBD2 Connection Failed: {e}")
    
    return False

def read_obd2_data():
    """Read data from OBD2 dongle"""
    if not motorcycle_data.connection or not motorcycle_data.is_connected:
        return None
    
    try:
        data = {}
        
        # RPM
        rpm = motorcycle_data.connection.query(obd.commands.RPM)
        data['rpm'] = int(rpm.value.magnitude) if rpm.value else 0
        
        # Speed
        speed = motorcycle_data.connection.query(obd.commands.SPEED)
        data['speed'] = int(speed.value.magnitude) if speed.value else 0
        
        # Coolant Temperature
        coolant = motorcycle_data.connection.query(obd.commands.COOLANT_TEMP)
        data['coolant_temp'] = int(coolant.value.magnitude) if coolant.value else 0
        
        # Throttle Position
        throttle = motorcycle_data.connection.query(obd.commands.THROTTLE_POS)
        data['throttle_pos'] = int(throttle.value.magnitude) if throttle.value else 0
        
        # Engine Load
        load = motorcycle_data.connection.query(obd.commands.ENGINE_LOAD)
        data['engine_load'] = int(load.value.magnitude) if load.value else 0
        
        # Intake Temperature
        intake = motorcycle_data.connection.query(obd.commands.INTAKE_TEMP)
        data['intake_temp'] = int(intake.value.magnitude) if intake.value else 0
        
        return data
    except Exception as e:
        print(f"⚠️  Error reading OBD2: {e}")
        return None

def generate_mock_data():
    """Generate realistic mock data for testing"""
    import random
    
    # Simulate realistic motorcycle behavior
    current_rpm = motorcycle_data.current['rpm']
    current_speed = motorcycle_data.current['speed']
    
    # RPM changes gradually
    rpm_change = random.randint(-200, 300)
    new_rpm = max(800, min(12000, current_rpm + rpm_change))
    
    # Speed correlates with RPM
    speed_change = random.randint(-5, 8)
    new_speed = max(0, min(200, current_speed + speed_change))
    
    # Temperature increases with RPM
    temp_change = random.randint(-1, 2)
    new_temp = max(40, min(110, motorcycle_data.current['coolant_temp'] + temp_change))
    
    return {
        'rpm': int(new_rpm),
        'speed': int(new_speed),
        'coolant_temp': int(new_temp),
        'intake_temp': int(new_temp - random.randint(5, 15)),
        'throttle_pos': int((new_rpm / 12000) * 100 + random.randint(-10, 10)),
        'engine_load': int((new_rpm / 12000) * 100 + random.randint(-5, 5)),
        'fuel_level': random.randint(20, 100),
        'o2_voltage': round(random.uniform(0.1, 0.9), 2),
        'maf_flow': round(random.uniform(2, 25), 1),
        'ignition_timing': round(random.uniform(5, 35), 1),
        'fuel_pressure': round(random.uniform(2.5, 3.8), 2),
    }

def data_collection_thread():
    """Background thread to collect OBD2 data"""
    print("🔄 Data collection started...")
    
    while True:
        try:
            # Try to read from OBD2
            if motorcycle_data.is_connected:
                data = read_obd2_data()
            else:
                # Use mock data if not connected
                data = generate_mock_data()
            
            if data:
                with motorcycle_data.lock:
                    # Update current data
                    motorcycle_data.current.update(data)
                    motorcycle_data.current['timestamp'] = datetime.now().isoformat()
                    
                    # Store in history
                    for key in motorcycle_data.history:
                        if key in data:
                            motorcycle_data.history[key].append(data[key])
            
            time.sleep(1)  # Update every 1 second
            
        except Exception as e:
            print(f"⚠️  Error in data collection: {e}")
            time.sleep(2)

# ============================================
# 🌐 FLASK ROUTES
# ============================================

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/current')
def get_current_data():
    """Get current motorcycle telemetry"""
    with motorcycle_data.lock:
        return jsonify(motorcycle_data.current)

@app.route('/api/history')
def get_history():
    """Get historical data for charts"""
    with motorcycle_data.lock:
        history = {}
        for key, values in motorcycle_data.history.items():
            history[key] = list(values)
        return jsonify(history)

@app.route('/api/status')
def get_status():
    """Get connection status"""
    return jsonify({
        'obd_connected': motorcycle_data.is_connected,
        'mock_mode': not OBD_AVAILABLE,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/connect', methods=['POST'])
def connect():
    """Attempt to connect to OBD2 dongle"""
    if connect_obd2():
        return jsonify({'status': 'connected', 'message': '✅ OBD2 Connected'}), 200
    else:
        return jsonify({'status': 'disconnected', 'message': '❌ Connection Failed'}), 400

@app.route('/api/disconnect', methods=['POST'])
def disconnect():
    """Disconnect from OBD2 dongle"""
    if motorcycle_data.connection:
        motorcycle_data.connection.close()
        motorcycle_data.is_connected = False
    return jsonify({'status': 'disconnected', 'message': '🛑 Disconnected'}), 200

# ============================================
# 🚀 STARTUP
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("🏍️  MOTORCYCLE OBD2 DASHBOARD")
    print("=" * 50)
    
    # Try to connect to OBD2
    if OBD_AVAILABLE:
        connect_obd2()
    
    # Start data collection thread
    data_thread = threading.Thread(target=data_collection_thread, daemon=True)
    data_thread.start()
    
    # Run Flask app
    print("🌐 Starting server on http://127.0.0.1:5000")
    app.run(debug=True, port=5000, use_reloader=False)
