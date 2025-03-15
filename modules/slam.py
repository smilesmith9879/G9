#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SLAM Module
This module implements visual SLAM (Simultaneous Localization and Mapping)
using camera data and IMU sensor fusion.

Note: This is a simplified implementation that simulates SLAM functionality.
For a full implementation, integration with RTAB-Map or other SLAM libraries
would be required.
"""

import time
import math
import logging
import threading
import numpy as np
import cv2

# Configure logging
logger = logging.getLogger(__name__)

class SLAMProcessor:
    """
    SLAM processor for visual mapping and localization.
    """
    
    def __init__(self, camera, imu):
        """
        Initialize the SLAM processor.
        
        Args:
            camera: Camera object for visual input
            imu: IMU sensor object for motion data
        """
        self.camera = camera
        self.imu = imu
        self.is_running = False
        self.lock = threading.Lock()
        
        # SLAM state
        self.position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self.orientation = {'roll': 0.0, 'pitch': 0.0, 'yaw': 0.0}
        self.map_points = []
        self.trajectory = []
        self.occupancy_grid = None
        
        # Feature tracking
        self.orb = cv2.ORB_create(nfeatures=500)
        self.last_frame = None
        self.last_keypoints = None
        self.last_descriptors = None
        
        # Matcher for feature matching
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        
        # Initialize occupancy grid (2D map)
        self.grid_size = 100  # 100x100 grid
        self.grid_resolution = 0.1  # 10cm per cell
        self.occupancy_grid = np.zeros((self.grid_size, self.grid_size), dtype=np.int8)
        self.grid_center = (self.grid_size // 2, self.grid_size // 2)
        
        logger.info("SLAM processor initialized")
    
    def start(self):
        """Start SLAM processing."""
        if self.is_running:
            return
        
        # Start the SLAM processing thread
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_slam)
        self.update_thread.daemon = True
        self.update_thread.start()
        
        logger.info("SLAM processing started")
    
    def stop(self):
        """Stop SLAM processing."""
        self.is_running = False
        logger.info("SLAM processing stopped")
    
    def _update_slam(self):
        """Background thread for SLAM processing."""
        while self.is_running:
            try:
                # Get current camera frame
                frame = self.camera.get_frame()
                
                if frame is not None:
                    # Process frame for SLAM
                    self._process_frame(frame)
                
                # Update at 5Hz
                time.sleep(0.2)
            except Exception as e:
                logger.error(f"Error in SLAM processing: {str(e)}")
                time.sleep(0.5)  # Sleep longer on error
    
    def _process_frame(self, frame):
        """
        Process a camera frame for SLAM.
        
        Args:
            frame: Camera frame to process
        """
        # Convert to grayscale for feature detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect ORB features
        keypoints, descriptors = self.orb.detectAndCompute(gray, None)
        
        # If this is the first frame, just store it
        if self.last_frame is None or self.last_keypoints is None or self.last_descriptors is None:
            self.last_frame = gray
            self.last_keypoints = keypoints
            self.last_descriptors = descriptors
            return
        
        # Match features between frames
        if len(keypoints) > 0 and len(self.last_keypoints) > 0 and descriptors is not None and self.last_descriptors is not None:
            matches = self.matcher.match(self.last_descriptors, descriptors)
            
            # Sort matches by distance
            matches = sorted(matches, key=lambda x: x.distance)
            
            # Use only good matches
            good_matches = matches[:min(30, len(matches))]
            
            if len(good_matches) >= 8:  # Need at least 8 points for homography
                # Extract matched keypoints
                src_pts = np.float32([self.last_keypoints[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                dst_pts = np.float32([keypoints[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)
                
                # Calculate homography
                H, mask = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, 5.0)
                
                if H is not None:
                    # Update position based on homography
                    self._update_position_from_homography(H)
                    
                    # Update map with new features
                    self._update_map(keypoints, good_matches)
        
        # Get IMU data for sensor fusion
        imu_data = self.imu.get_data()
        orientation = self.imu.get_orientation()
        
        # Update orientation from IMU
        with self.lock:
            self.orientation['roll'] = orientation['roll']
            self.orientation['pitch'] = orientation['pitch']
            # Yaw is estimated from visual odometry
        
        # Store current frame for next iteration
        self.last_frame = gray
        self.last_keypoints = keypoints
        self.last_descriptors = descriptors
        
        # Add current position to trajectory
        with self.lock:
            self.trajectory.append(self.position.copy())
            
            # Limit trajectory length
            if len(self.trajectory) > 100:
                self.trajectory = self.trajectory[-100:]
    
    def _update_position_from_homography(self, H):
        """
        Update position estimate from homography matrix.
        
        Args:
            H: Homography matrix
        """
        # Extract translation from homography
        tx = H[0, 2]
        ty = H[1, 2]
        
        # Scale factor (arbitrary for simulation)
        scale = 0.01
        
        # Update position
        with self.lock:
            self.position['x'] += tx * scale
            self.position['y'] += ty * scale
            
            # Estimate yaw from homography
            angle = math.atan2(H[1, 0], H[0, 0])
            self.orientation['yaw'] = angle * 180.0 / math.pi
    
    def _update_map(self, keypoints, matches):
        """
        Update the map with new feature points.
        
        Args:
            keypoints: Detected keypoints
            matches: Feature matches
        """
        # Add new map points
        with self.lock:
            for m in matches:
                # Convert keypoint to world coordinates (simplified)
                kp = keypoints[m.trainIdx]
                x = self.position['x'] + (kp.pt[0] - 320) * 0.01
                y = self.position['y'] + (kp.pt[1] - 240) * 0.01
                
                # Add to map points
                self.map_points.append({'x': x, 'y': y, 'z': 0})
                
                # Limit number of map points
                if len(self.map_points) > 1000:
                    self.map_points = self.map_points[-1000:]
            
            # Update occupancy grid
            self._update_occupancy_grid()
    
    def _update_occupancy_grid(self):
        """Update the 2D occupancy grid map."""
        # Convert robot position to grid coordinates
        grid_x = int(self.grid_center[0] + self.position['x'] / self.grid_resolution)
        grid_y = int(self.grid_center[1] + self.position['y'] / self.grid_resolution)
        
        # Ensure within grid bounds
        if 0 <= grid_x < self.grid_size and 0 <= grid_y < self.grid_size:
            # Mark current position as occupied
            self.occupancy_grid[grid_y, grid_x] = 100
            
            # Mark surrounding cells as free space
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    nx, ny = grid_x + dx, grid_y + dy
                    if 0 <= nx < self.grid_size and 0 <= ny < self.grid_size and (dx != 0 or dy != 0):
                        # Only mark as free if not already occupied
                        if self.occupancy_grid[ny, nx] < 50:
                            self.occupancy_grid[ny, nx] = 0
    
    def get_data(self):
        """
        Get current SLAM data.
        
        Returns:
            dict: SLAM data including position, orientation, and map
        """
        with self.lock:
            return {
                'position': self.position.copy(),
                'orientation': self.orientation.copy(),
                'trajectory': self.trajectory.copy(),
                'map_size': len(self.map_points),
                'occupancy_grid': self.occupancy_grid.copy()
            }
    
    def get_position(self):
        """
        Get current position estimate.
        
        Returns:
            dict: Position coordinates
        """
        with self.lock:
            return self.position.copy()
    
    def get_orientation(self):
        """
        Get current orientation estimate.
        
        Returns:
            dict: Orientation angles
        """
        with self.lock:
            return self.orientation.copy()
    
    def get_map_visualization(self, width=320, height=320):
        """
        Generate a visualization of the occupancy grid map.
        
        Args:
            width: Width of the output image
            height: Height of the output image
            
        Returns:
            numpy.ndarray: Map visualization image
        """
        with self.lock:
            # Create visualization image
            vis_map = np.zeros((self.grid_size, self.grid_size, 3), dtype=np.uint8)
            
            # Draw occupancy grid
            for y in range(self.grid_size):
                for x in range(self.grid_size):
                    if self.occupancy_grid[y, x] > 50:
                        # Occupied cell (black)
                        vis_map[y, x] = [0, 0, 0]
                    elif self.occupancy_grid[y, x] == 0:
                        # Free space (white)
                        vis_map[y, x] = [255, 255, 255]
                    else:
                        # Unknown (gray)
                        vis_map[y, x] = [128, 128, 128]
            
            # Draw robot position
            robot_x = int(self.grid_center[0] + self.position['x'] / self.grid_resolution)
            robot_y = int(self.grid_center[1] + self.position['y'] / self.grid_resolution)
            
            if 0 <= robot_x < self.grid_size and 0 <= robot_y < self.grid_size:
                # Draw robot as red dot
                cv2.circle(vis_map, (robot_x, robot_y), 2, (0, 0, 255), -1)
                
                # Draw orientation line
                yaw_rad = self.orientation['yaw'] * math.pi / 180.0
                end_x = int(robot_x + 5 * math.cos(yaw_rad))
                end_y = int(robot_y + 5 * math.sin(yaw_rad))
                cv2.line(vis_map, (robot_x, robot_y), (end_x, end_y), (0, 255, 0), 1)
            
            # Draw trajectory
            points = []
            for pos in self.trajectory:
                tx = int(self.grid_center[0] + pos['x'] / self.grid_resolution)
                ty = int(self.grid_center[1] + pos['y'] / self.grid_resolution)
                if 0 <= tx < self.grid_size and 0 <= ty < self.grid_size:
                    points.append((tx, ty))
            
            if len(points) > 1:
                for i in range(1, len(points)):
                    cv2.line(vis_map, points[i-1], points[i], (255, 0, 0), 1)
            
            # Resize to requested dimensions
            if vis_map.shape[0] != height or vis_map.shape[1] != width:
                vis_map = cv2.resize(vis_map, (width, height))
            
            return vis_map 