/**
 * AI Smart Car - Main JavaScript
 * This file handles the desktop web interface functionality.
 */

// Socket.IO connection
let socket;

// Joystick instances
let motionJoystick;
let cameraJoystick;

// UI elements
const connectionStatus = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');
const motionData = document.getElementById('motion-data');
const cameraData = document.getElementById('camera-data');
const mapOverlay = document.getElementById('map-overlay');
const mapCanvas = document.getElementById('map-canvas');
const toggleSlamButton = document.getElementById('toggle-slam');
const toggleMapButton = document.getElementById('toggle-map');
const centerCameraButton = document.getElementById('center-camera');
const emergencyStopButton = document.getElementById('emergency-stop');

// SLAM state
let slamActive = false;
let mapVisible = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    initSocketConnection();
    initJoysticks();
    initButtonHandlers();
    initMapCanvas();
});

// Initialize Socket.IO connection
function initSocketConnection() {
    // Connect to the server
    socket = io({
        reconnectionAttempts: 10,
        reconnectionDelay: 1000
    });

    // Connection events
    socket.on('connect', () => {
        connectionStatus.classList.remove('disconnected');
        connectionStatus.classList.add('connected');
        statusText.textContent = 'Connected';
        console.log('Connected to server');
    });

    socket.on('disconnect', () => {
        connectionStatus.classList.remove('connected');
        connectionStatus.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
        console.log('Disconnected from server');
    });

    // Data events
    socket.on('sensor_data', handleSensorData);
    socket.on('status_update', handleStatusUpdate);
    socket.on('error', handleError);
}

// Initialize joysticks
function initJoysticks() {
    // Motion control joystick
    motionJoystick = nipplejs.create({
        zone: document.getElementById('motion-joystick'),
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: 'blue',
        size: 120
    });

    // Camera control joystick
    cameraJoystick = nipplejs.create({
        zone: document.getElementById('camera-joystick'),
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: 'green',
        size: 120
    });

    // Motion joystick events
    motionJoystick.on('move', (evt, data) => {
        const x = parseFloat((data.vector.x).toFixed(2));
        const y = parseFloat((-data.vector.y).toFixed(2)); // Invert Y for intuitive control
        
        // Update UI
        motionData.textContent = `X: ${x}, Y: ${y}`;
        
        // Send control command to server
        socket.emit('control_command', { x, y });
    });

    motionJoystick.on('end', () => {
        // Stop when joystick is released
        motionData.textContent = 'X: 0, Y: 0';
        socket.emit('control_command', { x: 0, y: 0 });
    });

    // Camera joystick events
    cameraJoystick.on('move', (evt, data) => {
        const pan = parseFloat((data.vector.x).toFixed(2));
        const tilt = parseFloat((data.vector.y).toFixed(2));
        
        // Update UI
        cameraData.textContent = `Pan: ${pan.toFixed(2)}, Tilt: ${tilt.toFixed(2)}`;
        
        // Send camera control command to server
        socket.emit('camera_control', { pan, tilt });
    });

    cameraJoystick.on('end', () => {
        // Center camera when joystick is released
        cameraData.textContent = 'Pan: 0, Tilt: 0';
        socket.emit('camera_control', { pan: 0, tilt: 0 });
    });
}

// Initialize button handlers
function initButtonHandlers() {
    // Toggle SLAM button
    toggleSlamButton.addEventListener('click', () => {
        slamActive = !slamActive;
        socket.emit('toggle_slam', { active: slamActive });
        toggleSlamButton.textContent = slamActive ? 'Disable SLAM' : 'Enable SLAM';
    });

    // Toggle map visibility button
    toggleMapButton.addEventListener('click', () => {
        mapVisible = !mapVisible;
        if (mapVisible) {
            mapOverlay.classList.add('visible');
            toggleMapButton.textContent = 'Hide Map';
        } else {
            mapOverlay.classList.remove('visible');
            toggleMapButton.textContent = 'Show Map';
        }
    });

    // Center camera button
    centerCameraButton.addEventListener('click', () => {
        socket.emit('camera_control', { pan: 0, tilt: 0 });
        cameraData.textContent = 'Pan: 0, Tilt: 0';
    });

    // Emergency stop button
    emergencyStopButton.addEventListener('click', () => {
        socket.emit('control_command', { x: 0, y: 0 });
        motionData.textContent = 'X: 0, Y: 0';
        
        // Visual feedback
        emergencyStopButton.classList.add('active');
        setTimeout(() => {
            emergencyStopButton.classList.remove('active');
        }, 300);
    });
}

