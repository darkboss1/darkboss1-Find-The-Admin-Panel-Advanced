"""
Advanced Logging System for Find The Admin Panel Tool

This module provides an advanced logging system with the following features:
- Separate log files for errors, warnings, and general usage
- Master log that maintains full history
- System information logging
- Automatic log cleaning
- Usage statistics tracking
"""

import os
import sys
import time
import logging
import platform
import json
import shutil
import socket
import re
from datetime import datetime, timedelta
from pathlib import Path
from logging.handlers import RotatingFileHandler
import psutil
from typing import Dict, Any, Optional

# Global variable to store the singleton logger instance
_LOGGER_INSTANCE = None

class AdvancedLogger:
    """Advanced logging system with file rotation, separate log types, and usage statistics"""
    
    def __init__(self, log_dir="logs"):
        """Initialize the advanced logging system with separate log files for different log types"""
        self.log_dir = log_dir
        self.usage_stats_file = os.path.join(log_dir, "usage_stats.json")
        self.usage_stats = {
            "scans_count": 0,
            "total_scan_time": 0,
            "paths_scanned": 0,
            "panels_found": 0,
            "last_scan": None,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "errors_count": 0,
            "warnings_count": 0
        }
        
        # Create directories
        os.makedirs(log_dir, exist_ok=True)
        
        # Setup all loggers
        self._setup_loggers()
        
        # Log system information
        self._log_system_info()
        
        # Clean old logs
        self._clean_old_logs()
        
        # Load stats if exists
        self._update_stats()

    def _setup_loggers(self):
        """Setup all loggers with appropriate handlers and formatters"""
        # Create log files paths
        self.error_log = os.path.join(self.log_dir, "error.log")
        self.warning_log = os.path.join(self.log_dir, "warning.log")
        self.info_log = os.path.join(self.log_dir, "info.log")
        self.master_log = os.path.join(self.log_dir, "master.log")
        self.usage_log = os.path.join(self.log_dir, "usage.log")
        
        # Configure root logger
        logging.root.setLevel(logging.DEBUG)
        
        # Create logger for errors
        self.error_logger = logging.getLogger("error")
        self.error_logger.setLevel(logging.ERROR)
        error_handler = self._create_file_handler(self.error_log, logging.ERROR)
        self.error_logger.addHandler(error_handler)
        
        # Create logger for warnings
        self.warning_logger = logging.getLogger("warning")
        self.warning_logger.setLevel(logging.WARNING)
        warning_handler = self._create_file_handler(self.warning_log, logging.WARNING)
        self.warning_logger.addHandler(warning_handler)
        
        # Create logger for info
        self.info_logger = logging.getLogger("info")
        self.info_logger.setLevel(logging.INFO)
        info_handler = self._create_file_handler(self.info_log, logging.INFO)
        self.info_logger.addHandler(info_handler)
        
        # Create master logger for all levels
        self.master_logger = logging.getLogger("master")
        self.master_logger.setLevel(logging.DEBUG)
        master_handler = self._create_file_handler(self.master_log, logging.DEBUG)
        self.master_logger.addHandler(master_handler)
        
        # Create usage logger for statistics and important events
        self.usage_logger = logging.getLogger("usage")
        self.usage_logger.setLevel(logging.INFO)
        usage_handler = self._create_file_handler(self.usage_log, logging.INFO)
        self.usage_logger.addHandler(usage_handler)
        
        # Add console handler to master logger
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self._create_formatter(colored=True))
        self.master_logger.addHandler(console_handler)

    def _create_file_handler(self, log_file, level):
        """Create a file handler for a specific log file with proper rotation"""
        handler = RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5
        )
        handler.setLevel(level)
        handler.setFormatter(self._create_formatter())
        return handler

    def _create_formatter(self, colored=False):
        """Create a formatter for log messages"""
        if colored:
            return ColoredFormatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        else:
            return logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )

    def _log_system_info(self):
        """Log system information for diagnostic purposes"""
        system_info = {
            "platform": platform.platform(),
            "python_version": sys.version,
            "hostname": socket.gethostname(),
            "cpu_cores": psutil.cpu_count(),
            "total_memory": f"{psutil.virtual_memory().total / (1024**3):.2f} GB",
            "available_memory": f"{psutil.virtual_memory().available / (1024**3):.2f} GB"
        }
        
        self.master_logger.info("System Information:")
        for key, value in system_info.items():
            self.master_logger.info(f"  {key}: {value}")

    def _clean_old_logs(self):
        """Clean logs older than 30 days to prevent excessive disk usage"""
        try:
            current_time = datetime.now()
            cutoff_date = current_time - timedelta(days=30)
            
            # Check for old log files
            for filename in os.listdir(self.log_dir):
                filepath = os.path.join(self.log_dir, filename)
                
                # Skip non-files
                if not os.path.isfile(filepath):
                    continue
                    
                # Skip non-log files
                if not filename.endswith('.log') and not filename.endswith('.log.1'):
                    continue
                
                # Get file modification time
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                
                # Remove if older than cutoff date
                if file_time < cutoff_date:
                    os.remove(filepath)
                    self.master_logger.info(f"Removed old log file: {filename}")
        except Exception as e:
            self.master_logger.error(f"Error cleaning old logs: {str(e)}")

    def _update_stats(self):
        """Update usage statistics by loading from file if exists, or creating new"""
        try:
            if os.path.exists(self.usage_stats_file):
                with open(self.usage_stats_file, 'r') as f:
                    loaded_stats = json.load(f)
                    
                # Update current stats with loaded values, preserving new fields
                for key, value in loaded_stats.items():
                    if key in self.usage_stats:
                        self.usage_stats[key] = value
                        
                # Keep the current start time for the session
                self.usage_stats["last_session_start"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            else:
                # Save initial stats
                self._save_stats()
                
            # Log the usage stats loading
            self.usage_logger.info(f"Usage statistics loaded: {self.usage_stats}")
        except Exception as e:
            self.master_logger.error(f"Error updating stats: {str(e)}")
            
    def _save_stats(self):
        """Save current usage statistics to file"""
        try:
            with open(self.usage_stats_file, 'w') as f:
                json.dump(self.usage_stats, f, indent=4)
        except Exception as e:
            self.master_logger.error(f"Error saving usage stats: {str(e)}")
            
    def log_scan_start(self, url, mode, paths_count):
        """Log the start of a new scan with relevant information"""
        message = f"Scan started for {url} using mode {mode} with {paths_count} paths"
        # Only log to info_logger and master_logger once
        self.info_logger.info(message)
        
        # Update stats
        self.usage_stats["scans_count"] += 1
        self.usage_stats["last_scan"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._save_stats()

    def log_scan_end(self, url, duration, found_count, total_scanned):
        """Log the end of a scan with results summary"""
        message = (
            f"Scan completed for {url} in {duration:.2f} seconds. "
            f"Found {found_count} admin panels out of {total_scanned} paths."
        )
        self.usage_logger.info(message)
        self.master_logger.info(message)
        
        # Update stats
        self.usage_stats["total_scan_time"] += duration
        self.usage_stats["paths_scanned"] += total_scanned
        self.usage_stats["panels_found"] += found_count
        self._save_stats()
    
    def log_scan_complete(self, url, total_paths, found_count, scan_time):
        """Log scan completion with statistics"""
        message = f"Scan completed for {url}: found {found_count}/{total_paths} in {scan_time:.2f}s"
        self.usage_logger.info(message)
        self.master_logger.info(message)
    
    def log_results_exported(self, formats, count):
        """Log when results are exported to different formats"""
        formats_str = ", ".join(formats)
        message = f"Exported {count} results to formats: {formats_str}"
        self.usage_logger.info(message)
        self.master_logger.info(message)
    
    def log_settings_change(self, setting_name, old_value, new_value):
        """Log when a setting is changed"""
        message = f"Setting changed: {setting_name} from '{old_value}' to '{new_value}'"
        self.usage_logger.info(message)
        self.master_logger.info(message)
    
    def log_error(self, message, exc_info=None):
        """Log an error message with optional exception info"""
        self.error_logger.error(message, exc_info=exc_info)
        self.master_logger.error(message, exc_info=exc_info)
        # Update stats
        self.usage_stats["errors_count"] += 1
        self._save_stats()
    
    def log_warning(self, message):
        """Log a warning message"""
        self.warning_logger.warning(message)
        self.master_logger.warning(message)
        # Update stats
        self.usage_stats["warnings_count"] += 1
        self._save_stats()
    
    def log_info(self, message):
        """Log an informational message"""
        self.info_logger.info(message)
        self.master_logger.info(message)
    
    def log_debug(self, message):
        """Log a debug message"""
        self.master_logger.debug(message)
    
    def shutdown(self):
        """Properly shutdown the logging system and save final stats"""
        # Update the end time
        end_time = datetime.now()
        start_time = datetime.strptime(self.usage_stats["start_time"], "%Y-%m-%d %H:%M:%S")
        session_duration = (end_time - start_time).total_seconds()
        
        # Log session summary
        message = (
            f"Logging session ended. Duration: {session_duration:.2f} seconds. "
            f"Scans: {self.usage_stats['scans_count']}, "
            f"Errors: {self.usage_stats['errors_count']}, "
            f"Warnings: {self.usage_stats['warnings_count']}"
        )
        self.usage_logger.info(message)
        self.master_logger.info(message)
        
        # Save final stats
        self.usage_stats["last_shutdown"] = end_time.strftime("%Y-%m-%d %H:%M:%S")
        self.usage_stats["last_session_duration"] = session_duration
        self._save_stats()
        
        # Shutdown all loggers
        logging.shutdown()


class ColoredFormatter(logging.Formatter):
    """Formatter that adds colors to levelnames in terminal output"""
    
    COLORS = {
        'DEBUG': '\033[94m',  # blue
        'INFO': '\033[92m',   # green
        'WARNING': '\033[93m', # yellow
        'ERROR': '\033[91m',  # red
        'CRITICAL': '\033[91m\033[1m',  # bold red
        'RESET': '\033[0m'    # reset
    }
    
    def format(self, record):
        # Add colored level name to the record
        levelname = record.levelname
        if levelname in self.COLORS:
            colored_levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            record.levelname = colored_levelname
        
        # Use the default formatter
        return super().format(record)


def get_logger(log_dir="logs") -> AdvancedLogger:
    """Get singleton instance of the advanced logger
    
    Args:
        log_dir: Directory for log files
        
    Returns:
        AdvancedLogger instance
    """
    global _LOGGER_INSTANCE
    
    # Create the instance if it doesn't exist
    if _LOGGER_INSTANCE is None:
        _LOGGER_INSTANCE = AdvancedLogger(log_dir)
    
    return _LOGGER_INSTANCE 