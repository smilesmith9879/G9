#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Robot Controller Module
This module provides a high-level interface to control the robot's motors and servos.
It uses the LOBOROBOT.py library for low-level hardware control.
"""

import time
import logging
import threading
from LOBOROBOT import LOBOROBOT

# Configure logging
logger = logging.getLogger(__name__)

class RobotController:
    """
    High-level robot control interface that manages motors and servos.
    """
    
    def __init__(self):
        """Initialize the robot controller."""
        try:
            # Initialize the LOBOROBOT controller
            self.robot = LOBOROBOT()
            logger.info("Robot controller initialized")
            
            # Initialize servo positions
            self.pan_angle = 80  # Initial horizontal servo angle (PWM9)
            self.tilt_angle = 40  # Initial vertical servo angle (PWM10)
            
            # Lock for thread safety
            self.lock = threading.Lock()
            
            # Set initial servo positions
            self.center_camera()
            
            # Motor state
            self.motor_speeds = [0, 0, 0, 0]  # Speed of each motor
            self.motor_directions = ['forward', 'forward', 'forward', 'forward']  # Direction of each motor
            
        except Exception as e:
            logger.error(f"Failed to initialize robot controller: {str(e)}")
            raise
    
    def set_differential_drive(self, x, y, max_speed=60, turning_factor=0.7):
        """
        Set differential drive based on joystick x, y values.
        
        Args:
            x (float): Joystick x-axis value (-1 to 1)
            y (float): Joystick y-axis value (-1 to 1)
            max_speed (int): Maximum motor speed (0-100)
            turning_factor (float): Speed reduction factor when turning
        """
        with self.lock:
            # Stop if no input
            if x == 0 and y == 0:
                self.stop_all_motors()
                return
            
            # Calculate base speed from y input (forward/backward)
            base_speed = abs(y) * max_speed
            
            # Determine forward or backward direction
            direction = 'forward' if y >= 0 else 'backward'
            
            # Calculate left and right motor speeds for differential steering
            left_speed = base_speed
            right_speed = base_speed
            
            # Apply turning based on x input
            if x != 0:
                # Reduce overall speed when turning
                left_speed *= turning_factor
                right_speed *= turning_factor
                
                # Differential steering calculation
                if x > 0:  # Turn right
                    left_speed += (x * max_speed * 0.5)
                    right_speed -= (x * max_speed * 0.5)
                else:  # Turn left
                    left_speed -= (abs(x) * max_speed * 0.5)
                    right_speed += (abs(x) * max_speed * 0.5)
            
            # Ensure speeds are within valid range
            left_speed = max(0, min(max_speed, left_speed))
            right_speed = max(0, min(max_speed, right_speed))
            
            # Determine individual motor directions and speeds
            if direction == 'forward':
                if x > 0.7:  # Sharp right turn
                    self.robot.turnRight(int(max_speed * 0.7), 0.1)
                elif x < -0.7:  # Sharp left turn
                    self.robot.turnLeft(int(max_speed * 0.7), 0.1)
                else:
                    # Set left motors (0, 2)
                    self.robot.MotorRun(0, direction, int(left_speed))
                    self.robot.MotorRun(2, direction, int(left_speed))
                    
                    # Set right motors (1, 3)
                    self.robot.MotorRun(1, direction, int(right_speed))
                    self.robot.MotorRun(3, direction, int(right_speed))
            else:  # backward
                if x > 0.7:  # Sharp right turn backward
                    self.robot.turnRight(int(max_speed * 0.7), 0.1)
                    self.robot.t_down(int(max_speed * 0.7), 0.1)
                elif x < -0.7:  # Sharp left turn backward
                    self.robot.turnLeft(int(max_speed * 0.7), 0.1)
                    self.robot.t_down(int(max_speed * 0.7), 0.1)
                else:
                    # Set left motors (0, 2)
                    self.robot.MotorRun(0, direction, int(left_speed))
                    self.robot.MotorRun(2, direction, int(left_speed))
                    
                    # Set right motors (1, 3)
                    self.robot.MotorRun(1, direction, int(right_speed))
                    self.robot.MotorRun(3, direction, int(right_speed))
            
            # Update motor state
            self.motor_speeds = [int(left_speed), int(right_speed), int(left_speed), int(right_speed)]
            self.motor_directions = [direction, direction, direction, direction]
            
            logger.debug(f"Motors set: L={left_speed}, R={right_speed}, dir={direction}")
    
    def stop_all_motors(self):
        """Stop all motors."""
        with self.lock:
            for motor in range(4):
                self.robot.MotorStop(motor)
            
            # Update motor state
            self.motor_speeds = [0, 0, 0, 0]
            logger.debug("All motors stopped")
    
    def control_camera_gimbal(self, pan, tilt):
        """
        Control the camera gimbal based on joystick input.
        
        Args:
            pan (float): Pan control value (-1 to 1)
            tilt (float): Tilt control value (-1 to 1)
        """
        with self.lock:
            # Calculate new angles based on joystick input
            # Pan (horizontal) servo - PWM9
            # Map from -1:1 to angle range (35° to 125°)
            if pan != 0:
                # Calculate new pan angle
                pan_change = pan * 2  # Adjust sensitivity
                new_pan_angle = self.pan_angle + pan_change
                
                # Ensure within valid range
                new_pan_angle = max(35, min(125, new_pan_angle))
                
                # Set servo if angle changed
                if new_pan_angle != self.pan_angle:
                    self.pan_angle = new_pan_angle
                    self.robot.set_servo_angle(9, int(self.pan_angle))
                    logger.debug(f"Pan servo set to {self.pan_angle}°")
            
            # Tilt (vertical) servo - PWM10
            # Map from -1:1 to angle range (0° to 85°)
            if tilt != 0:
                # Calculate new tilt angle
                tilt_change = tilt * 2  # Adjust sensitivity
                new_tilt_angle = self.tilt_angle - tilt_change  # Invert for intuitive control
                
                # Ensure within valid range
                new_tilt_angle = max(0, min(85, new_tilt_angle))
                
                # Set servo if angle changed
                if new_tilt_angle != self.tilt_angle:
                    self.tilt_angle = new_tilt_angle
                    self.robot.set_servo_angle(10, int(self.tilt_angle))
                    logger.debug(f"Tilt servo set to {self.tilt_angle}°")
    
    def center_camera(self):
        """Center the camera gimbal to default position."""
        with self.lock:
            # Set default positions
            self.pan_angle = 80
            self.tilt_angle = 40
            
            # Set servo angles
            self.robot.set_servo_angle(9, int(self.pan_angle))
            self.robot.set_servo_angle(10, int(self.tilt_angle))
            
            logger.debug("Camera centered to default position")
    
    def get_motor_status(self):
        """
        Get the current status of all motors.
        
        Returns:
            dict: Dictionary containing motor speeds and directions
        """
        with self.lock:
            return {
                'speeds': self.motor_speeds,
                'directions': self.motor_directions
            }
    
    def get_servo_status(self):
        """
        Get the current status of the servos.
        
        Returns:
            dict: Dictionary containing servo angles
        """
        with self.lock:
            return {
                'pan': self.pan_angle,
                'tilt': self.tilt_angle
            } 