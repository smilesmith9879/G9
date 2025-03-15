#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Smart Four-Wheel Drive Car - Main Application
This is the main entry point for the AI Smart Car project.
It initializes the Flask server, WebSocket connections, and all required modules.
"""

import os
import time
import json
import threading
import logging
from flask import Flask, render_template, Response, request, jsonify
from flask_socketio import SocketIO, emit

# Import custom modules
from modules.robot import RobotController
from modules.camera import CameraStream
from modules.imu import IMUSensor
from modules.slam import SLAMProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'ai_smart_car_secret_key'
app.config['DEBUG'] = True

# Socket.IO settings
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_interval=25,
    ping_timeout=60
)

# Initialize modules
try:
    robot = RobotController()
    camera = CameraStream(resolution=(640, 480), framerate=10)
    imu = IMUSensor()
    slam = SLAMProcessor(camera, imu)
    
    # Start camera stream
    camera.start()
    
    # Start IMU data collection
    imu.start()
    
    # Initialize SLAM processing
    slam.start()
    
    logger.info("All modules initialized successfully")
except Exception as e:
    logger.error(f"Error initializing modules: {str(e)}")
    raise

# System status
system_status = {
    'connected': False,
    'camera_active': False,
    'slam_active': False,
    'imu_calibrated': False,
    'cpu_usage': 0,
    'memory_usage': 0,
    'battery_level': 100  # Placeholder for battery monitoring
}

# Routes
@app.route('/')
def index():
    """Render the main web interface."""
    return render_template('index.html')

@app.route('/mobile')
def mobile():
    """Render the mobile-optimized interface."""
    return render_template('mobile.html')

@app.route('/video_feed')
def video_feed():
    """Video streaming route for the camera feed."""
    return Response(
        camera.generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/status')
def get_status():
    """API endpoint to get system status."""
    return jsonify(system_status)

# Socket.IO event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.info(f"Client connected: {request.sid}")
    system_status['connected'] = True
    emit('status_update', system_status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {request.sid}")
    system_status['connected'] = False
    # Stop the robot for safety when connection is lost
    robot.stop_all_motors()

@socketio.on('control_command')
def handle_control_command(data):
    """Handle movement control commands from the client."""
    try:
        # Extract joystick values
        x = float(data.get('x', 0))  # Left/Right
        y = float(data.get('y', 0))  # Forward/Backward
        
        # Apply deadzone
        if abs(x) < 0.05:
            x = 0
        if abs(y) < 0.05:
            y = 0
            
        # Calculate motor speeds based on joystick position
        # Convert from -1:1 range to appropriate motor speed
        max_speed = 60  # Maximum speed as per specifications
        
        # If turning, reduce speed to 70%
        if abs(x) > 0.1:
            turning_factor = 0.7
        else:
            turning_factor = 1.0
            
        # Calculate individual motor speeds for differential steering
        robot.set_differential_drive(x, y, max_speed, turning_factor)
        
        # Log control commands at debug level
        logger.debug(f"Control command: x={x}, y={y}")
        
    except Exception as e:
        logger.error(f"Error processing control command: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('camera_control')
def handle_camera_control(data):
    """Handle camera gimbal control commands."""
    try:
        # Extract pan/tilt values
        pan = float(data.get('pan', 0))  # Left/Right
        tilt = float(data.get('tilt', 0))  # Up/Down
        
        # Apply deadzone
        if abs(pan) < 0.05:
            pan = 0
        if abs(tilt) < 0.05:
            tilt = 0
            
        # Control camera servos
        if pan == 0 and tilt == 0:
            # Auto-center if no input
            robot.center_camera()
        else:
            # Map joystick values to servo angles
            robot.control_camera_gimbal(pan, tilt)
            
        logger.debug(f"Camera control: pan={pan}, tilt={tilt}")
        
    except Exception as e:
        logger.error(f"Error processing camera control: {str(e)}")
        emit('error', {'message': str(e)})

@socketio.on('toggle_slam')
def handle_toggle_slam(data):
    """Toggle SLAM processing on/off."""
    try:
        active = bool(data.get('active', False))
        if active:
            slam.start()
        else:
            slam.stop()
        system_status['slam_active'] = active
        emit('status_update', system_status)
        logger.info(f"SLAM processing {'activated' if active else 'deactivated'}")
    except Exception as e:
        logger.error(f"Error toggling SLAM: {str(e)}")
        emit('error', {'message': str(e)})

# Background task to send sensor data and system status updates
def background_tasks():
    """Send periodic updates to connected clients."""
    while True:
        if system_status['connected']:
            try:
                # Get IMU data
                imu_data = imu.get_data()
                
                # Get SLAM data if active
                slam_data = slam.get_data() if system_status['slam_active'] else None
                
                # Update system status
                system_status['imu_calibrated'] = imu.is_calibrated()
                system_status['camera_active'] = camera.is_active()
                
                # Send data to client
                socketio.emit('sensor_data', {
                    'imu': imu_data,
                    'slam': slam_data,
                    'timestamp': time.time()
                })
                
                # Send system status update
                socketio.emit('status_update', system_status)
                
            except Exception as e:
                logger.error(f"Error in background task: {str(e)}")
        
        # Update at 5Hz as per specifications
        time.sleep(0.2)

# Start background tasks in a separate thread
background_thread = threading.Thread(target=background_tasks, daemon=True)
background_thread.start()

# Cleanup function to be called on shutdown
def cleanup():
    """Clean up resources before shutting down."""
    logger.info("Shutting down...")
    robot.stop_all_motors()
    camera.stop()
    imu.stop()
    slam.stop()

# Register cleanup function to be called on exit
import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    try:
        # Start the Flask-SocketIO server
        logger.info("Starting server on port 5000...")
        socketio.run(app, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Error running server: {str(e)}")
    finally:
        cleanup() 