"""
Menu module for Find The Admin Panel

This module handles the interactive menu system for the application,
allowing users to navigate through various options and perform actions.
"""

import os
import sys
import re
import time
import asyncio
import json
from typing import List, Dict, Any, Optional, Union, Callable

# Import advanced logging and display tools
from scripts.logging import get_logger
from scripts.ui import TerminalDisplay
from scripts.config import Config
from scripts.scanner import Scanner
from scripts.exporter import ResultExporter
from rich.panel import Panel
from rich.table import Table
from rich import box

# Initialize advanced logger and display
adv_logger = get_logger('logs')
display = TerminalDisplay()

class Menu:
    """Main menu system for the application"""
    
    def __init__(self, config: Config):
        self.config = config
        self.scanner = None
        self.exporter = ResultExporter(config)
        self.running = True
        self.current_menu = "main"
        self.last_scan_results = []
        self.last_scan_info = {}
        # Get base directory for absolute paths
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
    async def start(self):
        """Start the menu system"""
        try:
            adv_logger.log_info("Starting menu system")
            
            # Display welcome banner
            display.clear_screen()
            display.show_banner(self.config)
            
            # Initialize scanner
            self.scanner = await Scanner.create(self.config)
            
            # Main menu loop
            while self.running:
                if self.current_menu == "main":
                    await self._show_main_menu()
                elif self.current_menu == "scan":
                    await self._show_scan_menu()
                elif self.current_menu == "results":
                    await self._show_results_menu()
                elif self.current_menu == "settings":
                    await self._show_settings_menu()
                elif self.current_menu == "help":
                    await self._show_help_menu()
                elif self.current_menu == "exit":
                    self._exit_program()
                    break
                else:
                    self.current_menu = "main"
                    
        except KeyboardInterrupt:
            adv_logger.log_info("Menu system stopped by user (Ctrl+C)")
        except Exception as e:
            adv_logger.log_error(f"Error in menu system: {str(e)}")
        finally:
            if self.scanner:
                await self.scanner.close()
    
    async def _show_main_menu(self):
        """Display main menu and handle user input"""
        display.clear_screen()
        display.show_banner(self.config)
        
        # Use Rich panel with cyan border instead of blue
        display.console.print(Panel(
            "Select an option to proceed",
            title="[bold]MAIN MENU[/bold]",
            border_style="cyan",
            title_align="center"
        ))
        
        # Use Rich formatting for menu options with cyan styling
        options = [
            ("[bold cyan][[bold white]1[/bold white]][/bold cyan] [bold cyan]Start Scan[/bold cyan]", "Find admin panels on a website"),
            ("[bold cyan][[bold white]2[/bold white]][/bold cyan] [bold cyan]View Results[/bold cyan]", "Browse previous scan results"),
            ("[bold cyan][[bold white]3[/bold white]][/bold cyan] [bold cyan]Settings[/bold cyan]", "Configure scan options"),
            ("[bold cyan][[bold white]4[/bold white]][/bold cyan] [bold cyan]Help[/bold cyan]", "Show help information"),
            ("[bold cyan][[bold white]0[/bold white]][/bold cyan] [bold cyan]Exit[/bold cyan]", "Close the application")
        ]
        
        # Create a table for better-looking options
        options_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        options_table.add_column("Option", style="bold cyan")
        options_table.add_column("Description", style="dim")
        
        for option, description in options:
            options_table.add_row(option, description)
        
        display.console.print(options_table)
        
        choice = display.get_input("\nEnter your choice: ")
        
        if choice == "1":
            self.current_menu = "scan"
        elif choice == "2":
            self.current_menu = "results"
        elif choice == "3":
            self.current_menu = "settings"
        elif choice == "4":
            self.current_menu = "help"
        elif choice == "0":
            self.current_menu = "exit"
    
    async def _show_scan_menu(self):
        """Show the scan menu with enhanced options"""
        display.clear_screen()
        display.show_banner(self.config)
        
        # Use Rich panel instead of text separators
        display.console.print(Panel(
            "Configure and run scans for admin panels",
            title="[bold]SCAN MENU[/bold]",
            border_style="cyan",
            title_align="center"
        ))
        
        # Use Rich formatting for menu options
        options = [
            ("[bold cyan][[bold white]1[/bold white]][/bold cyan] [bold cyan]Start New Scan[/bold cyan]", "Begin scanning a new target"),
            ("[bold cyan][[bold white]2[/bold white]][/bold cyan] [bold cyan]Configure Scan Options[/bold cyan]", "Set scan parameters"),
            ("[bold cyan][[bold white]3[/bold white]][/bold cyan] [bold cyan]View Results[/bold cyan]", "Browse scan results"),
            ("[bold cyan][[bold white]4[/bold white]][/bold cyan] [bold cyan]Import Target List[/bold cyan]", "Scan multiple targets"),
            ("[bold cyan][[bold white]5[/bold white]][/bold cyan] [bold cyan]Return to Main Menu[/bold cyan]", "Go back to main menu"),
            ("[bold cyan][[bold white]0[/bold white]][/bold cyan] [bold cyan]Exit[/bold cyan]", "Close the application")
        ]
        
        # Create a table for better-looking options
        options_table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        options_table.add_column("Option", style="bold cyan")
        options_table.add_column("Description", style="dim")
        
        for option, description in options:
            options_table.add_row(option, description)
        
        display.console.print(options_table)
        
        option = display.get_input("Select an option: ")
        
        if option == "1":
            # Start new scan
            display.clear_screen()
            display.show_banner(self.config)
            
            # Use Rich panel for the scan title
            display.console.print(Panel(
                "Configure target and scan parameters",
                title="[bold]NEW SCAN[/bold]",
                border_style="cyan",
                title_align="center"
            ))
            
            target_url = display.get_input("Enter target URL (e.g., https://example.com): ")
            if not target_url:
                display.show_error("Target URL cannot be empty")
                display.get_input("Press Enter to continue...")
                await self._show_scan_menu()
                return
            
            # Validate URL
            is_valid, target_url = self._validate_url(target_url)
            if not is_valid:
                display.show_error(f"Invalid URL format: {target_url}")
                display.get_input("Press Enter to continue...")
                await self._show_scan_menu()
                return
            
            # Scan configuration
            display.console.print("\n[bold]Scan Configuration:[/bold]")
            
            # Choose scan mode with clear descriptions in a nice table
            scan_modes_table = Table(show_header=False, box=box.SIMPLE, title="[bold]Scan Modes[/bold]", title_style="bold cyan", border_style="cyan")
            scan_modes_table.add_column("Mode", style="bold cyan", width=12)
            scan_modes_table.add_column("Description", style="white")
            
            scan_modes_table.add_row("[bold green]quick[/bold green]", "Fast scan with common paths")
            scan_modes_table.add_row("[bold yellow]stealth[/bold yellow]", "Slower scan with delays to avoid detection")
            scan_modes_table.add_row("[bold red]aggressive[/bold red]", "Comprehensive scan with all available techniques")
            
            display.console.print(scan_modes_table)
            
            scan_mode = display.get_input("\nSelect scan mode [quick/stealth/aggressive] (default: quick): ").lower()
            if not scan_mode or scan_mode.strip() == "":
                scan_mode = "quick"
                display.show_warning(f"Using default mode: {scan_mode}")
            elif scan_mode not in ["quick", "stealth", "aggressive"]:
                display.show_warning(f"Invalid mode '{scan_mode}', using default mode: quick")
                scan_mode = "quick"
            
            # Choose wordlist with absolute path handling
            default_wordlist = os.path.join(self.base_dir, self.config.DEFAULT_WORDLIST)
            
            print(f"\nDefault wordlist: {default_wordlist}")
            use_custom = display.get_input("Use custom wordlist? [y/N]: ").lower() == "y"
            
            wordlist_path = default_wordlist
            if use_custom:
                wordlist_path = display.get_input("Enter path to wordlist file: ")
                if not os.path.exists(wordlist_path):
                    display.show_error(f"Wordlist file not found: {wordlist_path}")
                    wordlist_path = default_wordlist
                    display.show_warning(f"Using default wordlist: {wordlist_path}")
            
            # Confirmation
            scan_details = f"""[bold white]Target URL:[/bold white] [cyan]{target_url}[/cyan]
[bold white]Scan Mode:[/bold white] [cyan]{scan_mode}[/cyan]
[bold white]Wordlist:[/bold white] [cyan]{os.path.basename(wordlist_path)}[/cyan]"""
            
            display.console.print(Panel(
                scan_details,
                title="[bold]Scan Details[/bold]",
                border_style="cyan",
                box=box.ROUNDED
            ))
            
            # Now we explicitly call scan_target with a single mode, not performing additional scans
            confirm = display.get_input("\nStart scan? [Y/n]  (default: Y): ").lower() != "n"
            if confirm:
                display.show_progress(f"Starting {scan_mode} scan for {target_url}")
                
                # Execute the scan with the selected options (we only use exactly what was selected)
                try:
                    # Reading paths from the wordlist file
                    paths = []
                    if wordlist_path.endswith('.json'):
                        # If the file is in JSON format
                        try:
                            with open(wordlist_path, 'r', encoding='utf-8') as f:
                                paths_data = json.load(f)
                                if isinstance(paths_data, dict) and 'paths' in paths_data:
                                    paths = paths_data['paths']
                                elif isinstance(paths_data, list):
                                    paths = paths_data
                                else:
                                    display.show_error(f"Invalid JSON format in wordlist: {wordlist_path}")
                                    paths = []
                        except Exception as e:
                            display.show_error(f"Error reading JSON file: {str(e)}")
                            paths = []
                    else:
                        # If the file is a plain text file
                        try:
                            with open(wordlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                                paths = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                        except Exception as e:
                            display.show_error(f"Error reading wordlist file: {str(e)}")
                            paths = []
                    
                    if not paths:
                        display.show_error("No paths found for scanning in the specified file.")
                        display.get_input("Press Enter to continue...")
                        return

                    # Set scan mode in configuration
                    self.config.DETECTION_MODE = scan_mode
                    
                    # Call scan function with the paths read
                    total_paths = len(paths)
                    display.show_progress(f"Scanning {total_paths} paths for {target_url}")
                    
                    # Call the scan function with correct parameter order
                    try:
                        # Call scan function
                        results = await self.scanner.scan(target_url, paths, self.config.MAX_CONCURRENT_TASKS)
                        
                        if not results and not isinstance(results, list):
                            display.show_warning("No results obtained from scan operation")
                            display.get_input("\nPress Enter to return to main menu...")
                            return
                        
                        # Get scan information
                        scan_info = self.scanner.get_scan_info()
                        if not scan_info:
                            scan_info = {
                                "duration": 0,
                                "url": target_url,
                                "mode": scan_mode,
                                "paths_count": total_paths,
                                "found_count": 0
                            }
                        
                        # Store results for later display
                        self.last_scan_results = results
                        self.last_scan_info = scan_info
                        
                        # Display results
                        scan_time = scan_info.get("duration", 0)
                        found_count = sum(1 for r in results if r.get("found", False))
                        
                        display.show_scan_completion(results, scan_time, total_paths)
                        display.show_results(results)
                        display.show_summary(total_paths, found_count, scan_time)
                        
                        # Export results if configured
                        if self.config.SAVE_RESULTS and results:
                            display.show_progress("Exporting results...")
                            export_status = self.exporter.export_results(results, scan_info)
                            display.show_success("Results exported successfully")
                    except Exception as e:
                        adv_logger.log_error(f"Error during scan: {str(e)}", exc_info=True)
                        display.show_error(f"Error during scan: {str(e)}")
                        display.show_warning("Please check your internet connection and verify the URL")
                    
                    display.get_input("\nPress Enter to return to main menu...")
                except Exception as e:
                    display.show_error(f"Error during scan: {str(e)}")
                    display.get_input("Press Enter to continue...")
            
            await self._show_scan_menu()
        elif option == "2":
            # Configure options
            await self._configure_scan_options()
            await self._show_scan_menu()
        elif option == "3":
            # View results
            await self._show_results_menu()
            await self._show_scan_menu()
        elif option == "4":
            # Import target list
            await self._import_target_list()
            await self._show_scan_menu()
        elif option == "5":
            # Return to main menu
            await self._show_main_menu()
        elif option == "0":
            # Exit
            self._exit_program()
        else:
            display.show_error("Invalid option")
            display.get_input("Press Enter to continue...")
            await self._show_scan_menu()
    
    async def _show_results_menu(self):
        """Display results menu and handle user input"""
        display.clear_screen()
        display.show_banner(self.config)
        
        result_files = self.exporter.list_result_files()
        
        if not result_files:
            display.show_warning("No result files found")
            display.get_input("Press Enter to return to the main menu...")
            self.current_menu = "main"
            return
        
        display.show_results_list(result_files)
        
        choice = display.get_input("\nEnter file number to view or 0 to return to main menu: ")
        
        if choice == "0":
            self.current_menu = "main"
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(result_files):
                    filename = result_files[idx]
                    
                    # Determine how to display the file based on extension
                    if filename.endswith(".html"):
                        display.show_success(f"Opening {filename} in web browser...")
                        # Open HTML file in default browser
                        try:
                            filepath = os.path.join(self.config.RESULTS_DIR, filename)
                            filepath = os.path.abspath(filepath)
                            
                            if sys.platform == 'win32':
                                os.startfile(filepath)
                            elif sys.platform == 'darwin':  # macOS
                                os.system(f'open "{filepath}"')
                            else:  # linux variants
                                os.system(f'xdg-open "{filepath}"')
                        except Exception as e:
                            display.show_error(f"Failed to open file in browser: {str(e)}")
                    else:
                        # Read and display the file content
                        content = self.exporter.view_result_file(filename)
                        display.clear_screen()
                        display.show_banner(self.config)
                        print(f"\n=== {filename} ===\n")
                        print(content)
                
                display.get_input("\nPress Enter to return to the results menu...")
            except (ValueError, IndexError):
                display.show_error("Invalid selection")
                display.get_input("Press Enter to continue...")
    
    async def _show_settings_menu(self):
        """Display settings menu and handle user input"""
        display.clear_screen()
        display.show_banner(self.config)
        
        print("\n[1] Enable/Disable Result Saving")
        print("[2] Change Export Formats")
        print("[3] Change Request Timeout")
        print("[4] Change Maximum Concurrent Requests")
        print("[0] Back to Main Menu")
        
        choice = display.get_input("\nEnter your choice: ")
        
        if choice == "1":
            self.config.SAVE_RESULTS = not self.config.SAVE_RESULTS
            if self.config.SAVE_RESULTS:
                display.show_success("Result saving enabled")
            else:
                display.show_warning("Result saving disabled")
            self.config.save_config()
            display.get_input("Press Enter to continue...")
        elif choice == "2":
            display.clear_screen()
            display.show_banner(self.config)
            print("\nCurrent export formats: " + ", ".join(self.config.EXPORT_FORMATS))
            print("\nAvailable formats: json, html, csv, txt")
            
            formats_input = display.get_input("Enter formats (comma separated, e.g., json,html): ")
            formats = [fmt.strip().lower() for fmt in formats_input.split(",")]
            
            # Validate formats
            valid_formats = [fmt for fmt in formats if fmt in self.exporter.supported_formats]
            
            if valid_formats:
                self.config.EXPORT_FORMATS = valid_formats
                self.config.save_config()
                display.show_success(f"Export formats updated: {', '.join(valid_formats)}")
            else:
                display.show_error("No valid formats specified")
            
            display.get_input("Press Enter to continue...")
        elif choice == "3":
            display.clear_screen()
            display.show_banner(self.config)
            print(f"\nCurrent request timeout: {self.config.TIMEOUT} seconds")
            
            timeout_input = display.get_input("Enter new timeout in seconds (5-60): ")
            try:
                timeout = float(timeout_input)
                if 5 <= timeout <= 60:
                    self.config.TIMEOUT = timeout
                    self.config.save_config()
                    display.show_success(f"Request timeout updated to {timeout} seconds")
                else:
                    display.show_error("Timeout must be between 5 and 60 seconds")
            except ValueError:
                display.show_error("Invalid timeout value")
            
            display.get_input("Press Enter to continue...")
        elif choice == "4":
            display.clear_screen()
            display.show_banner(self.config)
            print(f"\nCurrent maximum concurrent requests: {self.config.MAX_CONCURRENT_REQUESTS}")
            
            requests_input = display.get_input("Enter new maximum (10-100): ")
            try:
                max_requests = int(requests_input)
                if 10 <= max_requests <= 100:
                    self.config.MAX_CONCURRENT_REQUESTS = max_requests
                    self.config.save_config()
                    display.show_success(f"Maximum concurrent requests updated to {max_requests}")
                else:
                    display.show_error("Value must be between 10 and 100")
            except ValueError:
                display.show_error("Invalid value")
            
            display.get_input("Press Enter to continue...")
        elif choice == "0":
            self.current_menu = "main"
    
    async def _show_help_menu(self):
        """Display help menu and handle user input"""
        display.clear_screen()
        display.show_banner(self.config)
        
        display.show_help()
        
        display.get_input("\nPress Enter to return to the main menu...")
        self.current_menu = "main"
    
    def _exit_program(self):
        """Exit the program"""
        self.running = False
        adv_logger.log_info("Exiting Admin Panel Finder")
        display.clear_screen()
        display.show_banner(self.config)
        print("\nThank you for using Admin Panel Finder!")
        print(f"GitHub: {self.config.GITHUB}")
        print("\nExiting...\n")
    
    def _validate_url(self, url):
        """Validate the URL format"""
        if not re.match(r'^https?://[a-zA-Z0-9][-a-zA-Z0-9.]*\.[a-zA-Z]{2,}', url):
            return False, url
        return True, url

async def start_menu(config: Config):
    """Initialize and start the menu system
    
    Args:
        config: Application configuration
        
    Returns:
        None
    """
    menu = Menu(config)
    await menu.start()