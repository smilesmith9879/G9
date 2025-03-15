#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IMU Module
This module handles the MPU6050 IMU sensor for motion tracking.
"""

import time
import math
import logging
import threading
import numpy as np
import smbus2 as smbus

# Configure logging
logger = logging.getLogger(__name__)

class IMUSensor:
    """
    MPU6050 IMU sensor interface for motion tracking.
    """
    
    # MPU6050 Registers
    MPU6050_ADDR = 0x68
    PWR_MGMT_1 = 0x6B
    SMPLRT_DIV = 0x19
    CONFIG = 0x1A
    GYRO_CONFIG = 0x1B
    ACCEL_CONFIG = 0x1C
    INT_ENABLE = 0x38
    ACCEL_XOUT_H = 0x3B
    ACCEL_YOUT_H = 0x3D
    ACCEL_ZOUT_H = 0x3F
    GYRO_XOUT_H = 0x43
    GYRO_YOUT_H = 0x45
    GYRO_ZOUT_H = 0x47
    
    def __init__(self):
        """Initialize the IMU sensor."""
        self.bus = None
        self.is_running = False
        self.is_calibrated = False
        self.lock = threading.Lock()
        
        # Sensor data
        self.accel_data = {'x': 0, 'y': 0, 'z': 0}
        self.gyro_data = {'x': 0, 'y': 0, 'z': 0}
        self.temp_data = 0
        
        # Calibration values
        self.accel_bias = {'x': 0, 'y': 0, 'z': 0}
        self.gyro_bias = {'x': 0, 'y': 0, 'z': 0}
        
        # Conversion factors
        self.accel_scale = 16384.0  # for ±2g range
        self.gyro_scale = 131.0     # for ±250°/s range
        
        # Initialize the sensor
        try:
            self.bus = smbus.SMBus(1)
            self._initialize_sensor()
            logger.info("MPU6050 IMU sensor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MPU6050: {str(e)}")
            self.bus = None
    
    def _initialize_sensor(self):
        """Initialize the MPU6050 sensor."""
        if self.bus is None:
            return False
        
        try:
            # Wake up the MPU6050
            self.bus.write_byte_data(self.MPU6050_ADDR, self.PWR_MGMT_1, 0)
            
            # Set sample rate to 50Hz
            self.bus.write_byte_data(self.MPU6050_ADDR, self.SMPLRT_DIV, 19)
            
            # Set DLPF to 21Hz (bandwidth)
            self.bus.write_byte_data(self.MPU6050_ADDR, self.CONFIG, 4)
            
            # Set gyroscope range to ±250°/s
            self.bus.write_byte_data(self.MPU6050_ADDR, self.GYRO_CONFIG, 0)
            
            # Set accelerometer range to ±2g
            self.bus.write_byte_data(self.MPU6050_ADDR, self.ACCEL_CONFIG, 0)
            
            # Enable data ready interrupt
            self.bus.write_byte_data(self.MPU6050_ADDR, self.INT_ENABLE, 1)
            
            return True
        except Exception as e:
            logger.error(f"Error initializing MPU6050: {str(e)}")
            return False
    
    def _read_word(self, reg):
        """Read a word from the sensor."""
        high = self.bus.read_byte_data(self.MPU6050_ADDR, reg)
        low = self.bus.read_byte_data(self.MPU6050_ADDR, reg + 1)
        value = (high << 8) + low
        
        # Convert to signed value
        if value >= 0x8000:
            value = -((65535 - value) + 1)
            
        return value
    
    def _read_sensor_data(self):
        """Read raw sensor data from MPU6050."""
        if self.bus is None:
            return False
        
        try:
            # Read accelerometer data
            accel_x = self._read_word(self.ACCEL_XOUT_H)
            accel_y = self._read_word(self.ACCEL_YOUT_H)
            accel_z = self._read_word(self.ACCEL_ZOUT_H)
            
            # Read gyroscope data
            gyro_x = self._read_word(self.GYRO_XOUT_H)
            gyro_y = self._read_word(self.GYRO_YOUT_H)
            gyro_z = self._read_word(self.GYRO_ZOUT_H)
            
            # Read temperature data
            temp = self._read_word(0x41)
            temp = (temp / 340.0) + 36.53  # Convert to Celsius
            
            # Apply calibration and scaling
            with self.lock:
                # Accelerometer (convert to g)
                self.accel_data['x'] = (accel_x / self.accel_scale) - self.accel_bias['x']
                self.accel_data['y'] = (accel_y / self.accel_scale) - self.accel_bias['y']
                self.accel_data['z'] = (accel_z / self.accel_scale) - self.accel_bias['z']
                
                # Gyroscope (convert to degrees per second)
                self.gyro_data['x'] = (gyro_x / self.gyro_scale) - self.gyro_bias['x']
                self.gyro_data['y'] = (gyro_y / self.gyro_scale) - self.gyro_bias['y']
                self.gyro_data['z'] = (gyro_z / self.gyro_scale) - self.gyro_bias['z']
                
                # Temperature
                self.temp_data = temp
            
            return True
        except Exception as e:
            logger.error(f"Error reading MPU6050 data: {str(e)}")
            return False
    
    def calibrate(self):
        """
        Calibrate the IMU sensor.
        
        This collects multiple samples to determine sensor bias.
        The robot must remain stationary during calibration.
        """
        if self.bus is None:
            logger.error("Cannot calibrate: IMU not initialized")
            return False
        
        logger.info("Starting IMU calibration. Keep the robot stationary...")
        
        try:
            # Number of samples for calibration
            num_samples = 50
            
            # Temporary storage for calibration data
            accel_x_sum = 0
            accel_y_sum = 0
            accel_z_sum = 0
            gyro_x_sum = 0
            gyro_y_sum = 0
            gyro_z_sum = 0
            
            # Collect calibration samples
            for _ in range(num_samples):
                # Read raw sensor data
                accel_x = self._read_word(self.ACCEL_XOUT_H) / self.accel_scale
                accel_y = self._read_word(self.ACCEL_YOUT_H) / self.accel_scale
                accel_z = self._read_word(self.ACCEL_ZOUT_H) / self.accel_scale
                gyro_x = self._read_word(self.GYRO_XOUT_H) / self.gyro_scale
                gyro_y = self._read_word(self.GYRO_YOUT_H) / self.gyro_scale
                gyro_z = self._read_word(self.GYRO_ZOUT_H) / self.gyro_scale
                
                # Accumulate values
                accel_x_sum += accel_x
                accel_y_sum += accel_y
                accel_z_sum += accel_z
                gyro_x_sum += gyro_x
                gyro_y_sum += gyro_y
                gyro_z_sum += gyro_z
                
                # Small delay between samples
                time.sleep(0.05)
            
            # Calculate average bias values
            with self.lock:
                # Accelerometer bias (subtract 1g from z-axis due to gravity)
                self.accel_bias['x'] = accel_x_sum / num_samples
                self.accel_bias['y'] = accel_y_sum / num_samples
                self.accel_bias['z'] = (accel_z_sum / num_samples) - 1.0  # Subtract 1g
                
                # Gyroscope bias
                self.gyro_bias['x'] = gyro_x_sum / num_samples
                self.gyro_bias['y'] = gyro_y_sum / num_samples
                self.gyro_bias['z'] = gyro_z_sum / num_samples
                
                self.is_calibrated = True
            
            logger.info("IMU calibration completed successfully")
            logger.debug(f"Accel bias: {self.accel_bias}")
            logger.debug(f"Gyro bias: {self.gyro_bias}")
            
            return True
        except Exception as e:
            logger.error(f"Error during IMU calibration: {str(e)}")
            return False
    
    def start(self):
        """Start the IMU data collection."""
        if self.bus is None:
            logger.error("Cannot start: IMU not initialized")
            return False
        
        # Calibrate if not already done
        if not self.is_calibrated:
            self.calibrate()
        
        # Start the data collection thread
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_data)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        logger.info("IMU data collection started")
        return True
    
    def stop(self):
        """Stop the IMU data collection."""
        self.is_running = False
        logger.info("IMU data collection stopped")
    
    def _update_data(self):
        """Background thread to update IMU data."""
        while self.is_running:
            try:
                # Read sensor data
                self._read_sensor_data()
                
                # Update at 20Hz (50ms interval) as per specifications
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Error updating IMU data: {str(e)}")
                time.sleep(0.1)  # Sleep longer on error
    
    def get_data(self):
        """
        Get the current IMU data.
        
        Returns:
            dict: Dictionary containing accelerometer and gyroscope data
        """
        with self.lock:
            return {
                'accelerometer': self.accel_data.copy(),
                'gyroscope': self.gyro_data.copy(),
                'temperature': self.temp_data,
                'calibrated': self.is_calibrated
            }
    
    def get_orientation(self):
        """
        Calculate orientation from accelerometer data.
        
        Returns:
            dict: Roll and pitch angles in degrees
        """
        with self.lock:
            # Calculate roll and pitch from accelerometer data
            accel_x = self.accel_data['x']
            accel_y = self.accel_data['y']
            accel_z = self.accel_data['z']
            
            # Calculate roll (rotation around X-axis)
            roll = math.atan2(accel_y, math.sqrt(accel_x**2 + accel_z**2)) * 180.0 / math.pi
            
            # Calculate pitch (rotation around Y-axis)
            pitch = math.atan2(-accel_x, math.sqrt(accel_y**2 + accel_z**2)) * 180.0 / math.pi
            
            return {
                'roll': roll,
                'pitch': pitch
            } 