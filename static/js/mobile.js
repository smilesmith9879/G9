/**
 * AI Smart Car - Mobile JavaScript
 * This file handles the mobile web interface functionality.
 */

// Socket.IO connection
let socket;

// Joystick instances
let leftJoystick;
let rightJoystick;

// UI elements
const connectionStatus = document.getElementById('connection-status');
const statusText = document.getElementById('status-text');
const videoFeed = document.getElementById('video-feed');
const mapOverlay = document.getElementById('map-overlay');
const mapCanvas = document.getElementById('map-canvas');
const toggleMapButton = document.getElementById('toggle-map');
const toggleSlamButton = document.getElementById('toggle-slam');
const centerCameraButton = document.getElementById('center-camera');
const emergencyStopButton = document.getElementById('emergency-stop');
const orientationWarning = document.getElementById('orientation-warning');
const rollValue = document.getElementById('roll-value');
const pitchValue = document.getElementById('pitch-value');
const posXValue = document.getElementById('pos-x-value');
const posYValue = document.getElementById('pos-y-value');

// SLAM state
let slamActive = false;
let mapVisible = false;

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    checkOrientation();
    initSocketConnection();
    initJoysticks();
    initButtonHandlers();
    initMapCanvas();
    
    // Check orientation on resize
    window.addEventListener('resize', checkOrientation);
});

// Check device orientation
function checkOrientation() {
    if (window.innerHeight > window.innerWidth) {
        orientationWarning.classList.remove('hidden');
    } else {
        orientationWarning.classList.add('hidden');
    }
}

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
    // Left joystick (motion control)
    leftJoystick = nipplejs.create({
        zone: document.getElementById('left-joystick'),
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: 'blue',
        size: 100
    });

    // Right joystick (camera control)
    rightJoystick = nipplejs.create({
        zone: document.getElementById('right-joystick'),
        mode: 'static',
        position: { left: '50%', top: '50%' },
        color: 'green',
        size: 100
    });

    // Left joystick events (motion control)
    leftJoystick.on('move', (evt, data) => {
        const x = parseFloat((data.vector.x).toFixed(2));
        const y = parseFloat((-data.vector.y).toFixed(2)); // Invert Y for intuitive control
        
        // Send control command to server
        socket.emit('control_command', { x, y });
    });

    leftJoystick.on('end', () => {
        // Stop when joystick is released
        socket.emit('control_command', { x: 0, y: 0 });
    });

    // Right joystick events (camera control)
    rightJoystick.on('move', (evt, data) => {
        const pan = parseFloat((data.vector.x).toFixed(2));
        const tilt = parseFloat((data.vector.y).toFixed(2));
        
        // Send camera control command to server
        socket.emit('camera_control', { pan, tilt });
    });

    rightJoystick.on('end', () => {
        // Center camera when joystick is released
        socket.emit('camera_control', { pan: 0, tilt: 0 });
    });
}

// Initialize button handlers
function initButtonHandlers() {
    // Toggle map visibility button
    toggleMapButton.addEventListener('click', () => {
        mapVisible = !mapVisible;
        if (mapVisible) {
            mapOverlay.classList.remove('hidden');
        } else {
            mapOverlay.classList.add('hidden');
        }
    });

    // Toggle SLAM button
    toggleSlamButton.addEventListener('click', () => {
        slamActive = !slamActive;
        socket.emit('toggle_slam', { active: slamActive });
        toggleSlamButton.classList.toggle('active', slamActive);
    });

    // Center camera button
    centerCameraButton.addEventListener('click', () => {
        socket.emit('camera_control', { pan: 0, tilt: 0 });
    });

    // Emergency stop button
    emergencyStopButton.addEventListener('click', () => {
        socket.emit('control_command', { x: 0, y: 0 });
        
        // Visual feedback
        emergencyStopButton.classList.add('active');
        setTimeout(() => {
            emergencyStopButton.classList.remove('active');
        }, 300);
    });
    
    // Prevent default touch behavior on video feed to avoid browser gestures
    videoFeed.addEventListener('touchstart', (e) => {
        e.preventDefault();
    }, { passive: false });
    
    videoFeed.addEventListener('touchmove', (e) => {
        e.preventDefault();
    }, { passive: false });
}

// Initialize map canvas
function initMapCanvas() {
    const ctx = mapCanvas.getContext('2d');
    ctx.fillStyle = '#333';
    ctx.fillRect(0, 0, mapCanvas.width, mapCanvas.height);
    ctx.fillStyle = '#fff';
    ctx.font = '12px Arial';
    ctx.textAlign = 'center';
    ctx.fillText('Map', mapCanvas.width / 2, mapCanvas.height / 2);
}

// Handle sensor data from server
function handleSensorData(data) {
    // Update IMU data
    if (data.imu) {
        // Update orientation values
        rollValue.textContent = data.imu.accelerometer.x.toFixed(1) + '°';
        pitchValue.textContent = data.imu.accelerometer.y.toFixed(1) + '°';
    }
    
    // Update SLAM data
    if (data.slam) {
        // Update position values
        posXValue.textContent = data.slam.position.x.toFixed(1);
        posYValue.textContent = data.slam.position.y.toFixed(1);
        
        // Update map if visible
        if (mapVisible && data.slam.occupancy_grid) {
            updateMapCanvas(data.slam.occupancy_grid);
        }
    }
}

// Handle status updates from server
function handleStatusUpdate(data) {
    // Update SLAM button state
    slamActive = data.slam_active;
    toggleSlamButton.classList.toggle('active', slamActive);
}

// Handle error messages from server
function handleError(data) {
    console.error('Server error:', data.message);
    // Could add a visual notification here
}

// Update the map canvas with occupancy grid data
function updateMapCanvas(gridData) {
    // This is a simplified visualization
    const ctx = mapCanvas.getContext('2d');
    ctx.clearRect(0, 0, mapCanvas.width, mapCanvas.height);
    
    // Draw a simple grid
    ctx.strokeStyle = '#555';
    ctx.lineWidth = 1;
    
    const gridSize = 15;
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
    ctx.arc(mapCanvas.width / 2, mapCanvas.height / 2, 4, 0, Math.PI * 2);
    ctx.fill();
} 