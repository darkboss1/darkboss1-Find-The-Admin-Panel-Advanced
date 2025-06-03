"""
Scan Helper module for Find The Admin Panel

This module provides functions and utilities to optimize scanning operations
and improve scan speed while maintaining accuracy.
"""

import subprocess
import time
import os
import json
import sys
import urllib.parse
import argparse
import logging
import shutil
import requests
import signal
import asyncio
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import random
import re
import socket
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from typing import List, Dict, Any, Optional, Union, Tuple, Set
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
import ssl
import concurrent.futures
from aiohttp import ClientSession, TCPConnector, ClientTimeout
from aiohttp.client_exceptions import (
    ClientConnectionError, ClientPayloadError, 
    ClientResponseError, ServerDisconnectedError,
    TooManyRedirects, ServerTimeoutError,
)
# Import unified logging tool
from scripts.logging import get_logger

# Suppress InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# Setup unified logging system
adv_logger = get_logger('logs')
logger = logging.getLogger(__name__)

# Paths with pathlib for better cross-platform compatibility
SCRIPTS_DIR = Path(__file__).parent
ROOT_DIR = SCRIPTS_DIR.parent
CONFIG_DIR = ROOT_DIR / "config"
PATHS_DIR = ROOT_DIR / "paths"
RESULTS_DIR = ROOT_DIR / "results"
LOGS_DIR = ROOT_DIR / "logs"
GENERAL_PATHS_FILE = PATHS_DIR / "general_paths.json"
CHANGELOG_FILE = ROOT_DIR / "CHANGELOG.md"
CONFIG_FILE = CONFIG_DIR / "config.json"

# Create directories if they don't exist
for directory in [CONFIG_DIR, PATHS_DIR, RESULTS_DIR, LOGS_DIR]:
    directory.mkdir(exist_ok=True)

# Variables to track Ctrl+C presses
ctrl_c_pressed = 0
last_ctrl_c_time = 0
ctrl_c_timeout = 2  # seconds between presses to count as double-press
current_scan_results = {}
success_file = "success.txt"

# Define signal handler for Ctrl+C
def signal_handler(sig, frame):
    """Handle Ctrl+C key presses
    
    First press: Stop the current scan and display results
    Second press within timeout: Exit the application
    """
    global ctrl_c_pressed, last_ctrl_c_time
    
    current_time = time.time()
    
    # Check if it's a double press (within timeout period)
    if ctrl_c_pressed > 0 and (current_time - last_ctrl_c_time) < ctrl_c_timeout:
        print("\n\n[!] Exiting application (Ctrl+C pressed twice).")
        # Save any pending results
        save_results_to_success_file()
        sys.exit(0)
    
    # First press or timeout expired
    ctrl_c_pressed += 1
    last_ctrl_c_time = current_time
    
    if ctrl_c_pressed == 1:
        print("\n\n[!] Scan interrupted by user. Displaying current results...")
        
        # Display current results if available
        if current_scan_results:
            print("\nScan Summary (Interrupted)")
            print(f"Target URL: {current_scan_results.get('url', 'Unknown')}")
            print(f"Scan Modes: {', '.join(current_scan_results.get('modes', ['Unknown']))}")
            if 'results' in current_scan_results:
                for mode, result_data in current_scan_results['results'].items():
                    if isinstance(result_data, dict) and 'found' in result_data and 'total' in result_data:
                        print(f"Mode {mode}: Found {result_data['found']} panels out of {result_data['total']} paths checked")
                        
            # Save results to success.txt file
            save_results_to_success_file()
        else:
            print("\nNo results available yet.")
        
        print("\n[!] Press Ctrl+C again within 2 seconds to exit the application.")
        print("[!] Or press Enter to continue...")
        return

