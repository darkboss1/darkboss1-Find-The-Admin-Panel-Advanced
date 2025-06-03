"""
Configuration module for Find The Admin Panel

This module handles configuration loading, validation, and management.
It provides a central Config class for storing and accessing application settings.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict

# Import advanced logging tool
from scripts.logging import get_logger

# Initialize advanced logger
adv_logger = get_logger('logs')

@dataclass
class Config:
    """Configuration loaded exclusively from config.json"""
    VERSION: str = ""
    DEVELOPER: str = ""
    GITHUB: str = ""
    TOOL_NAME: str = ""
    RELEASE_DATE: str = ""
    CACHE_TTL: int = 0
    CACHE_SIZE: int = 0
    MAX_CONCURRENT_TASKS: int = 0
    CONNECTION_TIMEOUT: int = 0
    READ_TIMEOUT: int = 0
    BATCH_SIZE: int = 0
    VERIFY_SSL: bool = False
    MAX_RETRIES: int = 0
    RETRY_DELAY: float = 0.0
    RETRY_JITTER: float = 0.0
    MAX_CONCURRENT_RETRIES: int = 0
    TIMEOUT_BACKOFF_FACTOR: float = 0.0
    AUTO_ADJUST_CONCURRENCY: bool = False
    MAX_TIMEOUT_THRESHOLD: int = 0
    USE_PROXIES: bool = False
    USE_HEADLESS_BROWSER: bool = False
    CAPTCHA_DETECTION: bool = False
    EXPORT_FORMATS: List[str] = field(default_factory=list)
    DETECTION_MODES: List[str] = field(default_factory=list)
    DETECTION_MODE: str = ""
    SCAN_FREQUENCY: str = ""
    MULTI_SITE_SCAN: bool = False
    LOGS_DIR: str = ""
    CUSTOM_PATHS_FILE: str = ""
    DEFAULT_WORDLIST: str = ""  
    MAX_PATHS: int = 0
    SAVE_RESULTS: bool = False
    RESULTS_DIR: str = ""
    USER_AGENTS: List[str] = field(default_factory=list)
    PROXIES: List[str] = field(default_factory=list)
    HEADERS_EXTRA: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """Load settings from config.json during initialization"""
        # Load settings
        self.load_config()
        
        # Validate important values and set defaults if needed
        self._validate_and_set_defaults()
    
    def _validate_and_set_defaults(self):
        """Validate essential settings and set defaults if missing"""
        # Check for user agents and set defaults if empty
        if not self.USER_AGENTS:
            default_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.6422.60 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15'
            ]
            self.USER_AGENTS = default_agents
            adv_logger.log_warning("USER_AGENTS not found in config.json or was empty. Using default user agents.")
            
            # Try to update config.json with default user agents
            try:
                config_file = "config/config.json"
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    
                    # Update USER_AGENTS in config data
                    config_data['USER_AGENTS'] = default_agents
                    
                    # Write updated config to file
                    with open(config_file, 'w') as f:
                        json.dump(config_data, f, indent=4)
                    
                    adv_logger.log_info("Updated config.json with default USER_AGENTS")
            except Exception as e:
                adv_logger.log_error(f"Failed to update config.json with default USER_AGENTS: {str(e)}")
        else:
            adv_logger.log_info(f"Using {len(self.USER_AGENTS)} user agents from config.json")
            
        # Set default wordlist path if not specified
        if not self.DEFAULT_WORDLIST:
            self.DEFAULT_WORDLIST = "paths/general_paths.json"
            adv_logger.log_info(f"Using default wordlist path: {self.DEFAULT_WORDLIST}")
            
            # Try to update config.json with default wordlist
            try:
                config_file = "config/config.json"
                if os.path.exists(config_file):
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    
                    # Update DEFAULT_WORDLIST in config data
                    config_data['DEFAULT_WORDLIST'] = self.DEFAULT_WORDLIST
                    
                    # Write updated config to file
                    with open(config_file, 'w') as f:
                        json.dump(config_data, f, indent=4)
                    
                    adv_logger.log_info("Updated config.json with DEFAULT_WORDLIST")
            except Exception as e:
                adv_logger.log_error(f"Failed to update config.json with DEFAULT_WORDLIST: {str(e)}")
    
    def save_config(self, filepath: str = "config/config.json"):
        """Save current configuration to a JSON file"""
        config_dict = {
            key: value for key, value in self.__dict__.items() 
            if not key.startswith('_') and not callable(value)
        }
        
        # Create config directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
        with open(filepath, 'w') as f:
            json.dump(config_dict, f, indent=4)
            
    def load_config(self, filepath: str = "config/config.json"):
        """Load configuration from config.json"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    config_data = json.load(f)
                
                # Update instance attributes from config file
                for key, value in config_data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
                
                adv_logger.log_info(f"Configuration loaded from {filepath}")
            else:
                adv_logger.log_warning(f"Configuration file {filepath} not found, using defaults")
                # Create directories for config file
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                
        except json.JSONDecodeError as e:
            adv_logger.log_error(f"Error parsing configuration file {filepath}: {str(e)}")
        except Exception as e:
            adv_logger.log_error(f"Error loading configuration: {str(e)}")

