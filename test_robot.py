#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI Smart Car - Robot Test Script
This script tests the basic functionality of the robot control system.
"""

import time
import sys
from LOBOROBOT import LOBOROBOT
from modules.robot import RobotController

def test_basic_movement():
    """Test basic movement functions of the robot."""
    print("Testing basic robot movement...")
    
    # Initialize the robot controller
    robot = RobotController()
    
    try:
        # Test forward movement
        print("Moving forward...")
        robot.set_differential_drive(0, 0.5, max_speed=30)
        time.sleep(2)
        
        # Test backward movement
        print("Moving backward...")
        robot.set_differential_drive(0, -0.5, max_speed=30)
        time.sleep(2)
        
        # Test turning left
        print("Turning left...")
        robot.set_differential_drive(-0.5, 0, max_speed=30)
        time.sleep(2)
        
        # Test turning right
        print("Turning right...")
        robot.set_differential_drive(0.5, 0, max_speed=30)
        time.sleep(2)
        
        # Test diagonal movement
        print("Moving diagonally forward-right...")
        robot.set_differential_drive(0.5, 0.5, max_speed=30)
        time.sleep(2)
        
        # Stop all motors
        print("Stopping...")
        robot.stop_all_motors()
        
        print("Basic movement test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during movement test: {str(e)}")
        # Make sure to stop motors on error
        robot.stop_all_motors()
        return False

def test_camera_servos():
    """Test camera servo control."""
    print("Testing camera servo control...")
    
    # Initialize the robot controller
    robot = RobotController()
    
    try:
        # Center camera
        print("Centering camera...")
        robot.center_camera()
        time.sleep(1)
        
        # Test pan left
        print("Panning left...")
        robot.control_camera_gimbal(-0.5, 0)
        time.sleep(1)
        
        # Test pan right
        print("Panning right...")
        robot.control_camera_gimbal(0.5, 0)
        time.sleep(1)
        
        # Test tilt up
        print("Tilting up...")
        robot.control_camera_gimbal(0, 0.5)
        time.sleep(1)
        
        # Test tilt down
        print("Tilting down...")
        robot.control_camera_gimbal(0, -0.5)
        time.sleep(1)
        
        # Center camera again
        print("Centering camera...")
        robot.center_camera()
        
        print("Camera servo test completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during camera servo test: {str(e)}")
        return False

def run_all_tests():
    """Run all robot tests."""
    print("Starting robot tests...")
    
    # Run movement test
    movement_result = test_basic_movement()
    
    # Run camera servo test
    camera_result = test_camera_servos()
    
    # Print summary
    print("\nTest Results:")
    print(f"Basic Movement: {'PASS' if movement_result else 'FAIL'}")
    print(f"Camera Servos: {'PASS' if camera_result else 'FAIL'}")
    
    if movement_result and camera_result:
        print("\nAll tests passed successfully!")
        return 0
    else:
        print("\nSome tests failed. Check the output for details.")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(run_all_tests())
    except KeyboardInterrupt:
        print("\nTests interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1) 