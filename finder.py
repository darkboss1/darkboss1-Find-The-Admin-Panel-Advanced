! /bin/bash
first_print(){
clear
echo `tput setaf 111`"

    ____     ___     ____     __ __    ____    ____    _____   _____   ___
   / __ \   /   |   / __ \   / //_/   / __ )  / __ \  / ___/  / ___/  <  /
  / / / /  / /| |  / /_/ /  / ,<     / __  | / / / /  \__ \   \__ \   / / 
 / /_/ /  / ___ | / _, _/  / /| |   / /_/ / / /_/ /  ___/ /  ___/ /  / /  
/_____/  /_/  |_|/_/ |_|  /_/ |_|  /_____/  \____/  /____/  /____/  /_/   
                                                                          

          ________________________________________________________________________
         |                                                                        |
         |     	             WebSite: serialkey.top                           |
         |	                Creator: darkboss1		          |
         |	                E-mail: chowdhuryethicalhacker@gmail.com		    |
         |							     	          | 
         --------------------------------------------------------------------------
"
}
first_print
import os
import sys
import asyncio
import argparse
from datetime import datetime

# Add the current directory to the path to ensure modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules
from scripts.config import Config
from scripts.ui import TerminalDisplay
from scripts.scanner import Scanner
from scripts.exporter import ResultExporter
from scripts.menu import start_menu
from scripts.utils import setup_signal_handler, validate_url, count_lines_in_file
from scripts.logging import get_logger

# Initialize advanced logger
adv_logger = get_logger('logs')


async def scan_target(config, target_url, wordlist_path=None, export_format=None, interactive=False):
    """Perform a scan on a target URL
    
    Args:
        config: Configuration object
        target_url: Target URL to scan
        wordlist_path: Path to wordlist file (default: None, uses config.DEFAULT_WORDLIST)
        export_format: Format to export results (default: None, uses config.EXPORT_FORMATS)
        interactive: Whether to run in interactive mode (default: False)
        
    Returns:
        Tuple of (results, scan_info)
    """
    display = TerminalDisplay()
    
    if not wordlist_path:
        # Use absolute path for default wordlist
        base_dir = os.path.dirname(os.path.abspath(__file__))
        wordlist_path = os.path.join(base_dir, config.DEFAULT_WORDLIST)
    
    # Validate target URL
    is_valid, target_url = validate_url(target_url)
    if not is_valid:
        adv_logger.log_error(f"Invalid URL format: {target_url}")
        if interactive:
            display.show_error(f"Invalid URL format: {target_url}")
            return [], {}
        else:
            print(f"Error: Invalid URL format: {target_url}")
            sys.exit(1)
    
    # Check if wordlist exists
    if not os.path.exists(wordlist_path):
        adv_logger.log_error(f"Wordlist file not found: {wordlist_path}")
        if interactive:
            display.show_error(f"Wordlist file not found: {wordlist_path}")
            return [], {}
        else:
            print(f"Error: Wordlist file not found: {wordlist_path}")
            sys.exit(1)
    
    # Create scanner
    scanner = await Scanner.create(config)
    
    # Set up signal handler for Ctrl+C
    setup_signal_handler(scanner)
    
    try:
        # Load wordlist
        with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
            paths = [line.strip() for line in f if line.strip()]
        
        # Log scan start
        scan_mode = "custom" if wordlist_path != os.path.join(base_dir, config.DEFAULT_WORDLIST) else "default"
        adv_logger.log_scan_start(target_url, scan_mode, len(paths))
        
        if interactive:
            display.clear_screen()
            display.show_banner(config)
            display.show_target_info(target_url, scan_mode, wordlist_path)
        else:
            print(f"Starting scan on {target_url}")
            print(f"Using wordlist: {wordlist_path} ({len(paths)} paths)")
        
        # Start scan
        start_time = datetime.now()
        results = await scanner.scan(target_url, paths)
        scan_time = (datetime.now() - start_time).total_seconds()
        
        # Prepare scan info
        scan_info = scanner.get_scan_info()
        scan_info["scan_time"] = scan_time
        scan_info["target_url"] = target_url
        scan_info["scan_mode"] = scan_mode
        scan_info["total_paths"] = len(paths)
        
        # Log scan completion
        adv_logger.log_scan_complete(
            target_url, 
            len(paths), 
            sum(1 for r in results if r.get("found", False)), 
            scan_time
        )
        
        # Display results
        if interactive:
            display.show_scan_completion(results, scan_time, len(paths))
            display.show_results(results)
            display.show_summary(len(paths), sum(1 for r in results if r.get("found", False)), scan_time)
        else:
            found_count = sum(1 for r in results if r.get("found", False))
            print(f"\nScan completed in {scan_time:.2f} seconds")
            print(f"Checked {len(paths)} paths")
            print(f"Found {found_count} potential admin panels\n")
        
        # Export results if configured
        if config.SAVE_RESULTS:
            exporter = ResultExporter(config)
            if interactive:
                display.show_progress("Exporting results...")
            else:
                print("Exporting results...")
                
            export_status = exporter.export_results(results, scan_info, export_format)
            
            if interactive:
                display.show_success("Results exported successfully")
        
        return results, scan_info
        
    except Exception as e:
        adv_logger.log_error(f"Error during scan: {str(e)}")
        if interactive:
            display.show_error(f"Error during scan: {str(e)}")
        else:
            print(f"Error: {str(e)}")
        return [], {}
    finally:
        # Close scanner
        await scanner.close()


async def main():
    """Main entry point for the application"""
    try:
        # Load configuration
        config = Config()
        
        # Parse command-line arguments
        parser = argparse.ArgumentParser(description="Find The Admin Panel - A tool for identifying admin panels")
        parser.add_argument("-u", "--url", help="Target URL to scan")
        parser.add_argument("-w", "--wordlist", help="Path to wordlist file")
        parser.add_argument("-e", "--export", help="Export format (json, html, csv, txt)")
        parser.add_argument("-i", "--interactive", action="store_true", help="Run in interactive mode")
        parser.add_argument("-v", "--version", action="store_true", help="Show version and exit")
        
        args = parser.parse_args()
        
        # Show version and exit
        if args.version:
            print(f"Find The Admin Panel v{config.VERSION}")
            print(f"Developed by: {config.DEVELOPER}")
            print(f"GitHub: {config.GITHUB}")
            return
        
        # Interactive mode
        if args.interactive or not args.url:
            # Start menu system
            await start_menu(config)
        else:
            # Non-interactive mode
            await scan_target(config, args.url, args.wordlist, args.export, False)
            
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
        adv_logger.log_warning("Scan interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"Error: {str(e)}")
        adv_logger.log_error(f"Unhandled error: {str(e)}")


if __name__ == "__main__":
    # Run the main async function
    asyncio.run(main())