// Initialize map canvas
function initMapCanvas() {
    const ctx = mapCanvas.getContext('2d');
    ctx.fillStyle = '#333';
    ctx.fillRect(0, 0, mapCanvas.width, mapCanvas.height);
    ctx.fillStyle = '#fff';
    ctx.font = '14px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Map will appear here', mapCanvas.width / 2, mapCanvas.height / 2);
}

// Handle sensor data from server
function handleSensorData(data) {
    // Update IMU data
    if (data.imu) {
        // Accelerometer
        const accelX = document.querySelector('#accelerometer-data p:nth-child(1) span');
        const accelY = document.querySelector('#accelerometer-data p:nth-child(2) span');
        const accelZ = document.querySelector('#accelerometer-data p:nth-child(3) span');
        
        accelX.textContent = data.imu.accelerometer.x.toFixed(2);
        accelY.textContent = data.imu.accelerometer.y.toFixed(2);
        accelZ.textContent = data.imu.accelerometer.z.toFixed(2);
        
        // Gyroscope
        const gyroX = document.querySelector('#gyroscope-data p:nth-child(1) span');
        const gyroY = document.querySelector('#gyroscope-data p:nth-child(2) span');
        const gyroZ = document.querySelector('#gyroscope-data p:nth-child(3) span');
        
        gyroX.textContent = data.imu.gyroscope.x.toFixed(2);
        gyroY.textContent = data.imu.gyroscope.y.toFixed(2);
        gyroZ.textContent = data.imu.gyroscope.z.toFixed(2);
    }
    
    // Update SLAM data
    if (data.slam) {
        // Position
        const posX = document.querySelector('#position-data p:nth-child(1) span');
        const posY = document.querySelector('#position-data p:nth-child(2) span');
        const posZ = document.querySelector('#position-data p:nth-child(3) span');
        
        posX.textContent = data.slam.position.x.toFixed(2);
        posY.textContent = data.slam.position.y.toFixed(2);
        posZ.textContent = data.slam.position.z.toFixed(2);
        
        // Orientation
        const roll = document.querySelector('#orientation-data p:nth-child(1) span');
        const pitch = document.querySelector('#orientation-data p:nth-child(2) span');
        const yaw = document.querySelector('#orientation-data p:nth-child(3) span');
        
        roll.textContent = data.slam.orientation.roll.toFixed(2);
        pitch.textContent = data.slam.orientation.pitch.toFixed(2);
        yaw.textContent = data.slam.orientation.yaw.toFixed(2);
        
        // Update map if visible
        if (mapVisible && data.slam.occupancy_grid) {
            updateMapCanvas(data.slam.occupancy_grid);
        }
    }
}

// Handle status updates from server
function handleStatusUpdate(data) {
    // Update system status indicators
    document.getElementById('camera-status').textContent = data.camera_active ? 'Active' : 'Inactive';
    document.getElementById('imu-status').textContent = data.imu_calibrated ? 'Calibrated' : 'Not Calibrated';
    document.getElementById('slam-status').textContent = data.slam_active ? 'Active' : 'Inactive';
    document.getElementById('cpu-usage').textContent = `${data.cpu_usage}%`;
    document.getElementById('memory-usage').textContent = `${data.memory_usage}%`;
    document.getElementById('battery-level').textContent = `${data.battery_level}%`;
    
    // Update SLAM button state
    slamActive = data.slam_active;
    toggleSlamButton.textContent = slamActive ? 'Disable SLAM' : 'Enable SLAM';
}

// Handle error messages from server
function handleError(data) {
    console.error('Server error:', data.message);
    // Could add a visual notification here
}

// Update the map canvas with occupancy grid data
function updateMapCanvas(gridData) {
    // This is a placeholder - in a real implementation, 
    // we would render the occupancy grid data to the canvas
    // For now, we'll just show a simple visualization
    
    const ctx = mapCanvas.getContext('2d');
    ctx.clearRect(0, 0, mapCanvas.width, mapCanvas.height);
    
    // Draw a simple grid
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 1;
    
    const gridSize = 20;
    for (let x = 0; x < mapCanvas.width; x += gridSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, mapCanvas.height);
        ctx.stroke();
    }
    
    for (let y = 0; y < mapCanvas.height; y += gridSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(mapCanvas.width, y);
        ctx.stroke();
    }
    
    // Draw robot position (center)
    ctx.fillStyle = 'red';
    ctx.beginPath();
    ctx.arc(mapCanvas.width / 2, mapCanvas.height / 2, 5, 0, Math.PI * 2);
    ctx.fill();
} 