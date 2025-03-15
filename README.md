# AI Smart Four-Wheel Drive Car

## Overview
This project implements an intelligent, four-wheel drive robotic platform that combines real-time control, visual SLAM (Simultaneous Localization and Mapping), sensor fusion, and an intuitive web/mobile interface. The system allows users to remotely control the car while simultaneously building a map of the environment and tracking the car's position in real-time.

## Features
- Real-time video streaming with pan/tilt camera control
- Differential drive system with proportional speed control
- MPU6050 IMU integration for improved motion tracking
- Visual SLAM for environment mapping and localization
- Responsive web interface for both desktop and mobile devices
- WebSocket-based communication for low-latency control

## Hardware Requirements
- Raspberry Pi 5 (recommended) or equivalent
- Four-wheel drive chassis with motors
- Camera (USB webcam or Raspberry Pi Camera)
- MPU6050 IMU sensor
- 2 servos for camera pan/tilt
- Power supply

## Software Dependencies
- Python 3.7+
- Flask
- OpenCV
- Socket.IO
- NumPy
- smbus2
- gpiozero

## Installation
1. Clone this repository:
   ```
   git clone https://github.com/yourusername/ai-smart-car.git
   cd ai-smart-car
   ```

2. Install required packages:
   ```
   pip install -r requirements.txt
   ```

3. Connect hardware components according to the wiring diagram

4. Run the server:
   ```
   python app.py
   ```

5. Access the web interface by navigating to:
   ```
   http://<raspberry-pi-ip>:5000
   ```

## Project Structure
- `app.py`: Main Flask application
- `static/`: Frontend assets (CSS, JS, images)
- `templates/`: HTML templates
- `modules/`: Python modules for different functionalities
  - `camera.py`: Camera and video streaming
  - `imu.py`: MPU6050 sensor interface
  - `slam.py`: SLAM implementation
  - `robot.py`: Robot control interface
- `LOBOROBOT.py`: Base robot control library

## License
MIT License