def setup_logging(config):
    """Set up logging handlers"""
    global adv_logger
    
    # Ensure log directory exists
    os.makedirs(config.LOGS_DIR, exist_ok=True)
    
    # Create advanced logger if not already initialized
    if adv_logger is None:
        adv_logger = get_logger(config.LOGS_DIR)
    
    # Log startup information
    adv_logger.log_info(f"Logging system initialized for {config.TOOL_NAME} v{config.VERSION}")
    
    return adv_logger

def setup_directories(config):
    """Ensure all required directories exist"""
    directories = [
        config.LOGS_DIR,
        config.RESULTS_DIR,
        os.path.dirname(config.CUSTOM_PATHS_FILE)
    ]
    
    try:
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                adv_logger.log_info(f"Created directory: {directory}")
                
        # Check general_paths.json exists, if not create a basic one
        if not os.path.exists(config.CUSTOM_PATHS_FILE):
            adv_logger.log_warning(f"General paths file {config.CUSTOM_PATHS_FILE} not found, creating a minimal version")
            with open(config.CUSTOM_PATHS_FILE, 'w') as f:
                json.dump([
                    "admin/", 
                    "admin.php", 
                    "administrator/", 
                    "login.php",
                    "wp-admin/",
                    "cp/",
                    "cpanel/",
                    "dashboard/"
                ], f, indent=4)
                
        return True
    except Exception as e:
        adv_logger.log_error(f"Failed to create directories: {str(e)}")
        return False

def load_paths(config) -> List[str]:
    """Load paths from the general_paths.json file"""
    paths_file = config.CUSTOM_PATHS_FILE
    paths = []
    
    try:
        # Create directory if it doesn't exist
        paths_dir = os.path.dirname(paths_file)
        if not os.path.exists(paths_dir):
            os.makedirs(paths_dir)
            adv_logger.log_info(f"Created paths directory: {paths_dir}")
        
        # Check if file exists, if not return empty list
        if not os.path.exists(paths_file):
            adv_logger.log_warning(f"General paths file not found: {paths_file}")
            return []
            
        with open(paths_file, 'r') as f:
            data = json.load(f)
            
        if not isinstance(data, list):
            adv_logger.log_error(f"Invalid format in {paths_file}. Expected a list.")
            return []
            
        paths = data
        
        # Track total available paths before limiting
        total_available_paths = len(paths)
        
        # Apply max paths limit if configured
        max_paths = config.MAX_PATHS
        if max_paths > 0 and max_paths < total_available_paths:
            paths = paths[:max_paths]
            adv_logger.log_info(f"Limiting paths to {max_paths} (from {total_available_paths} available)")
        elif max_paths > 0:
            adv_logger.log_info(f"Using all {total_available_paths} available paths")
        else:
            adv_logger.log_info(f"Using all {total_available_paths} available paths (no limit set)")
        
        adv_logger.log_info(f"Loaded {len(paths)} paths from {paths_file}")
        return paths
        
    except json.JSONDecodeError as e:
        adv_logger.log_error(f"Failed to parse {paths_file}: {str(e)}")
        return []
        
    except Exception as e:
        adv_logger.log_error(f"Error loading paths: {str(e)}")
        return [] 