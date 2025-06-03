"""
Result exporter module for Find The Admin Panel

This module handles the exporting of scan results to various formats
including JSON, HTML, CSV, and TXT. It provides a centralized interface
for saving and viewing scan results.
"""

import os
import json
import csv
import html
from datetime import datetime
from typing import List, Dict

# Import advanced logging tool
from scripts.logging import get_logger

# Initialize advanced logger
adv_logger = get_logger('logs')

class ResultExporter:
    """Exports scan results in various formats"""
    
    def __init__(self, config):
        self.config = config
        self.results_dir = config.RESULTS_DIR
        self.supported_formats = ["json", "html", "csv", "txt"]
        # Ensure default export formats exist
        if not hasattr(config, 'EXPORT_FORMATS') or not config.EXPORT_FORMATS:
            self.config.EXPORT_FORMATS = ["json", "html"]
            adv_logger.log_info("No export formats configured, using defaults: json, html")
    
    def _get_timestamp(self) -> str:
        """Get current timestamp for filenames"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_result_filename(self, base_filename: str = None, format_type: str = "json") -> str:
        """Generate a filename for results"""
        timestamp = self._get_timestamp()
        if base_filename:
            # Clean up any path separators to avoid directory traversal
            safe_basename = os.path.basename(base_filename)
            return f"{self.results_dir}/{safe_basename}_{timestamp}.{format_type}"
        else:
            return f"{self.results_dir}/results_{timestamp}.{format_type}"
    
    def _ensure_result_has_required_fields(self, result: Dict) -> Dict:
        """Ensure result has all required fields to prevent export errors"""
        # Standard fields that should be present in all results
        required_fields = {
            "url": "Unknown",
            "status_code": 0,
            "title": "Unknown",
            "confidence": 0.0,
            "found": False,
            "has_login_form": False,
            "technologies": [],
            "headers": {},
            "server": "Unknown",
            "forms": [],
            "inputs": [],
            "content_length": 0
        }
        
        # Create a copy to avoid modifying the original
        safe_result = result.copy()
        
        # Extract server from headers if present
        if "headers" in safe_result and "Server" in safe_result["headers"]:
            safe_result["server"] = safe_result["headers"]["Server"]
        
        # Add any missing fields
        for field, default_value in required_fields.items():
            if field not in safe_result or safe_result[field] is None:
                safe_result[field] = default_value
                
        return safe_result
    
    def _export_json(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        """Export results to JSON format"""
        try:
            # Ensure all results have required fields
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            # Create full export data with scan info and results
            export_data = {
                "scan_info": scan_info,
                "results": safe_results,
                "total_count": len(safe_results),
                "found_count": sum(1 for r in safe_results if r.get("found", False)),
                "export_time": datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            adv_logger.log_info(f"Exported {len(results)} results to JSON: {filename}")
            return True
        except Exception as e:
            adv_logger.log_error(f"Failed to export to JSON: {str(e)}")
            return False
    
    def _export_html(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        """Export results to HTML format"""
        try:
            # Ensure all results have required fields
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            # Get scan info with safe defaults
            url = scan_info.get("target_url", "Unknown")
            mode = scan_info.get("scan_mode", "Unknown")
            duration = scan_info.get("scan_time", 0)
            total_paths = scan_info.get("total_paths", 0)
            found_count = sum(1 for r in safe_results if r.get("found", False))
            
            # Create HTML content
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Admin Panel Finder Results - {url}</title>
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                    .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                    .header {{ background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                    .summary {{ background-color: #f8f9fa; padding: 15px; margin: 20px 0; border-radius: 5px; border-left: 4px solid #2c3e50; }}
                    h1, h2, h3 {{ margin-top: 0; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
                    th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                    th {{ background-color: #2c3e50; color: white; position: sticky; top: 0; }}
                    tr:hover {{ background-color: #f5f5f5; }}
                    .success {{ color: green; }}
                    .warning {{ color: orange; }}
                    .error {{ color: red; }}
                    .badge {{ display: inline-block; padding: 3px 7px; border-radius: 3px; font-size: 12px; font-weight: bold; margin-right: 5px; }}
                    .badge-blue {{ background-color: #3498db; color: white; }}
                    .badge-green {{ background-color: #2ecc71; color: white; }}
                    .badge-red {{ background-color: #e74c3c; color: white; }}
                    .badge-orange {{ background-color: #f39c12; color: white; }}
                    .tech-list {{ margin: 0; padding: 0; list-style: none; display: flex; flex-wrap: wrap; }}
                    .tech-list li {{ margin-right: 8px; margin-bottom: 5px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Admin Panel Finder Results</h1>
                        <p>Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                    </div>
                    
                    <div class="summary">
                        <h2>Scan Summary</h2>
                        <p><strong>Target URL:</strong> {url}</p>
                        <p><strong>Scan Mode:</strong> {mode}</p>
                        <p><strong>Duration:</strong> {duration:.2f} seconds</p>
                        <p><strong>Found:</strong> {found_count} potential admin panels</p>
                        <p><strong>Total Paths Checked:</strong> {total_paths}</p>
                        <p><strong>Success Rate:</strong> {(found_count/total_paths*100) if total_paths > 0 else 0:.2f}%</p>
                    </div>
                    
                    <h2>Results</h2>
            """
            
            if not safe_results:
                html_content += "<p>No potential admin panels found.</p>"
            else:
                html_content += """
                    <table>
                        <thead>
                            <tr>
                                <th>URL</th>
                                <th>Status</th>
                                <th>Title</th>
                                <th>Confidence</th>
                                <th>Features</th>
                                <th>Technologies</th>
                            </tr>
                        </thead>
                        <tbody>
                """
                
                # Add rows for each result
                for result in safe_results:
                    confidence = result.get("confidence", 0) * 100
                    confidence_class = "success" if confidence > 70 else "warning" if confidence > 40 else "error"
                    
                    features = []
                    if result.get("has_login_form", False):
                        features.append('<span class="badge badge-green">Login Form</span>')
                    if "forms" in result and len(result["forms"]) > 0:
                        features.append(f'<span class="badge badge-blue">{len(result["forms"])} Forms</span>')
                    if result.get("status_code", 0) == 401 or result.get("status_code", 0) == 403:
                        features.append('<span class="badge badge-orange">Authentication Required</span>')
                        
                    technologies = ""
                    if result.get("technologies", []):
                        technologies = '<ul class="tech-list">' + ''.join([f'<li><span class="badge badge-blue">{tech}</span></li>' for tech in result.get("technologies", [])]) + '</ul>'
                    
                    html_content += f"""
                        <tr>
                            <td><a href="{result.get('url', '#')}" target="_blank">{result.get('url', 'Unknown')}</a></td>
                            <td>{result.get('status_code', 'Unknown')}</td>
                            <td>{html.escape(result.get('title', 'Unknown'))}</td>
                            <td class="{confidence_class}">{confidence:.1f}%</td>
                            <td>{"".join(features)}</td>
                            <td>{technologies}</td>
                        </tr>
                    """
                
                html_content += """
                        </tbody>
                    </table>
                """
            
            # Close tags
            html_content += """
                </div>
                <script>
                    document.addEventListener("DOMContentLoaded", function() {
                        // Add any JavaScript enhancements here
                    });
                </script>
            </body>
            </html>
            """
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            adv_logger.log_info(f"Exported {len(results)} results to HTML: {filename}")
            return True
            
        except Exception as e:
            adv_logger.log_error(f"Failed to export to HTML: {str(e)}")
            return False
    
    def _export_csv(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        """Export results to CSV format"""
        try:
            # Ensure all results have required fields
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write header
                writer.writerow([
                    "URL", "Status", "Title", "Confidence", "Has Login Form", 
                    "Technologies", "Server", "Content Length", "Form Count"
                ])
                
                # Write data
                for result in safe_results:
                    writer.writerow([
                        result.get("url", "Unknown"),
                        result.get("status_code", "Unknown"),
                        result.get("title", "Unknown"),
                        f"{result.get('confidence', 0) * 100:.1f}%",
                        "Yes" if result.get("has_login_form", False) else "No",
                        ", ".join(result.get("technologies", [])),
                        result.get("server", "Unknown"),
                        result.get("content_length", 0),
                        len(result.get("forms", []))
                    ])
            
            adv_logger.log_info(f"Exported {len(results)} results to CSV: {filename}")
            return True
            
        except Exception as e:
            adv_logger.log_error(f"Failed to export to CSV: {str(e)}")
            return False
    
    def _export_txt(self, results: List[Dict], scan_info: Dict, filename: str) -> bool:
        """Export results to plain text format"""
        try:
            # Ensure all results have required fields
            safe_results = [self._ensure_result_has_required_fields(r) for r in results]
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("===== Admin Panel Finder Results =====\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Write scan info
                f.write(f"Target URL: {scan_info.get('target_url', 'Unknown')}\n")
                f.write(f"Scan Mode: {scan_info.get('scan_mode', 'Unknown')}\n")
                f.write(f"Total Paths Checked: {scan_info.get('total_paths', 0)}\n")
                f.write(f"Scan Duration: {scan_info.get('scan_time', 0):.2f} seconds\n\n")
                
                f.write(f"Found {len(safe_results)} potential admin panels\n\n")
                
                # Write results
                for i, result in enumerate(safe_results, 1):
                    confidence = result.get("confidence", 0) * 100
                    f.write(f"[{i}] {result.get('url', 'Unknown')}\n")
                    f.write(f"    Status Code: {result.get('status_code', 'Unknown')}\n")
                    f.write(f"    Title: {result.get('title', 'Unknown')}\n")
                    f.write(f"    Confidence: {confidence:.1f}%\n")
                    f.write(f"    Server: {result.get('server', 'Unknown')}\n")
                    
                    # Add login form info
                    f.write(f"    Has Login Form: {'Yes' if result.get('has_login_form', False) else 'No'}\n")
                    
                    # Add technologies info
                    if result.get("technologies", []):
                        f.write(f"    Technologies: {', '.join(result.get('technologies', []))}\n")
                    
                    f.write("\n")
            
            adv_logger.log_info(f"Exported {len(results)} results to TXT: {filename}")
            return True
            
        except Exception as e:
            adv_logger.log_error(f"Failed to export to TXT: {str(e)}")
            return False
    
    def export_results(self, results: List[Dict], scan_info: Dict, format_type: str = None, base_filename: str = None) -> Dict[str, bool]:
        """Export results to the specified format
        
        Args:
            results: List of result objects
            scan_info: Information about the scan
            format_type: Format type to export (json, html, csv, txt). If None, will use config.EXPORT_FORMATS
            base_filename: Base name for the result file
            
        Returns:
            Dictionary with format types as keys and success status as values
        """
        if not results:
            return {}
        
        # Create results directory if it doesn't exist
        os.makedirs(self.results_dir, exist_ok=True)
        
        # Determine which formats to use
        export_formats = []
        
        # If a specific format is specified, use that
        if format_type:
            if format_type in self.supported_formats:
                export_formats = [format_type]
            else:
                export_formats = self.config.EXPORT_FORMATS
        # Otherwise use all formats from config
        else:
            export_formats = self.config.EXPORT_FORMATS
        
        # Filter to supported formats only
        export_formats = [fmt for fmt in export_formats if fmt in self.supported_formats]
        
        if not export_formats:
            adv_logger.log_warning("No valid export formats available. Using default: json")
            export_formats = ["json"]
        
        export_status = {}
        exported_files = []
        
        # Export to each format
        for fmt in export_formats:
            filename = self._get_result_filename(base_filename, fmt)
            
            if fmt == "json":
                success = self._export_json(results, scan_info, filename)
            elif fmt == "html":
                success = self._export_html(results, scan_info, filename)
            elif fmt == "csv":
                success = self._export_csv(results, scan_info, filename)
            elif fmt == "txt":
                success = self._export_txt(results, scan_info, filename)
            else:
                success = False
                
            export_status[fmt] = success
            
            if success:
                exported_files.append(filename)
            
        # Log export activity
        if exported_files:
            adv_logger.log_results_exported(export_formats, len(results))
            
        return export_status
    
    def list_result_files(self) -> List[str]:
        """List all result files in the results directory"""
        try:
            if not os.path.exists(self.results_dir):
                return []
                
            # Get all result files
            result_files = []
            for filename in os.listdir(self.results_dir):
                if filename.endswith((".json", ".html", ".csv", ".txt")):
                    result_files.append(filename)
                    
            return sorted(result_files, reverse=True)
            
        except Exception as e:
            adv_logger.log_error(f"Failed to list result files: {str(e)}")
            return []
    
    def view_result_file(self, filename: str) -> str:
        """Get the contents of a result file
        
        Args:
            filename: Name of the file to view
            
        Returns:
            Contents of the file as a string, or empty string if error
        """
        try:
            filepath = os.path.join(self.results_dir, filename)
            
            if not os.path.exists(filepath):
                return ""
                
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
                
        except Exception as e:
            adv_logger.log_error(f"Failed to view result file: {str(e)}")
            return ""