def save_results_to_success_file():
    """Save current scan results to success.txt file"""
    if not current_scan_results:
        return
        
    try:
        with open(success_file, 'a', encoding='utf-8') as f:
            f.write(f"\n--- Interrupted Scan Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f.write(f"Target: {current_scan_results.get('url', 'Unknown')}\n")
            f.write(f"Modes: {', '.join(current_scan_results.get('modes', ['Unknown']))}\n")
            
            if 'results' in current_scan_results:
                for mode, result_data in current_scan_results['results'].items():
                    if isinstance(result_data, dict) and 'found' in result_data:
                        f.write(f"Mode {mode}: Found {result_data['found']} panels\n")
                        
                        # Add details of found URLs if available
                        if 'found_urls' in result_data:
                            f.write("\nFound Admin Panels:\n")
                            for url_data in result_data['found_urls']:
                                f.write(f"- {url_data.get('url', 'Unknown')}\n")
                                if 'title' in url_data:
                                    f.write(f"  Title: {url_data['title']}\n")
                                if 'confidence' in url_data:
                                    f.write(f"  Confidence: {url_data['confidence']:.2f}\n")
            
            f.write("-" * 50 + "\n")
    except Exception as e:
        adv_logger.log_error(f"Error saving results to {success_file}: {str(e)}")

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# Load configuration from config.json for consistent settings
def load_config():
    """Load settings from the config.json file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            adv_logger.log_info(f"Loaded configuration from {CONFIG_FILE}")
            return config
        except Exception as e:
            adv_logger.log_error(f"Error loading config from {CONFIG_FILE}: {str(e)}")
    adv_logger.log_warning(f"Config file {CONFIG_FILE} not found or invalid, using default configuration")
    return {}

# Get config settings
config_data = load_config()

def print_banner():
    """Print tool banner with version information"""
    # Read version from config.json
    version = config_data.get("VERSION", "1.0.0")
    tool_name = config_data.get("TOOL_NAME", "Find The Admin Panel")
    developer = config_data.get("DEVELOPER", "Anonymous")
    github = config_data.get("GITHUB", "https://github.com/")
    
    banner = f"""
╔{"═" * 70}╗
║{" " * 70}║
║{tool_name.center(70)}║
║{f"Version {version}".center(70)}║
║{f"By {developer}".center(70)}║
║{f"{github}".center(70)}║
║{" " * 70}║
╚{"═" * 70}╝
"""
    print(banner)

def print_section(title):
    """Print a section header"""
    print("\n" + "═" * 80)
    print(f" {title} ".center(80, "="))
    print("═" * 80 + "\n")

def parse_url(url):
    """Parse and validate URL, ensuring proper format"""
    if not url:
        return None
        
    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
        
    try:
        parsed = urllib.parse.urlparse(url)
        return url
    except:
        return None

def run_command(command, description, show_output=True, capture_output=False):
    """Run a shell command with enhanced error handling and output management
    
    Args:
        command: The command to run
        description: Description of what the command does
        show_output: Whether to show the output in real-time
        capture_output: Whether to capture and return the output
    
    Returns:
        The command output if capture_output is True
    """
    global ctrl_c_pressed
    
    print_section(description)
    print(f"Command: {command}\n")
    
    start_time = time.time()
    result = None
    
    try:
        if show_output and not capture_output:
            # Show output in real-time
            result = subprocess.run(command, shell=True)
            if result.returncode != 0:
                print(f"\n[!] Command failed with exit code {result.returncode}")
                adv_logger.log_error(f"Command failed: {command}, exit code: {result.returncode}")
        elif capture_output:
            # Capture output to return
            result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, universal_newlines=True)
            if show_output:
                print(result)
        else:
            # Just run without showing output
            result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("Command executed silently.")
            if result.returncode != 0:
                print(f"Command failed with exit code {result.returncode}")
                print(result.stderr)
                adv_logger.log_error(f"Silent command failed: {command}, exit code: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"\n[!] Command execution error: {e}")
        print(e.output)
        adv_logger.log_error(f"Command execution error: {e}")
    except Exception as e:
        print(f"\n[!] Unexpected error: {str(e)}")
        adv_logger.log_error(f"Unexpected error in run_command: {str(e)}")
    
    execution_time = time.time() - start_time
    print(f"\nCommand completed in {execution_time:.2f} seconds")
    print("\n" + "═" * 80)
    
    # Check if Ctrl+C was pressed during command execution
    if ctrl_c_pressed > 0:
        print("\n[!] Command interrupted by user.")
        
    if capture_output:
        return result

def update_changelog(change_description, version="1.0.0"):
    """Update the CHANGELOG.md file with the new change description
    
    Args:
        change_description: Description of the change
        version: Version number for the change entry
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        change_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create the file if it doesn't exist
        if not CHANGELOG_FILE.exists():
            with open(CHANGELOG_FILE, 'w') as f:
                f.write("# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n")
        
        with open(CHANGELOG_FILE, 'r') as f:
            content = f.readlines()
            
        # Add the new change at the top of the file, after the header
        header_end = 3  # Assuming the header is the first 3 lines
        new_change = f"\n## [{version}] - {change_date}\n\n- {change_description}\n"
        content.insert(header_end, new_change)
        
        with open(CHANGELOG_FILE, 'w') as f:
            f.writelines(content)
            
        adv_logger.log_info(f"Changelog updated with: {change_description}")
        return True
    except Exception as e:
        adv_logger.log_error(f"Failed to update changelog: {str(e)}")
        return False

def save_temp_paths_file(paths, file_path):
    """Save a list of paths to a temporary file
    
    Args:
        paths: List of paths to save
        file_path: Path to save the file
    """
    try:
        with open(file_path, 'w') as f:
            json.dump(paths, f, indent=4)
    except Exception as e:
        adv_logger.log_error(f"Error saving temp paths file: {str(e)}")

def fetch_site_info(url, timeout=10):
    """Fetch basic information about a website, including server type and possible technologies
    
    Args:
        url: URL to check
        timeout: Request timeout in seconds
        
    Returns:
        dict: Information about the site
    """
    # Get configuration
    config = load_config()
    user_agents = config.get('USER_AGENTS', [])
    
    # Default info
    info = {
        'url': url,
        'status': None,
        'server': 'Unknown',
        'technologies': [],
        'headers': {},
        'title': 'Unknown',
        'language': 'en',  # Default language
        'response_time': 0,
        'content_length': 0
    }
    
    # Build proper URL
    if not url.startswith(('http://', 'https://')):
        url = f'http://{url}'
    
    # Use a random user agent from config
    if not user_agents:
        # Log warning if no user agents found in config
        adv_logger.log_warning("No user agents found in config.json")
        user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    else:
        user_agent = random.choice(user_agents)
    
    headers = {
        'User-Agent': user_agent,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5,ar;q=0.3',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        start_time = time.time()
        response = requests.get(
            url, 
            headers=headers, 
            timeout=timeout,
            verify=False,
            allow_redirects=True
        )
        response_time = time.time() - start_time
        
        info['status'] = response.status_code
        info['headers'] = dict(response.headers)
        info['response_time'] = response_time
        info['content_length'] = len(response.content)
        
        # Get server info
        if 'Server' in response.headers:
            info['server'] = response.headers['Server']
            
        # Check for common technologies
        tech_signatures = {
            'WordPress': ['wp-content', 'wp-includes', 'wp-admin'],
            'Joomla': ['joomla', 'com_content', 'com_users'],
            'Drupal': ['drupal', 'sites/all', 'sites/default'],
            'Laravel': ['laravel', 'csrf-token'],
            'Django': ['csrfmiddlewaretoken', 'django'],
            'Angular': ['ng-app', 'ng-controller', 'angular'],
            'React': ['react', 'react-dom', 'reactjs'],
            'Vue.js': ['vue', 'vue.js', 'vuejs'],
            'Bootstrap': ['bootstrap.css', 'bootstrap.min.css', 'bootstrap.js'],
            'jQuery': ['jquery.js', 'jquery.min.js'],
            'PHP': ['php', '.php'],
            'ASP.NET': ['asp.net', '.aspx', 'viewstate'],
            'Node.js': ['node_modules'],
            'Express': ['express', 'powered by express']
        }
        
        # Check response text for tech signatures
        for tech, signatures in tech_signatures.items():
            if any(sig.lower() in response.text.lower() for sig in signatures):
                info['technologies'].append(tech)
                
        # Try to extract title
        title_match = re.search('<title>(.*?)</title>', response.text, re.IGNORECASE)
        if title_match:
            info['title'] = title_match.group(1).strip()
            
        return info
        
    except requests.exceptions.Timeout:
        adv_logger.log_warning(f"Request timeout for {url}")
    except requests.exceptions.ConnectionError:
        adv_logger.log_warning(f"Connection error for {url}")
    except requests.exceptions.RequestException as e:
        adv_logger.log_error(f"Request error for {url}: {str(e)}")
    except Exception as e:
        adv_logger.log_error(f"Error fetching site info: {str(e)}")
        
    return info

def detect_site_language(url):
    """Detect the language of the site and get appropriate paths with enhanced analysis"""
    print_section("Detecting Site Language")
    print(f"Analyzing URL: {url}")
    
    # First fetch basic site info
    site_info = fetch_site_info(url)
    
    # Print site info for better user feedback
    print(f"Status Code: {site_info['status']}")
    print(f"Server: {site_info['server']}")
    print(f"Title: {site_info['title']}")
    print(f"Technologies: {', '.join(site_info['technologies'])}")
    print(f"Response Time: {site_info['response_time']:.2f}s")
    print(f"Content Length: {site_info['content_length']} bytes")

    # Always use general_paths.json as the only source of paths
    print(f"Using general paths from: {GENERAL_PATHS_FILE}")
    return str(GENERAL_PATHS_FILE), "en", ["en"], False
    
def check_internet_connection():
    """Check if internet connection is available"""
    try:
        # Try to connect to Google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def clean_url(url):
    """Ensure URL has a proper scheme with validation"""
    # Check for obvious invalid URLs
    if not url or len(url) < 3:
        raise ValueError("URL is too short or empty")
    
    # Remove whitespace
    url = url.strip()
    
    # Fix common URL entry mistakes
    url = re.sub(r'^([a-zA-Z0-9][-a-zA-Z0-9]*\.)+[a-zA-Z]{2,}(:[0-9]+)?.*$', 
                lambda m: f"https://{m.group(0)}" if not m.group(0).startswith(('http://', 'https://')) else m.group(0), 
                url)
    
    # Ensure proper scheme
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'
    
    # Validate basic URL structure
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        raise ValueError("Invalid URL format")
    
    return url

def create_timestamp_dir(base_dir, prefix="scan"):
    """Create a timestamped directory for results"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    dir_path = os.path.join(base_dir, f"{prefix}_{timestamp}")
    os.makedirs(dir_path, exist_ok=True)
    return dir_path

def parse_args():
    """Parse command line arguments with enhanced options"""
    parser = argparse.ArgumentParser(
        description="Advanced Admin Panel Finder - Smart Scan Helper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("-u", "--url", help="Target URL to scan")
    parser.add_argument("--mode", choices=["all", "aggressive", "stealth", "simple"], default="all",
                      help="Scan mode (default: all)")
    parser.add_argument("--concurrency", type=int, default=50,
                      help="Number of concurrent requests")
    parser.add_argument("--timeout", type=int, default=30,
                      help="Request timeout in seconds")
    parser.add_argument("--no-verify", action="store_true",
                      help="Disable SSL verification")
    parser.add_argument("--quiet", action="store_true",
                      help="Suppress detailed output")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    return parser.parse_args()

def count_paths(file_path):
    """Count the number of paths in a JSON file"""
    try:
        with open(file_path, 'r') as f:
            paths = json.load(f)
        return len(paths)
    except Exception as e:
        adv_logger.log_error(f"Error counting paths in {file_path}: {str(e)}")
        return 0

def main():
    """Main function to run the scan helper with enhanced workflow"""
    global ctrl_c_pressed, last_ctrl_c_time, current_scan_results
    
    # Reset Ctrl+C counter on start
    ctrl_c_pressed = 0
    last_ctrl_c_time = 0
    
    args = parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        adv_logger.log_info("Debug logging enabled")
    
    print_banner()
    
    # Check internet connection
    if not check_internet_connection():
        print("[!] Warning: No internet connection detected. The scanner may not work properly.")
        if input("Continue anyway? (y/n): ").lower() != 'y':
            sys.exit(0)
    
    try:
        # Get target URL
        url = args.url
        if not url:
            url = input("Enter the target URL (e.g., https://example.com): ").strip()
            if not url:
                print("[!] Error: URL cannot be empty")
                return
        
        try:
            url = clean_url(url)
            print(f"\n[+] Target set to: {url}")
        except ValueError as e:
            print(f"[!] Error: {str(e)}")
            return
        
        # Determine output directory
        output_dir = create_timestamp_dir(str(RESULTS_DIR))
        print(f"[+] Results will be saved to: {output_dir}")
        
        # Check if general_paths.json exists
        if not os.path.exists(GENERAL_PATHS_FILE):
            print(f"[!] Warning: General paths file {GENERAL_PATHS_FILE} not found!")
            sys.exit(1)
        else:
            print(f"[+] Found general paths file with {count_paths(GENERAL_PATHS_FILE)} paths")
        
        # Always use general_paths.json as source of paths
        paths_file = str(GENERAL_PATHS_FILE)
        primary_lang = "en"
        all_langs = ["en"]
        
        # Create base filename
        url_safe = urllib.parse.quote_plus(url)
        base_name = f"{url_safe}_{primary_lang}"
        
        # Run scans based on selected mode
        scan_modes = []
        if args.mode == "all":
            scan_modes = ["aggressive", "stealth", "simple"]
        else:
            scan_modes = [args.mode]
        
        print(f"[+] Running scans with modes: {', '.join(scan_modes)}")
        print(f"[+] Using paths from: {paths_file}")
        
        # Update current_scan_results with initial info
        current_scan_results = {
            'url': url,
            'modes': scan_modes,
            'results': {}
        }
        
        # Store results for each mode
        scan_results = {}
        
        for mode in scan_modes:
            # Check if Ctrl+C was pressed
            if ctrl_c_pressed > 0:
                print(f"\n[!] Scan for mode {mode} skipped due to user interruption.")
                continue
                
            # Build command with enhanced options
            command = (
                f"python {os.path.join(ROOT_DIR, 'finder.py')} "
                f"-u {url} "
                f"--mode {mode} "
                f"-p {paths_file} "
                f"--concurrency {args.concurrency} "
                f"-j -h "  # Always generate JSON and HTML reports
                f"--timeout {args.timeout} "
            )
            
            # Add optional arguments
            if args.no_verify:
                command += "--no-verify "
                
            if args.quiet:
                command += "--quiet "
                
            if args.debug:
                command += "--debug "
                
            # Add output directory
            command += f"--output {os.path.join(output_dir, f'{base_name}_{mode}')}"
            
            # Run scan
            result = run_command(
                command,
                f"Running {mode} scan for {url} using general paths",
                show_output=not args.quiet,
                capture_output=args.quiet
            )
            
            scan_results[mode] = result
            
            # Check if the result file was created
            result_file = os.path.join(output_dir, f'{base_name}_{mode}.json')
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        results_data = json.load(f)
                        found_count = sum(1 for item in results_data.get('results', []) if item.get('found', False))
                        total_count = len(results_data.get('results', []))
                        
                        # Update current results for Ctrl+C handler
                        current_scan_results['results'][mode] = {
                            'found': found_count,
                            'total': total_count,
                            'file': result_file
                        }
                except Exception as e:
                    adv_logger.log_error(f"Error reading scan results for {mode}: {str(e)}")
        
        # Combine results from all scans
        print_section("Scan Summary")
        print(f"Target URL: {url}")
        print(f"Used path source: {paths_file}")
        print(f"Modes used: {', '.join(scan_modes)}")
        print(f"Results saved to: {output_dir}")
        
        # Check for result files
        for mode in scan_modes:
            result_file = os.path.join(output_dir, f'{base_name}_{mode}.json')
            html_report = os.path.join(output_dir, f'{base_name}_{mode}.html')
            
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r', encoding='utf-8') as f:
                        results = json.load(f)
                        
                    found_count = sum(1 for item in results.get('results', []) if item.get('found', False))
                    total_count = len(results.get('results', []))
                    
                    print(f"\n[+] {mode.capitalize()} scan results:")
                    print(f"    - Found: {found_count} potential admin panels")
                    print(f"    - Total URLs scanned: {total_count}")
                    if found_count > 0:
                        print(f"    - HTML report: {html_report}")
                except Exception as e:
                    print(f"[!] Error reading results from {result_file}: {str(e)}")
        
        # Update changelog with scan information
        scan_info = f"Scan completed for {url}\n- Scan modes: {', '.join(scan_modes)}\n- Results saved to: {output_dir}"
        update_changelog(scan_info)
        
        # Provide next steps
        print("\n" + "═" * 80)
        print("[+] All scans completed. Check the results directory for findings.")
        print("[+] Remember to review the HTML reports for detailed information.")
        print("═" * 80)
    
    except KeyboardInterrupt:
        # This might not be reached due to our signal handler
        print("\n\n[!] Scan interrupted by user. Exiting...")
    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
        adv_logger.log_error("An error occurred during execution", exc_info=True)
    finally:
        if ctrl_c_pressed == 0:
            sys.exit(0)
        else:
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Scan interrupted by user. Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n[!] Error: {str(e)}")
        adv_logger.log_error("An error occurred during execution", exc_info=True)
        sys.exit(1)

class ScanOptimizer:
    """Optimizes scan operations to improve speed and efficiency"""
    
    def __init__(self, config):
        self.config = config
        self.seen_paths = set()
        self.common_responses = {}
        self.failed_paths = set()
        self.throttled_hosts = {}
        self.host_capabilities = {}
    
    def reset(self):
        """Reset optimizer state"""
        self.seen_paths = set()
        self.common_responses = {}
        self.failed_paths = set()
        self.throttled_hosts = {}
        self.host_capabilities = {}
    
    def should_throttle(self, host: str) -> bool:
        """Check if requests to the host should be throttled
        
        Args:
            host: The host to check
            
        Returns:
            True if requests should be throttled, False otherwise
        """
        if host not in self.throttled_hosts:
            return False
            
        throttle_info = self.throttled_hosts[host]
        current_time = time.time()
        
        # If enough time has passed since we started throttling, try again
        if current_time - throttle_info['start_time'] > throttle_info['duration']:
            del self.throttled_hosts[host]
            return False
            
        return True
    
    def add_throttle(self, host: str, failure_count: int = 1):
        """Add throttling for a host
        
        Args:
            host: The host to throttle
            failure_count: Number of consecutive failures
            
        Returns:
            None
        """
        current_time = time.time()
        
        # If already throttled, increase duration
        if host in self.throttled_hosts:
            throttle_info = self.throttled_hosts[host]
            throttle_info['count'] += failure_count
            
            # Increase throttle duration exponentially based on consecutive failures
            throttle_info['duration'] = min(120, 5 * (2 ** min(5, throttle_info['count'])))
            throttle_info['start_time'] = current_time
        else:
            # Start with a small throttle
            self.throttled_hosts[host] = {
                'count': failure_count,
                'duration': 5,  # 5 seconds initially
                'start_time': current_time
            }
    
    def optimize_paths(self, paths: List[str]) -> List[str]:
        """Optimize the order of paths for scanning
        
        Args:
            paths: List of paths to optimize
            
        Returns:
            Optimized list of paths
        """
        # Skip paths that have consistently failed
        filtered_paths = [p for p in paths if p not in self.failed_paths]
        
        # Group paths by structure
        path_categories = {}
        
        # Define path categories based on patterns
        patterns = {
            'admin': re.compile(r'admin|administrator|adm|manage|manager|mgr', re.I),
            'login': re.compile(r'login|signin|sign-in|auth|authentication', re.I),
            'dashboard': re.compile(r'dashboard|panel|control|console', re.I),
            'api': re.compile(r'api|rest|graphql|endpoint', re.I),
            'user': re.compile(r'user|account|profile|member', re.I),
            'backup': re.compile(r'backup|bak|old|temp|tmp|copy', re.I),
            'generic': re.compile(r'.*')
        }
        
        # Categorize paths
        for path in filtered_paths:
            categorized = False
            for category, pattern in patterns.items():
                if pattern.search(path):
                    if category not in path_categories:
                        path_categories[category] = []
                    path_categories[category].append(path)
                    categorized = True
                    break
            
            if not categorized:
                if 'other' not in path_categories:
                    path_categories['other'] = []
                path_categories['other'].append(path)
        
        # Order of categories (priority)
        category_order = ['admin', 'login', 'dashboard', 'user', 'api', 'backup', 'generic', 'other']
        
        # Build the optimized paths list
        optimized_paths = []
        for category in category_order:
            if category in path_categories:
                optimized_paths.extend(path_categories[category])
        
        # If paths were filtered out, add a small subset of them at the end
        if len(filtered_paths) < len(paths):
            sample_size = min(50, len(paths) - len(filtered_paths))
            remainder = list(self.failed_paths)[:sample_size]
            optimized_paths.extend(remainder)
        
        return optimized_paths
    
    def should_skip_path(self, path: str) -> bool:
        """Check if a path should be skipped
        
        Args:
            path: Path to check
            
        Returns:
            True if path should be skipped, False otherwise
        """
        # Skip if already seen this exact path
        if path in self.seen_paths:
            return True
        
        # Skip if path has consistently failed
        if path in self.failed_paths:
            return True
        
        return False
    
    def record_path_result(self, path: str, status_code: int, success: bool = True):
        """Record the result for a path
        
        Args:
            path: The path that was scanned
            status_code: The HTTP status code received
            success: Whether the request was successful
            
        Returns:
            None
        """
        # Add to seen paths
        self.seen_paths.add(path)
        
        # If the request failed, record it
        if not success and path not in self.failed_paths:
            self.failed_paths.add(path)
        
        # Record common response code
        if status_code not in self.common_responses:
            self.common_responses[status_code] = 0
        self.common_responses[status_code] += 1
    
    def record_host_capabilities(self, host: str, supports_keep_alive: bool, 
                                supports_http2: bool, avg_response_time: float):
        """Record capabilities of a host
        
        Args:
            host: The host
            supports_keep_alive: Whether the host supports keep-alive
            supports_http2: Whether the host supports HTTP/2
            avg_response_time: Average response time
            
        Returns:
            None
        """
        self.host_capabilities[host] = {
            'supports_keep_alive': supports_keep_alive,
            'supports_http2': supports_http2,
            'avg_response_time': avg_response_time
        }
    
    def get_optimal_batch_size(self, host: str) -> int:
        """Get the optimal batch size for a host
        
        Args:
            host: The host
            
        Returns:
            Optimal batch size
        """
        if host in self.throttled_hosts:
            # If host is throttled, use a smaller batch size
            return 5
        
        if host in self.host_capabilities:
            capabilities = self.host_capabilities[host]
            
            # If the host supports keep-alive and has good response time
            if capabilities['supports_keep_alive'] and capabilities['avg_response_time'] < 0.5:
                # If also supports HTTP/2, can use a larger batch size
                if capabilities['supports_http2']:
                    return self.config.MAX_CONCURRENT_REQUESTS
                else:
                    return min(30, self.config.MAX_CONCURRENT_REQUESTS)
            
            # If response time is slow, use a smaller batch size
            if capabilities['avg_response_time'] > 1.0:
                return 10
        
        # Default to a moderate batch size
        return min(20, self.config.MAX_CONCURRENT_REQUESTS)


class ResponseAnalyzer:
    """Analyzes HTTP responses to identify admin panels"""
    
    def __init__(self, config):
        self.config = config
        # Compile regular expressions
        self.login_form_re = re.compile(r'<form[^>]*>.*?(?:<input[^>]*password[^>]*>|<input[^>]*username[^>]*>).*?</form>', re.DOTALL | re.IGNORECASE)
        self.admin_indicators_re = re.compile(r'admin|administrator|login|dashboard|control\s*panel|manage|console', re.IGNORECASE)
        self.sensitive_terms_re = re.compile(r'password|username|user|token|auth|key|credential', re.IGNORECASE)
    
    def analyze_response(self, url: str, status_code: int, html_content: str, 
                         response_headers: Dict[str, str], response_time: float) -> Dict:
        """Analyze an HTTP response to determine if it's an admin panel
        
        Args:
            url: The URL that was requested
            status_code: HTTP status code
            html_content: HTML content of the response
            response_headers: Response headers
            response_time: Time taken for the response
            
        Returns:
            Dictionary with analysis results
        """
        result = {
            "url": url,
            "status_code": status_code,
            "title": "",
            "confidence": 0.0,
            "found": False,
            "has_login_form": False,
            "technologies": [],
            "headers": response_headers,
            "server": response_headers.get("Server", "Unknown"),
            "forms": [],
            "inputs": [],
            "content_length": len(html_content) if html_content else 0,
            "response_time": response_time
        }
        
        # Skip further analysis for error codes
        if status_code >= 400 and status_code != 401 and status_code != 403:
            return result
        
        try:
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                result["title"] = title_tag.text.strip()
            
            # Check for login forms
            login_forms = self.login_form_re.findall(html_content)
            result["has_login_form"] = len(login_forms) > 0
            
            # Find all forms
            forms = soup.find_all('form')
            result["forms"] = [self._extract_form_info(form) for form in forms]
            
            # Find all input fields
            inputs = soup.find_all('input')
            result["inputs"] = [self._extract_input_info(input_field) for input_field in inputs]
            
            # Detect technologies
            result["technologies"] = self._detect_technologies(soup, html_content, response_headers)
            
            # Calculate confidence score
            result["confidence"] = self._calculate_confidence(result, soup, html_content)
            
            # Determine if this is likely an admin panel
            result["found"] = result["confidence"] >= 0.5
            
            return result
            
        except Exception as e:
            adv_logger.log_error(f"Error analyzing response for {url}: {str(e)}")
            return result
    
    def _extract_form_info(self, form_tag) -> Dict:
        """Extract information about a form
        
        Args:
            form_tag: BeautifulSoup form tag
            
        Returns:
            Dictionary with form information
        """
        try:
            action = form_tag.get('action', '')
            method = form_tag.get('method', 'get').upper()
            
            inputs = form_tag.find_all('input')
            input_fields = []
            
            for input_tag in inputs:
                input_type = input_tag.get('type', 'text')
                input_name = input_tag.get('name', '')
                input_id = input_tag.get('id', '')
                
                input_fields.append({
                    'type': input_type,
                    'name': input_name,
                    'id': input_id
                })
            
            return {
                'action': action,
                'method': method,
                'inputs': input_fields
            }
        except Exception:
            return {'action': '', 'method': 'GET', 'inputs': []}
    
    def _extract_input_info(self, input_tag) -> Dict:
        """Extract information about an input field
        
        Args:
            input_tag: BeautifulSoup input tag
            
        Returns:
            Dictionary with input information
        """
        try:
            input_type = input_tag.get('type', 'text')
            input_name = input_tag.get('name', '')
            input_id = input_tag.get('id', '')
            
            return {
                'type': input_type,
                'name': input_name,
                'id': input_id
            }
        except Exception:
            return {'type': 'text', 'name': '', 'id': ''}
    
    def _detect_technologies(self, soup, html_content: str, headers: Dict[str, str]) -> List[str]:
        """Detect technologies used in the web page
        
        Args:
            soup: BeautifulSoup object
            html_content: HTML content
            headers: Response headers
            
        Returns:
            List of detected technologies
        """
        technologies = []
        
        # Check headers for server info
        if 'Server' in headers:
            server = headers['Server']
            if 'nginx' in server.lower():
                technologies.append('Nginx')
            elif 'apache' in server.lower():
                technologies.append('Apache')
            elif 'microsoft-iis' in server.lower():
                technologies.append('IIS')
            elif 'cloudflare' in server.lower():
                technologies.append('Cloudflare')
        
        # Look for common JavaScript frameworks
        # jQuery
        if re.search(r'jquery', html_content, re.I):
            technologies.append('jQuery')
        
        # React
        if re.search(r'react', html_content, re.I) or soup.find('div', {'id': 'root'}):
            technologies.append('React')
        
        # Angular
        if re.search(r'angular', html_content, re.I) or soup.find('ng-app'):
            technologies.append('Angular')
        
        # Bootstrap
        if re.search(r'bootstrap', html_content, re.I) or soup.find('link', {'href': re.compile(r'bootstrap')}):
            technologies.append('Bootstrap')
        
        # Check for common CMS
        # WordPress
        if re.search(r'wp-content|wordpress', html_content, re.I) or soup.find('meta', {'name': 'generator', 'content': re.compile(r'WordPress')}):
            technologies.append('WordPress')
        
        # Joomla
        if re.search(r'joomla', html_content, re.I) or soup.find('meta', {'name': 'generator', 'content': re.compile(r'Joomla')}):
            technologies.append('Joomla')
        
        # Drupal
        if re.search(r'drupal', html_content, re.I) or soup.find('meta', {'name': 'generator', 'content': re.compile(r'Drupal')}):
            technologies.append('Drupal')
        
        # Check for common backends
        # PHP
        if 'X-Powered-By' in headers and 'php' in headers['X-Powered-By'].lower():
            technologies.append('PHP')
        
        # ASP.NET
        if 'X-AspNet-Version' in headers or 'X-Powered-By' in headers and 'asp.net' in headers['X-Powered-By'].lower():
            technologies.append('ASP.NET')
        
        return list(set(technologies))  # Remove duplicates
    
    def _calculate_confidence(self, result: Dict, soup, html_content: str) -> float:
        """Calculate confidence score for an admin panel
        
        Args:
            result: Result dictionary
            soup: BeautifulSoup object
            html_content: HTML content
            
        Returns:
            Confidence score between 0 and 1
        """
        confidence = 0.0
        
        # Check if URL contains admin indicators
        if self.admin_indicators_re.search(result["url"]):
            confidence += 0.2
        
        # Check for login forms
        if result["has_login_form"]:
            confidence += 0.3
        
        # Check if title contains admin indicators
        if self.admin_indicators_re.search(result["title"]):
            confidence += 0.2
        
        # Check for authentication required
        if result["status_code"] in [401, 403]:
            confidence += 0.15
        
        # Check for common admin technologies
        admin_tech = ["WordPress Admin", "Joomla", "Drupal", "phpMyAdmin", "cPanel", "WebMin", "AdminLTE"]
        for tech in result["technologies"]:
            if tech in admin_tech:
                confidence += 0.1
                break
        
        # Check HTML content for admin keywords
        if self.admin_indicators_re.search(html_content):
            confidence += 0.1
        
        # Check for sensitive terms in the HTML
        if self.sensitive_terms_re.search(html_content):
            confidence += 0.05
        
        # Bonus for login pages with simple URLs
        url_path = urlparse(result["url"]).path.strip('/')
        if (result["has_login_form"] and len(url_path.split('/')) <= 2 and 
            ('login' in url_path.lower() or 'admin' in url_path.lower())):
            confidence += 0.1
        
        # Cap confidence at 1.0
        return min(1.0, confidence)


async def create_optimized_session(config, optimizer: ScanOptimizer) -> ClientSession:
    """Create an optimized aiohttp session
    
    Args:
        config: Configuration object
        optimizer: Scan optimizer instance
        
    Returns:
        Optimized aiohttp ClientSession
    """
    # Create a custom SSL context that's less strict for compatibility
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    # Configure timeout based on config
    timeout = ClientTimeout(total=config.TIMEOUT, connect=config.TIMEOUT/2)
    
    # Create a connector with optimal settings
    connector = TCPConnector(
        ssl=ssl_context,
        limit=config.MAX_CONCURRENT_REQUESTS,
        ttl_dns_cache=300,  # Cache DNS results for 5 minutes
        force_close=False,  # Enable connection pooling
        enable_cleanup_closed=True,
        verify_ssl=False
    )
    
    # Create session with optimized headers
    session = ClientSession(
        connector=connector,
        timeout=timeout,
        trust_env=True,
        auto_decompress=True
    )
    
    return session


async def scan_paths_concurrently(
    target_url: str, 
    paths: List[str], 
    session: ClientSession, 
    config, 
    optimizer: ScanOptimizer, 
    analyzer: ResponseAnalyzer,
    progress_callback=None
) -> List[Dict]:
    """Scan multiple paths concurrently with optimized batches
    
    Args:
        target_url: Target URL
        paths: List of paths to scan
        session: aiohttp ClientSession
        config: Configuration object
        optimizer: Scan optimizer instance
        analyzer: Response analyzer instance
        progress_callback: Optional callback for progress updates
        
    Returns:
        List of scan results
    """
    # Extract host for throttling checks
    host = urlparse(target_url).netloc
    
    # Optimize path order
    optimized_paths = optimizer.optimize_paths(paths)
    
    # Get optimal batch size
    batch_size = optimizer.get_optimal_batch_size(host)
    
    results = []
    total_paths = len(optimized_paths)
    completed = 0
    
    # Process paths in batches
    for i in range(0, total_paths, batch_size):
        # Check if host should be throttled
        if optimizer.should_throttle(host):
            # Sleep for a while before trying again
            await asyncio.sleep(5)
        
        # Get current batch
        batch_paths = optimized_paths[i:i+batch_size]
        batch_paths = [p for p in batch_paths if not optimizer.should_skip_path(p)]
        
        if not batch_paths:
            completed += len(optimized_paths[i:i+batch_size])
            if progress_callback:
                progress_callback(completed, total_paths)
            continue
        
        # Prepare tasks for this batch
        tasks = []
        for path in batch_paths:
            url = urljoin(target_url, path)
            tasks.append(_scan_single_path(url, path, session, config, optimizer, analyzer))
        
        # Execute batch
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in batch_results:
            if isinstance(result, Exception):
                # Handle exceptions
                adv_logger.log_error(f"Error during scan: {str(result)}")
                continue
            
            if result:
                results.append(result)
        
        # Update progress
        completed += len(batch_paths)
        if progress_callback:
            progress_callback(completed, total_paths)
        
        # Add a small delay to avoid overwhelming the server
        await asyncio.sleep(0.2)
    
    return results


async def _scan_single_path(url: str, path: str, session: ClientSession, config, 
                           optimizer: ScanOptimizer, analyzer: ResponseAnalyzer) -> Optional[Dict]:
    """Scan a single path
    
    Args:
        url: Complete URL to scan
        path: Path component only
        session: aiohttp ClientSession
        config: Configuration object
        optimizer: Scan optimizer instance
        analyzer: Response analyzer instance
        
    Returns:
        Scan result or None if error
    """
    host = urlparse(url).netloc
    
    # Get random user agent
    headers = {"User-Agent": random.choice(config.USER_AGENTS)}
    
    start_time = time.time()
    try:
        async with session.get(url, headers=headers, allow_redirects=True, timeout=config.TIMEOUT) as response:
            response_time = time.time() - start_time
            
            # Get response content and headers
            html_content = await response.text(errors='ignore')
            response_headers = dict(response.headers)
            
            # Record path result
            optimizer.record_path_result(path, response.status, True)
            
            # Record host capabilities
            supports_keep_alive = 'Connection' in response_headers and 'keep-alive' in response_headers['Connection'].lower()
            supports_http2 = response.version >= (2, 0)
            optimizer.record_host_capabilities(host, supports_keep_alive, supports_http2, response_time)
            
            # Analyze response
            result = analyzer.analyze_response(url, response.status, html_content, 
                                            response_headers, response_time)
            
            return result
            
    except (ClientConnectionError, ClientPayloadError, ClientResponseError,
            ServerDisconnectedError, TooManyRedirects, ServerTimeoutError) as e:
        # Record failure to optimize future scans
        optimizer.record_path_result(path, 0, False)
        
        # Apply throttling after connection errors
        optimizer.add_throttle(host)
        
        adv_logger.log_error(f"Connection error for {url}: {str(e)}")
        return None
    except asyncio.TimeoutError:
        # Record failure to optimize future scans
        optimizer.record_path_result(path, 0, False)
        
        # Apply throttling after timeouts
        optimizer.add_throttle(host)
        
        adv_logger.log_error(f"Timeout for {url}")
        return None
    except Exception as e:
        # Record failure to optimize future scans
        optimizer.record_path_result(path, 0, False)
        
        adv_logger.log_error(f"Error scanning {url}: {str(e)}")
        return None 