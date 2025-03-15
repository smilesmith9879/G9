#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Camera Module
This module handles camera initialization, video capture, and streaming.
"""

import cv2
import time
import logging
import threading
import numpy as np
from imutils.video import VideoStream

# Configure logging
logger = logging.getLogger(__name__)

class CameraStream:
    """
    Camera streaming class that handles video capture and processing.
    """
    
    def __init__(self, resolution=(640, 480), framerate=10):
        """
        Initialize the camera stream.
        
        Args:
            resolution (tuple): Resolution of the camera capture (width, height)
            framerate (int): Target framerate for the stream
        """
        self.resolution = resolution
        self.framerate = framerate
        self.stream = None
        self.frame = None
        self.jpeg_quality = 70  # JPEG quality (0-100)
        self.is_running = False
        self.lock = threading.Lock()
        
        # Frame processing settings
        self.target_fps = framerate
        self.last_frame_time = 0
        self.frame_interval = 1.0 / self.target_fps
        
        logger.info(f"Camera initialized with resolution {resolution} and target {framerate} FPS")
    
    def start(self):
        """Start the camera stream."""
        try:
            # Try to use the Raspberry Pi camera first
            try:
                self.stream = VideoStream(usePiCamera=True, resolution=self.resolution).start()
                logger.info("Using Raspberry Pi Camera")
            except:
                # Fall back to USB camera
                self.stream = VideoStream(src=0, resolution=self.resolution).start()
                logger.info("Using USB Camera")
            
            # Wait for camera to warm up
            time.sleep(2.0)
            
            # Start the frame update thread
            self.is_running = True
            self.update_thread = threading.Thread(target=self._update_frame)
            self.update_thread.daemon = True
            self.update_thread.start()
            
            logger.info("Camera stream started")
            return True
        except Exception as e:
            logger.error(f"Failed to start camera: {str(e)}")
            return False
    
    def stop(self):
        """Stop the camera stream."""
        self.is_running = False
        if self.stream is not None:
            self.stream.stop()
            logger.info("Camera stream stopped")
    
    def _update_frame(self):
        """Background thread to update the current frame."""
        while self.is_running:
            try:
                # Throttle frame capture to target FPS
                current_time = time.time()
                if (current_time - self.last_frame_time) >= self.frame_interval:
                    # Get frame from camera
                    frame = self.stream.read()
                    
                    # Process frame if valid
                    if frame is not None:
                        # Resize if needed
                        if frame.shape[1] != self.resolution[0] or frame.shape[0] != self.resolution[1]:
                            frame = cv2.resize(frame, self.resolution)
                        
                        # Store the frame with thread safety
                        with self.lock:
                            self.frame = frame
                            self.last_frame_time = current_time
                
                # Small sleep to prevent CPU overuse
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Error updating camera frame: {str(e)}")
                time.sleep(0.1)  # Sleep longer on error
    
    def get_frame(self):
        """
        Get the current frame.
        
        Returns:
            numpy.ndarray: Current camera frame or None if not available
        """
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return None
    
    def get_jpeg_frame(self):
        """
        Get the current frame as JPEG bytes.
        
        Returns:
            bytes: JPEG encoded frame or None if not available
        """
        frame = self.get_frame()
        if frame is not None:
            try:
                # Encode frame as JPEG
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
                if ret:
                    return jpeg.tobytes()
            except Exception as e:
                logger.error(f"Error encoding JPEG: {str(e)}")
        return None
    
    def generate_frames(self):
        """
        Generator function for streaming frames via HTTP.
        
        Yields:
            bytes: MJPEG frame data for streaming
        """
        while self.is_running:
            # Get JPEG encoded frame
            jpeg_frame = self.get_jpeg_frame()
            
            if jpeg_frame is not None:
                # Yield the frame in MJPEG format
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_frame + b'\r\n')
            else:
                # If no frame is available, yield an empty frame
                time.sleep(0.1)
    
    def is_active(self):
        """
        Check if the camera is active.
        
        Returns:
            bool: True if camera is running, False otherwise
        """
        return self.is_running and self.stream is not None
    
    def set_resolution(self, width, height):
        """
        Set a new resolution for the camera.
        
        Args:
            width (int): New width
            height (int): New height
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Store new resolution
            self.resolution = (width, height)
            
            # Restart the camera with new resolution
            was_running = self.is_running
            if was_running:
                self.stop()
                time.sleep(0.5)
            
            if was_running:
                self.start()
            
            logger.info(f"Camera resolution changed to {width}x{height}")
            return True
        except Exception as e:
            logger.error(f"Failed to set resolution: {str(e)}")
            return False
    
    def set_framerate(self, fps):
        """
        Set a new target framerate.
        
        Args:
            fps (int): New target framerate
        """
        if fps > 0:
            self.target_fps = fps
            self.frame_interval = 1.0 / self.target_fps
            logger.info(f"Target framerate set to {fps} FPS")
    
    def set_jpeg_quality(self, quality):
        """
        Set JPEG encoding quality.
        
        Args:
            quality (int): JPEG quality (0-100)
        """
        if 0 <= quality <= 100:
            self.jpeg_quality = quality
            logger.info(f"JPEG quality set to {quality}")
    
    def get_camera_info(self):
        """
        Get information about the camera.
        
        Returns:
            dict: Camera information
        """
        return {
            'resolution': self.resolution,
            'target_fps': self.target_fps,
            'jpeg_quality': self.jpeg_quality,
            'is_active': self.is_active()
        } 