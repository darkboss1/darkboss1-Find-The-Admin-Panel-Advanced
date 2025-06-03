"""
Utilities module for Find The Admin Panel

This module provides various utility functions used throughout the application,
including URL validation, file operations, and other helper functions.
"""

import os
import re
import sys
import signal
import asyncio
import urllib.parse
from typing import List, Dict, Any, Optional, Union, Tuple
from datetime import datetime, timedelta
import hashlib
import random
import string
import socket
import platform

# Import advanced logging
from scripts.logging import get_logger

# Initialize advanced logger
adv_logger = get_logger('logs')

def validate_url(url: str) -> Tuple[bool, str]:
    """Validate a URL and normalize it
    
    Args:
        url: URL to validate
        
    Returns:
        Tuple of (is_valid, normalized_url)
    """
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    # Validate URL format
    if not re.match(r'^https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}', url):
        return False, url
    
    # Add trailing slash if needed
    if not url.endswith('/'):
        url += '/'
    
    return True, url

def validate_path(path: str) -> str:
    """Validate and normalize a URL path
    
    Args:
        path: Path to validate
        
    Returns:
        Normalized path
    """
    # Remove leading slash if present
    if path.startswith('/'):
        path = path[1:]
    
    # URL encode the path
    path = urllib.parse.quote(path, safe='/')
    
    return path

def join_url(base_url: str, path: str) -> str:
    """Join a base URL and a path
    
    Args:
        base_url: Base URL
        path: Path to join
        
    Returns:
        Joined URL
    """
    # Ensure base URL ends with a slash
    if not base_url.endswith('/'):
        base_url += '/'
    
    # Remove leading slash from path if present
    if path.startswith('/'):
        path = path[1:]
    
    return urllib.parse.urljoin(base_url, path)

def count_lines_in_file(filepath: str) -> int:
    """Count the number of lines in a file
    
    Args:
        filepath: Path to the file
        
    Returns:
        Number of lines
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return sum(1 for line in f if line.strip())
    except Exception as e:
        adv_logger.log_error(f"Error counting lines in file {filepath}: {str(e)}")
        return 0

def md5_hash(text: str) -> str:
    """Generate MD5 hash of a string
    
    Args:
        text: String to hash
        
    Returns:
        MD5 hash as hex string
    """
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def generate_random_string(length: int = 8) -> str:
    """Generate a random string of specified length
    
    Args:
        length: Length of the string to generate
        
    Returns:
        Random string
    """
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def get_file_size(filepath: str) -> int:
    """Get the size of a file in bytes
    
    Args:
        filepath: Path to the file
        
    Returns:
        File size in bytes
    """
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        adv_logger.log_error(f"Error getting file size for {filepath}: {str(e)}")
        return 0

def format_file_size(size_bytes: int) -> str:
    """Format file size from bytes to human-readable format
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def get_system_info() -> Dict[str, str]:
    """Get system information
    
    Returns:
        Dictionary with system information
    """
    try:
        return {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': socket.gethostname(),
            'processor': platform.processor(),
            'python_version': platform.python_version()
        }
    except Exception as e:
        adv_logger.log_error(f"Error getting system info: {str(e)}")
        return {}

def setup_signal_handler(scanner) -> None:
    """Set up signal handler for keyboard interrupts
    
    Args:
        scanner: Scanner instance to stop on signal
        
    Returns:
        None
    """
    # Store the time of the last Ctrl+C press
    last_press_time = None
    press_count = 0
    
    def signal_handler(sig, frame):
        nonlocal last_press_time, press_count
        current_time = datetime.now()
        
        # If this is the first press or it's been more than 2 seconds since the last press
        if last_press_time is None or (current_time - last_press_time).total_seconds() > 2:
            press_count = 1
            last_press_time = current_time
            
            # If a scan is running, stop it
            if scanner and scanner.is_running():
                print("\n\nStopping scan. Press Ctrl+C again within 2 seconds to exit immediately.")
                adv_logger.log_warning("Scan interrupted by user (Ctrl+C)")
                scanner.stop()
            else:
                # If no scan is running, exit
                print("\n\nExiting...")
                adv_logger.log_info("Application exited by user (Ctrl+C)")
                sys.exit(0)
        else:
            # This is a second press within the timeout
            press_count += 1
            adv_logger.log_info("Application force exited by user (double Ctrl+C)")
            print("\n\nForce exiting...")
            sys.exit(0)
    
    # Register the signal handler
    signal.signal(signal.SIGINT, signal_handler)

async def run_with_timeout(coro, timeout):
    """Run a coroutine with a timeout
    
    Args:
        coro: Coroutine to run
        timeout: Timeout in seconds
        
    Returns:
        Result of the coroutine or None if timeout
    """
    try:
        return await asyncio.wait_for(coro, timeout)
    except asyncio.TimeoutError:
        return None

def group_by_status_code(results: List[Dict]) -> Dict[int, List[Dict]]:
    """Group results by status code
    
    Args:
        results: List of result dictionaries
        
    Returns:
        Dictionary with status codes as keys and lists of results as values
    """
    grouped = {}
    
    for result in results:
        status_code = result.get('status_code', 0)
        if status_code not in grouped:
            grouped[status_code] = []
        grouped[status_code].append(result)
    
    return grouped

def find_results_by_confidence(results: List[Dict], min_confidence: float = 0.7) -> List[Dict]:
    """Find results with confidence above threshold
    
    Args:
        results: List of result dictionaries
        min_confidence: Minimum confidence threshold
        
    Returns:
        Filtered list of results
    """
    return [r for r in results if r.get('confidence', 0) >= min_confidence] 