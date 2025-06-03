"""
Scanner module for Find The Admin Panel

This module handles the core scanning functionality for detecting admin panels.
It includes the Scanner class responsible for performing concurrent requests
and analyzing responses to identify potential admin panels.
"""

import os
import aiohttp
import asyncio
import time
import random
import re
import ssl
import certifi
import signal
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from rich.progress import Progress, TextColumn, BarColumn, TimeRemainingColumn
from rich.console import Console
from urllib.parse import urlparse
from aiohttp import ClientSession, TCPConnector, ClientTimeout

# Import advanced logging tool
from scripts.logging import get_logger

# Initialize advanced logger
adv_logger = get_logger('logs')
console = Console()

class Scanner:
    """Scanner for detecting admin panels on websites"""
    
    def __init__(self, config):
        """Initialize the scanner with configuration"""
        self.config = config
        self.session = None
        self.running = False
        self.results = []
        self.scan_info = {}
        self.valid_results = []  # Tracks valid findings for summary
        
        # Add variables for Ctrl+C handling
        self.ctrl_c_pressed = 0
        self.last_ctrl_c_time = 0
        self.ctrl_c_timeout = 2  # seconds between presses to count as double-press
        
        # Success file path
        self.success_file = "success.txt"
        
        # Set up signal handler for this instance
        self._setup_signal_handler()
    
    def _setup_signal_handler(self):
        """Set up signal handler for Ctrl+C"""
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle Ctrl+C key presses
        
        First press: Stop the current scan and display results
        Second press within timeout: Exit the application
        """
        current_time = time.time()
        
        # Check if it's a double press (within timeout period)
        if self.ctrl_c_pressed > 0 and (current_time - self.last_ctrl_c_time) < self.ctrl_c_timeout:
            console.print("\n\n[bold red]Exiting application (Ctrl+C pressed twice).[/bold red]")
            self._save_current_results()  # Save any remaining results before exit
            os._exit(0)  # Force exit
        
        # First press or timeout expired
        self.ctrl_c_pressed += 1
        self.last_ctrl_c_time = current_time
        
        if self.ctrl_c_pressed == 1:
            console.print("\n\n[bold yellow]Scan interrupted by user. Stopping scan and displaying current results...[/bold yellow]")
            
            # Stop the scan
            self.stop_scan()
            
            # Display current results
            self._display_current_results()
            
            console.print("\n[bold yellow]Press Ctrl+C again within 2 seconds to exit the application.[/bold yellow]")
            console.print("[bold yellow]Or press Enter to continue...[/bold yellow]")
    
    def _display_current_results(self):
        """Display current scan results after interruption"""
        if not self.results:
            console.print("[yellow]No results available yet.[/yellow]")
            return
        
        found_count = sum(1 for r in self.results if r.get("found", False))
        total_count = len(self.results)
        
        console.print(f"\n[bold cyan]Scan Summary (Interrupted)[/bold cyan]")
        console.print(f"Target URL: {self.scan_info.get('url', 'Unknown')}")
        console.print(f"Mode: {self.scan_info.get('mode', 'Unknown')}")
        console.print(f"Found: [bold green]{found_count}[/bold green] potential admin panels out of [bold]{total_count}[/bold] checked")
        
        if found_count > 0:
            console.print("\n[bold green]Potential Admin Panels:[/bold green]")
            for result in self.results:
                if result.get("found", False):
                    console.print(f"  - {result['url']} (Confidence: {result['confidence']:.2f}, Status: {result['status_code']})")
    
    def _save_current_results(self):
        """Save current results to success.txt file"""
        if not self.results:
            return
            
        found_results = [r for r in self.results if r.get("found", False)]
        if not found_results:
            return
            
        try:
            with open(self.success_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Interrupted Scan Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                for result in found_results:
                    f.write(f"URL: {result['url']}\n")
                    f.write(f"Title: {result['title']}\n")
                    f.write(f"Confidence: {result['confidence']:.2f}\n")
                    f.write(f"Status Code: {result['status_code']}\n")
                    f.write("-" * 50 + "\n")
        except Exception as e:
            adv_logger.log_error(f"Error saving results to {self.success_file}: {str(e)}")

    @classmethod
    async def create(cls, config):
        """Create and initialize a scanner instance
        
        Args:
            config: Configuration object
            
        Returns:
            Initialized Scanner instance
        """
        scanner = cls(config)
        await scanner.create_session()
        return scanner
        
    async def create_session(self):
        """Create an HTTP session for scanning"""
        try:
            # Create a custom SSL context that's less strict for compatibility
            connector = TCPConnector(
                ssl=False,  # Disable SSL verification
                limit=self.config.MAX_CONCURRENT_TASKS,
                ttl_dns_cache=300,  # Cache DNS results for 5 minutes
                force_close=False,  # Enable connection pooling
                enable_cleanup_closed=True
            )
            
            # Configure timeout based on config
            timeout = ClientTimeout(total=self.config.CONNECTION_TIMEOUT, connect=self.config.CONNECTION_TIMEOUT/2)
            
            # Create session with optimized headers
            self.session = ClientSession(
                connector=connector,
                timeout=timeout,
                trust_env=True
            )
            
            adv_logger.log_info("Created HTTP session for scanning")
            return True
        except Exception as e:
            adv_logger.log_error(f"Error creating HTTP session: {str(e)}")
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get HTTP headers with a random user agent"""
        if not self.config.USER_AGENTS:
            adv_logger.log_warning("No user agents configured. Using default.")
            return {"User-Agent": "Mozilla/5.0 (compatible; AdminPanelFinder/1.0)"}
        
        user_agent = random.choice(self.config.USER_AGENTS)
        headers = {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5,ar;q=0.3",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        }
        
        # Add extra headers from config
        if hasattr(self.config, 'HEADERS_EXTRA') and self.config.HEADERS_EXTRA:
            headers.update(self.config.HEADERS_EXTRA)
            
        return headers

    def _extract_title(self, content: str) -> str:
        """Extract page title from HTML content"""
        try:
            title_match = re.search('<title>(.*?)</title>', content, re.IGNORECASE | re.DOTALL)
            if title_match:
                return title_match.group(1).strip()
        except Exception as e:
            adv_logger.log_debug(f"Error extracting title: {str(e)}")
        return "Unknown"

    def _has_login_form(self, content: str) -> bool:
        """Check if the page contains a login form"""
        login_indicators = [
            # Form with password field - standard pattern
            re.search(r'<form[^>]*>.*?<input[^>]*type=["\']password["\'].*?</form>', content, re.DOTALL | re.IGNORECASE),
            # Login keywords in form - expanded keywords
            re.search(r'<form[^>]*>.*?(?:login|log[_\s]?in|sign[_\s]?in|admin|authenticate|session|account|auth|password).*?</form>', content, re.DOTALL | re.IGNORECASE),
            # Input fields with login-related names/ids - expanded attributes
            re.search(r'<input[^>]*(?:name|id|placeholder)=["\'](?:username|user|email|login|admin|account|user_?name)["\']', content, re.IGNORECASE),
            # Login-related button texts - expanded button variations
            re.search(r'<button[^>]*>.*?(?:login|log[_\s]?in|sign[_\s]?in|submit|enter|access).*?</button>', content, re.DOTALL | re.IGNORECASE),
            # Non-button input submit with login keywords
            re.search(r'<input[^>]*type=["\']submit["\'][^>]*value=["\'](?:login|log[_\s]?in|sign[_\s]?in|submit|enter|access)["\']', content, re.IGNORECASE),
            # Multilingual login indicators - using more languages without storing them as plain text
            # Arabic, Persian, Turkish, Russian, French, Spanish, German, Chinese, Japanese
            re.search(r'<form[^>]*>.*?(?:connexion|s\'identifier|connecter|identifiant|iniciar sesión|acceso|ingresar|entrar|anmelden|einloggen|登录|登入|ログイン).*?</form>', content, re.DOTALL | re.IGNORECASE),
            # Check for specific login-related CSS classes
            re.search(r'<(?:div|form|section)[^>]*class=["\'](?:[^"\']*\s)?(?:login|signin|auth|account)(?:\s[^"\']*)?["\']', content, re.IGNORECASE),
        ]
        
        return any(login_indicators)

    def _detect_technologies(self, content: str, headers: Dict) -> List[str]:
        """Detect web technologies used on the page"""
        techs = []
        
        # Check for common signatures
        tech_signatures = {
            "WordPress": ["wp-content", "wp-includes", "wp-admin"],
            "Joomla": ["joomla", "com_content", "com_users"],
            "Drupal": ["drupal", "sites/all", "sites/default"],
            "Laravel": ["laravel", "csrf-token"],
            "Django": ["csrfmiddlewaretoken", "django"],
            "Angular": ["ng-app", "ng-controller", "angular"],
            "React": ["react", "react-dom", "reactjs"],
            "Vue.js": ["vue", "vue.js", "vuejs"],
            "Bootstrap": ["bootstrap.css", "bootstrap.min.css", "bootstrap.js"],
            "jQuery": ["jquery.js", "jquery.min.js"],
            "PHP": ["php", ".php"],
            "ASP.NET": ["asp.net", ".aspx", "viewstate"],
            "Node.js": ["node_modules"],
            "Express": ["express", "powered by express"]
        }
        
        for tech, signatures in tech_signatures.items():
            if any(sig.lower() in content.lower() for sig in signatures):
                techs.append(tech)
        
        # Check headers for more info
        if "X-Powered-By" in headers:
            techs.append(headers["X-Powered-By"])
            
        if "Server" in headers:
            techs.append(headers["Server"])
        
        return list(set(techs))  # Remove duplicates

    def _detect_admin_layout(self, content: str) -> float:
        """Detect common admin panel layout patterns and assign a score"""
        score = 0.0
        
        # Check for sidebar navigation - common in admin panels
        if re.search(r'<(?:div|nav|aside)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:sidebar|side-nav|admin-nav|navigation|main-menu)(?:\s[^"\']*)?["\']', content, re.IGNORECASE):
            score += 0.15
        
        # Check for dashboard elements like cards, widgets, or panels
        if re.search(r'<(?:div|section)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:card|widget|panel|dashboard-item|stat|metric)(?:\s[^"\']*)?["\']', content, re.IGNORECASE):
            score += 0.10
        
        # Check for table layouts (common in admin lists)
        table_patterns = [
            re.search(r'<table[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:admin|data-table|list-table|users|records)(?:\s[^"\']*)?["\']', content, re.IGNORECASE),
            re.search(r'<th[^>]*>.*?(?:ID|Name|User|Email|Status|Actions|Edit|Delete|Role|Permission).*?</th>', content, re.DOTALL | re.IGNORECASE)
        ]
        if any(table_patterns):
            score += 0.10
        
        # Check for action buttons like add/edit/delete
        action_buttons = [
            re.search(r'<(?:a|button)[^>]*>.*?(?:Add New|Create New|New|Add|Edit|Update|Delete|Remove).*?</(?:a|button)>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<(?:a|button)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:add-new|create-new|btn-add|btn-edit|btn-delete)(?:\s[^"\']*)?["\']', content, re.IGNORECASE)
        ]
        if any(action_buttons):
            score += 0.08
        
        # Check for breadcrumbs (common in admin panels)
        if re.search(r'<(?:div|nav|ul)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:breadcrumb|breadcrumbs)(?:\s[^"\']*)?["\']', content, re.IGNORECASE):
            score += 0.05
        
        # Check for admin-specific footer or branding
        admin_footer = [
            re.search(r'<(?:div|footer)[^>]*>.*?(?:Admin|Administration|Dashboard|©|Copyright).*?</(?:div|footer)>', content, re.DOTALL | re.IGNORECASE),
            re.search(r'<(?:div|footer)[^>]*(?:class|id)=["\'](?:[^"\']*\s)?(?:admin-footer|dashboard-footer)(?:\s[^"\']*)?["\']', content, re.IGNORECASE)
        ]
        if any(admin_footer):
            score += 0.05
        
        return min(score, 0.40)  # Cap the layout score at 0.40

    def _check_meta_indicators(self, content: str) -> float:
        """Check meta tags and other header indicators for admin panels"""
        score = 0.0
        
        # Check for admin-related meta tags
        meta_patterns = [
            re.search(r'<meta[^>]*name=["\'](?:application-name|app-name)["\'][^>]*content=["\'][^"\']*(?:admin|dashboard|control)[^"\']*["\']', content, re.IGNORECASE),
            re.search(r'<meta[^>]*content=["\'][^"\']*(?:admin|dashboard|control)[^"\']*["\'][^>]*name=["\'](?:application-name|app-name)["\']', content, re.IGNORECASE),
            re.search(r'<meta[^>]*name=["\']generator["\'][^>]*content=["\'][^"\']*(?:wordpress|joomla|drupal|admin|cms)[^"\']*["\']', content, re.IGNORECASE)
        ]
        if any(meta_patterns):
            score += 0.05
        
        # Check for admin-specific JS files
        js_patterns = [
            re.search(r'<script[^>]*src=["\'][^"\']*(?:admin|dashboard|control)[^"\']*\.js["\']', content, re.IGNORECASE),
            re.search(r'<script[^>]*src=["\'][^"\']*(?:wp-admin|admin-ajax|adminify)[^"\']*["\']', content, re.IGNORECASE)
        ]
        if any(js_patterns):
            score += 0.05
        
        # Check for admin-specific CSS files
        css_patterns = [
            re.search(r'<link[^>]*href=["\'][^"\']*(?:admin|dashboard|control)[^"\']*\.css["\']', content, re.IGNORECASE),
            re.search(r'<link[^>]*href=["\'][^"\']*(?:wp-admin|admin-styles|adminify)[^"\']*["\']', content, re.IGNORECASE)
        ]
        if any(css_patterns):
            score += 0.05
        
        return min(score, 0.15)  # Cap the meta score at 0.15

    def _analyze_content_keywords(self, content: str) -> float:
        """Analyze content for admin-related keywords in multiple languages"""
        score = 0.0
        content_lower = content.lower()
        
        # Multilingual admin keywords - Using general patterns instead of specific Arabic text
        multilingual_admin_keywords = [
            # English
            "admin panel", "dashboard", "control panel", "administration", "site admin",
            "user management", "permissions", "settings", "login", "account", "administrator",
            "stats", "statistics", "reports",
            
            # Universal symbols and patterns
            "admin", "panel", "manage", "config", "backend",
            
            # Generalized patterns that would match various languages
            "login", "user", "control", "access", "system", "management",
            "security", "permission", "setting", "config", "account", "profile",
            "password", "auth", "log", "stat", "report", "dashboard", "admin"
        ]
        
        for keyword in multilingual_admin_keywords:
            if keyword in content_lower:
                score += 0.02
                # Avoid double counting similar keywords
                if score > 0.20:
                    break
        
        # Common admin features in various languages
        admin_features = [
            # English
            "user management", "user administration", "content management", "site settings", 
            "configuration", "system settings", "site options",
            
            # Spanish 
            "gestión de usuarios", "administración", "panel de control",
            
            # French
            "gestion des utilisateurs", "administration", "tableau de bord",
            
            # Chinese
            "權限管理", "权限管理", "用户管理", "站点设置",
            
            # German
            "benutzerverwaltung", "administration", "einstellungen", "systemkonfiguration",
            
            # Universal patterns
            "admin", "dashboard", "control", "panel", "manage", "users", "settings"
        ]
        
        for feature in admin_features:
            if feature.lower() in content_lower:
                score += 0.02
                if score > 0.20:
                    break
        
        return min(score, 0.20)  # Cap the content score at 0.20

    def _analyze_response_headers(self, headers: Dict) -> float:
        """Analyze response headers for admin panel indicators"""
        score = 0.0
        
        # Check for access control headers (indicating protected resource)
        if any(header in headers for header in ["WWW-Authenticate", "X-Permitted-Cross-Domain-Policies"]):
            score += 0.05
        
        # Check for csrf tokens in cookies (common in admin areas)
        cookies = headers.get("Set-Cookie", "")
        if re.search(r'(csrf|xsrf|token|admin|session|auth)', cookies, re.IGNORECASE):
            score += 0.05
        
        # Check for specific server or application headers that often indicate admin areas
        if "X-Powered-By" in headers and re.search(r'(wordpress|joomla|drupal|laravel|django|rails)', headers["X-Powered-By"], re.IGNORECASE):
            score += 0.03
        
        # Check for cache control headers (admin pages often disable caching)
        cache_headers = headers.get("Cache-Control", "")
        if "no-store" in cache_headers or "private" in cache_headers:
            score += 0.02
        
        return min(score, 0.10)  # Cap the headers score at 0.10

    def _calculate_confidence(self, status_code: int, content: str, title: str, path: str, headers: Dict) -> float:
        """Calculate confidence score for an admin panel
        
        Args:
            status_code: HTTP status code
            content: HTML content
            title: Page title
            path: URL path
            headers: Response headers
            
        Returns:
            Confidence score between 0 and 1
        """
        # Convert content to lowercase for case-insensitive matching
        content_lower = content.lower() if content else ""
        
        # Base score for path based on common admin paths
        base_path_score = 0.0
        
        # Score based on specific admin paths
        admin_path_scores = {
            "admin": 0.15, "administrator": 0.15, "administration": 0.15, 
            "adm": 0.1, "manage": 0.1, "management": 0.1, "manager": 0.1,
            "cp": 0.1, "control": 0.1, "panel": 0.1, "admincp": 0.15,
            "wp-admin": 0.15, "wp-login": 0.15, "admin-panel": 0.15,
            "backend": 0.1, "dashboard": 0.15, "login": 0.02, "signin": 0.02,
            "portal": 0.05, "webmaster": 0.1, "moderator": 0.1, "site-admin": 0.15
        }

        # Multilingual admin path terms - using generic keywords with English descriptions
        multilingual_path_terms = {
            # Multilingual terms for "login"
            "connexion": 0.02, "acesso": 0.02, "acceso": 0.02, "einloggen": 0.02,
            # Multilingual terms for "admin"
            "admin": 0.15, "admincp": 0.15, "adminedit": 0.15,
            # Multilingual terms for "control panel" 
            "panel": 0.1, "dashboard": 0.15, "console": 0.1,
            # Other international terms
            "gestion": 0.05, "gestao": 0.05, "verwaltung": 0.05
        }
        
        # Apply path scoring
        for pattern, score in admin_path_scores.items():
            if pattern in path.lower():
                base_path_score += score
        
        # Apply multilingual path terms
        for term, score in multilingual_path_terms.items():
            if term in path.lower():
                base_path_score += score
        
        # 2. Check for keywords in title (improved with more specific weighting)
        admin_title_keywords = {
            # High-confidence keywords (exact admin panel indicators)
            "admin panel": 0.18, "admin dashboard": 0.18, "administrator": 0.18, 
            "control panel": 0.18, "admin console": 0.18, "management panel": 0.18, 
            "admin area": 0.17, "administration area": 0.17, "admin section": 0.17,
            
            # Medium-confidence keywords (likely admin but could be user area)
            "admin": 0.12, "dashboard": 0.12, "control panel": 0.12, "admincp": 0.12,
            "management": 0.11, "backend": 0.11, "console": 0.10, "administration": 0.12,
            
            # Lower-confidence keywords (could be admin or regular login)
            "login": 0.03, "sign in": 0.03, "log in": 0.03, "authentication": 0.04,
            "access": 0.03, "portal": 0.04, "account": 0.03, "secure": 0.03
        }
        
        # Apply title scoring with more precise matching
        if title and title.strip() != "Unknown":
            title_lower = title.lower()
            for keyword, score in admin_title_keywords.items():
                if keyword.lower() in title_lower:
                    # Exact match gets full score
                    if keyword.lower() == title_lower.strip():
                        base_path_score += score * 1.5  # Boost for exact title match
                    # Partial match gets regular score
                    else:
                        base_path_score += score
                    # Add small boost if admin is at the beginning of title
                    if title_lower.startswith(("admin", "dashboard", "panel", "control")):
                        base_path_score += 0.04
                    break
        
        # 3. Analyze status code (refined for better accuracy)
        if status_code == 200:
            base_path_score += 0.03  # Successful response
        elif status_code == 401 or status_code == 403:
            base_path_score += 0.20  # Strong indicator of a protected area
        elif status_code == 302 or status_code == 301:
            if any(redirect_term in headers.get("Location", "").lower() for redirect_term in ["login", "admin", "auth", "dashboard"]):
                base_path_score += 0.15  # Redirects to login or admin pages
            else:
                base_path_score += 0.01  # Generic redirect
        elif 500 <= status_code < 600:
            base_path_score += 0.01  # Server errors can sometimes indicate hidden areas
        
        # 4. Advanced layout analysis - new method
        base_path_score += self._detect_admin_layout(content)
        
        # 5. Meta tags and resources analysis - new method
        base_path_score += self._check_meta_indicators(content)
        
        # 6. Content keyword analysis - new method
        base_path_score += self._analyze_content_keywords(content)
        
        # 7. Response headers analysis - new method
        base_path_score += self._analyze_response_headers(headers)
        
        # 8. IMPROVED: False positive detection - Reduce score for pages that are likely NOT admin panels
        
        # Login form check - more sophisticated
        has_login_form = self._has_login_form(content)
        if has_login_form:
            # Only add bonus for login forms that appear to be admin-related
            if re.search(r'(admin|administrator|manage|dashboard|control)', content_lower):
                base_path_score += 0.15
            else:
                # Regular login forms get a very small bonus
                base_path_score += 0.05
        
        # Check for user registration indicators - increased penalty
        if re.search(r'(sign[- ]?up|register|create[- ]?account|registration|join[- ]?now)', content_lower):
            # If it's a registration page without admin context, reduce score
            if not re.search(r'(admin|administrator|dashboard|control[- ]?panel)', content_lower):
                base_path_score -= 0.20
        
        # Check for social media login indicators - increased penalty
        if re.search(r'(facebook|twitter|google|github|linkedin|social[- ]?media|social[- ]?login)', content_lower):
            # Social media login pages are usually not admin panels
            if not re.search(r'(admin|administrator|control|panel|dashboard)', path.lower()):
                base_path_score -= 0.15
        
        # Check for typical user-facing features that are NOT in admin panels
        user_facing_features = [
            r'shopping[- ]?cart', r'add[- ]?to[- ]?cart', r'checkout', r'purchase', 
            r'my[- ]?account', r'profile', r'my[- ]?profile', r'personal[- ]?info',
            r'wishlist', r'favorites', r'product[- ]?reviews', r'customer[- ]?reviews',
            r'subscribe', r'newsletter', r'membership', r'forgot[- ]?password'
        ]
        
        for feature in user_facing_features:
            if re.search(feature, content_lower):
                base_path_score -= 0.08
                # Don't reduce too much at once
                if base_path_score <= 0.3:
                    break
        
        # Check for typical content sections that indicate regular website, not admin
        content_sections = [
            r'about[- ]?us', r'about', r'contact[- ]?us', r'contact',
            r'faq', r'privacy[- ]?policy', r'terms[- ]?of[- ]?service', r'terms[- ]?and[- ]?conditions',
            r'shipping', r'delivery', r'returns', r'blog', r'news', r'articles'
        ]
        
        section_count = 0
        for section in content_sections:
            if re.search(section, content_lower):
                section_count += 1
        
        # If multiple regular website sections are found, it's likely not an admin panel
        if section_count >= 2:
            base_path_score -= 0.20
        
        # Content size considerations (admin pages tend to be smaller than regular user pages)
        content_length = len(content)
        if 5000 <= content_length <= 40000:  # Typical size for admin pages
            base_path_score += 0.02
        elif content_length > 100000:  # Very large pages are likely not admin panels
            base_path_score -= 0.08
        
        # Look for admin-specific elements in content
        admin_specific_patterns = [
            r'user[- ]management', r'site[- ]settings', r'system[- ]settings',
            r'add[- ]user', r'edit[- ]user', r'delete[- ]user', r'permissions',
            r'configuration', r'analytics', r'statistics', r'reports'
        ]
        
        admin_pattern_count = 0
        for pattern in admin_specific_patterns:
            if re.search(pattern, content_lower):
                admin_pattern_count += 1
                
        # Add significant boost if multiple admin-specific patterns are found
        if admin_pattern_count >= 2:
            base_path_score += 0.15
        elif admin_pattern_count == 1:
            base_path_score += 0.08
        
        # Add penalty if title contains terms indicating regular user login
        user_login_indicators = [
            'member login', 'customer login', 'user login', 'account login',
            'sign in', 'log in', 'login to your account'
        ]
        
        if title and title.strip() != "Unknown":
            title_lower = title.lower()
            for indicator in user_login_indicators:
                if indicator in title_lower:
                    # If it matches user login but doesn't have admin context, reduce score
                    if not re.search(r'(admin|administrator|manage|dashboard|control)', content_lower):
                        base_path_score -= 0.15
                    break
        
        # Ensure confidence is between 0 and 1
        return min(max(base_path_score, 0.0), 1.0)

    async def scan_path(self, base_url: str, path: str) -> Dict:
        """Scan a single path to check for admin panel"""
        try:
            # Check if scan was stopped
            if not self.running:
                return None
                
            # Add delay for stealth mode
            if self.config.DETECTION_MODE == "stealth":
                await asyncio.sleep(random.uniform(0.5, 2.0))
            
            full_url = f"{base_url}/{path}".replace("//", "/").replace(":/", "://")
            headers = self._get_headers()
            
            async with self.session.get(full_url, headers=headers, allow_redirects=True, 
                                      timeout=self.config.CONNECTION_TIMEOUT) as response:
                status = response.status
                if status == 404:
                    return None
                    
                # Read page content for analysis
                content = await response.text(errors='ignore')
                title = self._extract_title(content)
                
                # Calculate confidence based on multiple criteria - using improved method with headers
                confidence = self._calculate_confidence(status, content, title, path, dict(response.headers))
                
                result = {
                    "url": full_url,
                    "status_code": status,
                    "title": title,
                    "confidence": confidence,
                    "found": confidence > 0.6,  # Increased threshold to reduce false positives
                    "has_login_form": self._has_login_form(content),
                    "technologies": self._detect_technologies(content, response.headers),
                    "headers": dict(response.headers),
                    "content_length": len(content),
                    "scan_time": datetime.now().isoformat()
                }
                
                # If found, save to success.txt immediately
                if result["found"]:
                    self._save_result_to_file(result)
                
                return result
        except asyncio.TimeoutError:
            adv_logger.log_debug(f"Timeout scanning {full_url}")
            return None
        except Exception as e:
            adv_logger.log_debug(f"Error scanning {full_url}: {str(e)}")
            return None

    def _save_result_to_file(self, result: Dict):
        """Save a successful result to success.txt file immediately"""
        try:
            with open(self.success_file, 'a', encoding='utf-8') as f:
                f.write(f"\n=== FOUND ADMIN PANEL ===\n")
                f.write(f"URL: {result['url']}\n")
                f.write(f"Title: {result['title']}\n")
                f.write(f"Confidence: {result['confidence']:.2f}\n")
                f.write(f"Status Code: {result['status_code']}\n")
                
                # Add more details if available
                if result.get('has_login_form'):
                    f.write(f"Login Form: Yes\n")
                
                if result.get('technologies'):
                    f.write(f"Technologies: {', '.join(result['technologies'])}\n")
                    
                f.write(f"Content Length: {result.get('content_length', 0)} bytes\n")
                f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            adv_logger.log_error(f"Error saving result to {self.success_file}: {str(e)}")

    async def scan(self, url: str, paths: List[str], concurrency: int = None) -> List[Dict]:
        """Scan a URL with multiple paths for admin panels"""
        if not paths:
            adv_logger.log_warning(f"No paths to scan for {url}")
            return []
        
        # Clear success.txt file before starting new scan
        self._clear_success_file()
        
        # Set scan as running
        self.running = True
        self.results = []
        self.valid_results = []
        self.scan_info = {
            "url": url,
            "mode": self.config.DETECTION_MODE,
            "start_time": time.time(),
            "paths_count": len(paths),
            "concurrency": concurrency or self.config.MAX_CONCURRENT_TASKS
        }
        
        # Reset Ctrl+C counter
        self.ctrl_c_pressed = 0
        self.last_ctrl_c_time = 0
        
        # NOTE: Log scan start is handled in finder.py to avoid duplication
        # adv_logger.log_scan_start(url, self.config.DETECTION_MODE, len(paths))
        
        # Create session if needed
        if not self.session:
            await self.create_session()
            if not self.session:
                adv_logger.log_error("Failed to create session for scanning")
                return []
        
        # Use configured or specified concurrency
        workers = concurrency or self.config.MAX_CONCURRENT_TASKS
        batch_size = self.config.BATCH_SIZE or min(50, len(paths))
        
        # Setup progress tracking
        try:
            progress = Progress(
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                TextColumn("[bold]{task.completed}/{task.total}"),
                TextColumn("[cyan]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=console
            )
            
            console.print(f"[cyan]Starting scan of [bold]{url}[/bold] with [bold]{len(paths)}[/bold] paths[/cyan]")
            console.print(f"[cyan]Using [bold]{workers}[/bold] concurrent workers and batch size of [bold]{batch_size}[/bold][/cyan]")
            
            all_results = []
            
            # Split paths into batches for better memory and performance control
            batches = [paths[i:i + batch_size] for i in range(0, len(paths), batch_size)]
            
            with progress:
                task_id = progress.add_task(f"Scanning {url}", total=len(paths))
                
                for batch in batches:
                    if not self.running:  # Check if user stopped the scan
                        console.print("[yellow]Scan stopped by user.[/yellow]")
                        break
                        
                    # Create tasks for current batch
                    tasks = [self.scan_path(url, path) for path in batch]
                    
                    # Execute tasks in parallel
                    batch_results = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    # Filter out None results and exceptions
                    batch_results = [r for r in batch_results if r and not isinstance(r, Exception)]
                    all_results.extend(batch_results)
                    
                    # Update found results
                    for result in batch_results:
                        if result.get("found", False):
                            self.valid_results.append(result)
                                
                    progress.update(task_id, advance=len(batch))
            
            # Update scan info with end time
            self.scan_info["end_time"] = time.time()
            self.scan_info["duration"] = self.scan_info["end_time"] - self.scan_info["start_time"]
            self.scan_info["found_count"] = len(self.valid_results)
            self.scan_info["total_count"] = len(all_results)
            self.scan_info["success_rate"] = len(self.valid_results) / len(paths) if paths else 0
            
            # Log scan completion
            adv_logger.log_scan_complete(
                url, 
                len(paths), 
                len(self.valid_results), 
                self.scan_info["duration"]
            )
            
            # Sort results by confidence
            self.valid_results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
            self.results = all_results
            
            # Write summary to success.txt
            self._write_scan_summary()
            
            return all_results
            
        except asyncio.CancelledError:
            console.print("[yellow]\nScan was cancelled.[/yellow]")
            self._save_current_results()  # Save results before exit
            return self.results
        except Exception as e:
            adv_logger.log_error(f"Error during scan: {str(e)}")
            return self.results
    
    def _clear_success_file(self):
        """Clear the success.txt file at the start of a new scan"""
        try:
            target_url = self.scan_info.get('url', 'Unknown')
            with open(self.success_file, 'w', encoding='utf-8') as f:
                f.write(f"--- New Scan Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"Target: {target_url}\n")
                f.write(f"Mode: {self.config.DETECTION_MODE}\n")
                f.write("-" * 50 + "\n\n")
        except Exception as e:
            adv_logger.log_error(f"Error clearing success file: {str(e)}")
    
    def _write_scan_summary(self):
        """Write scan summary to success.txt file"""
        try:
            with open(self.success_file, 'a', encoding='utf-8') as f:
                f.write(f"\n--- Scan Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n")
                f.write(f"Duration: {self.scan_info.get('duration', 0):.2f} seconds\n")
                f.write(f"Total paths checked: {self.scan_info.get('total_count', 0)}\n")
                f.write(f"Found admin panels: {self.scan_info.get('found_count', 0)}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            adv_logger.log_error(f"Error writing scan summary: {str(e)}")

    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            try:
                await self.session.close()
                adv_logger.log_info("Closed HTTP session")
            except Exception as e:
                adv_logger.log_error(f"Error closing HTTP session: {str(e)}")
    
    async def close(self):
        """Close the scanner and release resources"""
        await self.cleanup()
    
    def is_running(self) -> bool:
        """Check if a scan is currently running"""
        return self.running
    
    def get_results(self) -> List[Dict]:
        """Get scan results"""
        return self.results
    
    def get_scan_info(self) -> Dict:
        """Get scan information"""
        return self.scan_info
    
    def stop_scan(self):
        """Stop the current scan"""
        self.running = False
        adv_logger.log_warning("Scan stopped by user")
        console.print("[yellow]Scan stopped by user[/yellow]") 