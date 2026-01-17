import random
import os
import sys
import time
import json
from pathlib import Path
import subprocess
import requests
from fake_useragent import UserAgent
import stem
import stem.connection
from stem import Signal
from stem.control import Controller

# Try to import the original Downloader
try:
    from interactive_downloader import Downloader
except ImportError:
    # If not available, create a minimal version
    class Downloader:
        def __init__(self):
            self.__bitrate = "320k"
            self.__audio_format = "mp3"
            self.__output_dir = Path("Albums")
        
        def log_success(self, message):
            print(f"SUCCESS: {message}")
        
        def log_error(self, message):
            print(f"ERROR: {message}")
        
        def log_failure(self, message):
            print(f"FAILURE: {message}")
        
        def check_spotdl(self):
            return True
        
        @staticmethod
        def show_spotdl_help():
            print("spotdl help not available")
        
        @staticmethod
        def program_info():
            print("Program info not available")

DOWNLOAD_TIMEOUT = 120

class NetworkManager:
    """
    Comprehensive network management with:
    - Proxy rotation (HTTP/SOCKS)
    - VPN switching (if supported)
    - Tor circuit rotation
    - User agent rotation
    """
    
    def __init__(self, config_file="network_config.json"):
        self.config = self.load_config(config_file)
        self.ua = UserAgent()
        self.current_proxy = None
        self.current_user_agent = None
        self.tor_controller = None
        self.proxy_list = []
        self.vpn_interfaces = []
        
        # Initialize based on configuration
        self.setup_network_manager()
    
    def load_config(self, config_file):
        """Load network configuration from JSON file"""
        default_config = {
            "use_proxies": True,
            "use_tor": False,
            "use_vpn": False,
            "proxy_sources": [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
                "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/http.txt",
                "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
            ],
            "tor_port": 9050,
            "tor_control_port": 9051,
            "tor_password": "your_tor_password",  # Set your Tor password
            "vpn_interfaces": ["tun0", "tun1", "wg0"],  # Common VPN interfaces
            "max_proxy_age": 3600,  # 1 hour
            "proxy_test_url": "https://api.spotify.com/v1",
            "rotation_strategy": "random",  # random, round_robin, weighted
        }
        
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                loaded_config = json.load(f)
                return {**default_config, **loaded_config}
        else:
            # Save default config
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
            return default_config
    
    def setup_network_manager(self):
        """Initialize network components based on config"""
        print("Initializing Network Manager...")
        
        if self.config["use_proxies"]:
            self.load_proxies()
        
        if self.config["use_tor"]:
            self.setup_tor()
        
        if self.config["use_vpn"]:
            self.detect_vpn_interfaces()
        
        print(f"Network Manager Ready: {len(self.proxy_list)} proxies loaded")
    
    # ========== PROXY MANAGEMENT ==========
    
    def load_proxies(self):
        """Load proxies from multiple sources"""
        all_proxies = []
        
        for source in self.config["proxy_sources"]:
            try:
                response = requests.get(source, timeout=10)
                proxies = response.text.strip().split('\n')
                all_proxies.extend([p.strip() for p in proxies if p.strip()])
                print(f"Loaded {len(proxies)} proxies from {source}")
            except Exception as e:
                print(f"Failed to load proxies from {source}: {e}")
        
        # Add local proxy servers if any
        local_proxies = [
            "http://localhost:8080",
            "socks5://localhost:9050",  # Tor default
            "socks5://localhost:9052",  # Tor alternate
        ]
        all_proxies.extend(local_proxies)
        
        # Test and validate proxies
        self.proxy_list = self.test_proxies(all_proxies[:50])  # Test first 50
        
        # Save working proxies
        self.save_working_proxies()
    
    def test_proxies(self, proxies, max_workers=10):
        """Test proxies for connectivity and speed"""
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        working_proxies = []
        
        def test_proxy(proxy):
            try:
                # Test with Spotify API (lightweight request)
                test_url = "https://api.spotify.com/v1/search?q=test&type=track&limit=1"
                proxies_dict = {
                    'http': proxy,
                    'https': proxy
                }
                
                start_time = time.time()
                response = requests.get(
                    test_url,
                    proxies=proxies_dict,
                    timeout=5,
                    headers={'User-Agent': self.ua.random}
                )
                response_time = time.time() - start_time
                
                if response.status_code in [200, 429]:  # 429 is rate limit, but proxy works
                    return {
                        'proxy': proxy,
                        'response_time': response_time,
                        'working': True
                    }
            except Exception as e:
                pass
            
            return {'proxy': proxy, 'working': False}
        
        # Test proxies in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(test_proxy, proxy) for proxy in proxies]
            
            for future in as_completed(futures):
                result = future.result()
                if result['working']:
                    working_proxies.append(result)
                    print(f"✓ Proxy working: {result['proxy']} ({result['response_time']:.2f}s)")
        
        # Sort by response time
        working_proxies.sort(key=lambda x: x['response_time'])
        return [p['proxy'] for p in working_proxies]
    
    def save_working_proxies(self):
        """Save working proxies to file"""
        with open('working_proxies.json', 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'proxies': self.proxy_list
            }, f, indent=2)
    
    def get_random_proxy(self):
        """Get a random proxy from working list"""
        if not self.proxy_list:
            return None
        
        if self.config["rotation_strategy"] == "random":
            proxy = random.choice(self.proxy_list)
        elif self.config["rotation_strategy"] == "round_robin":
            if not hasattr(self, 'proxy_index'):
                self.proxy_index = 0
            proxy = self.proxy_list[self.proxy_index % len(self.proxy_list)]
            self.proxy_index += 1
        else:
            proxy = self.proxy_list[0]
        
        self.current_proxy = proxy
        return proxy
    
    # ========== TOR NETWORK MANAGEMENT ==========
    
    def setup_tor(self):
        """Initialize Tor connection"""
        try:
            # Connect to Tor control port
            self.tor_controller = Controller.from_port(
                port=self.config["tor_control_port"]
            )
            
            # Authenticate
            self.tor_controller.authenticate(password=self.config["tor_password"])
            
            print("✓ Tor controller connected successfully")
            
            # Get initial circuit info
            self.print_tor_info()
            
        except Exception as e:
            print(f"✗ Failed to connect to Tor: {e}")
            print("Make sure Tor is running with ControlPort enabled")
            print("Add to torrc: ControlPort 9051")
            print("              HashedControlPassword ...")
            self.tor_controller = None
    
    def get_tor_proxy(self, port=None):
        """Get Tor SOCKS5 proxy"""
        if port is None:
            port = self.config["tor_port"]
        
        return f"socks5://127.0.0.1:{port}"
    
    def renew_tor_circuit(self):
        """Create new Tor circuit (new IP)"""
        if not self.tor_controller:
            return False
        
        try:
            self.tor_controller.signal(Signal.NEWNYM)
            time.sleep(5)  # Wait for new circuit
            print("✓ Tor circuit renewed (new IP)")
            self.print_tor_info()
            return True
        except Exception as e:
            print(f"✗ Failed to renew Tor circuit: {e}")
            return False
    
    def print_tor_info(self):
        """Display current Tor circuit information"""
        if not self.tor_controller:
            return
        
        try:
            circuit_info = []
            for circuit in self.tor_controller.get_circuits():
                if circuit.status == "BUILT":
                    entry_relay = self.tor_controller.get_network_status(circuit.path[0][0])
                    exit_relay = self.tor_controller.get_network_status(circuit.path[-1][0])
                    
                    circuit_info.append({
                        'id': circuit.id,
                        'entry': entry_relay.address if entry_relay else "Unknown",
                        'exit': exit_relay.address if exit_relay else "Unknown"
                    })
            
            if circuit_info:
                print(f"Current Tor circuits: {len(circuit_info)}")
                for idx, circuit in enumerate(circuit_info[:3]):  # Show first 3
                    print(f"  Circuit {idx+1}: {circuit['entry']} → ... → {circuit['exit']}")
        
        except Exception as e:
            print(f"Could not get Tor info: {e}")
    
    def get_tor_ip(self):
        """Get current Tor exit IP"""
        try:
            tor_proxy = self.get_tor_proxy()
            response = requests.get(
                "https://api.ipify.org?format=json",
                proxies={'http': tor_proxy, 'https': tor_proxy},
                timeout=10
            )
            return response.json()['ip']
        except:
            return "Unknown"
    
    # ========== VPN MANAGEMENT ==========
    
    def detect_vpn_interfaces(self):
        """Detect available VPN network interfaces"""
        import platform
        
        system = platform.system()
        
        if system == "Windows":
            # Use PowerShell to get network interfaces
            try:
                result = subprocess.run(
                    ["powershell", "Get-NetAdapter | Where-Object {$_.InterfaceDescription -like '*VPN*' -or $_.Name -like '*VPN*'} | Select-Object -ExpandProperty Name"],
                    capture_output=True,
                    text=True,
                    shell=True
                )
                interfaces = result.stdout.strip().split('\n')
                self.vpn_interfaces = [iface.strip() for iface in interfaces if iface.strip()]
            except:
                pass
        
        elif system == "Linux":
            # Check common VPN interfaces
            for iface in ["tun0", "tun1", "wg0", "ppp0", "ovpn0"]:
                if Path(f"/sys/class/net/{iface}").exists():
                    self.vpn_interfaces.append(iface)
        
        elif system == "Darwin":  # macOS
            try:
                result = subprocess.run(
                    ["ifconfig", "-l"],
                    capture_output=True,
                    text=True
                )
                interfaces = result.stdout.strip().split()
                vpn_patterns = ["utun", "tun", "ppp", "ipsec"]
                self.vpn_interfaces = [
                    iface for iface in interfaces 
                    if any(pattern in iface for pattern in vpn_patterns)
                ]
            except:
                pass
        
        print(f"Detected VPN interfaces: {self.vpn_interfaces}")
    
    def switch_vpn_connection(self):
        """Switch to different VPN server/connection"""
        # This is platform/VPN-client specific
        # You'll need to implement based on your VPN client
        
        vpn_clients = {
            "openvpn": self.switch_openvpn,
            "wireguard": self.switch_wireguard,
            "nordvpn": self.switch_nordvpn,
            "expressvpn": self.switch_expressvpn,
        }
        
        # Detect VPN client
        vpn_client = self.detect_vpn_client()
        
        if vpn_client in vpn_clients:
            return vpn_clients[vpn_client]()
        else:
            print(f"No VPN switching method for {vpn_client}")
            return False
    
    def detect_vpn_client(self):
        """Detect which VPN client is running"""
        try:
            import psutil
            
            vpn_processes = {
                "openvpn": "openvpn",
                "wireguard": "wireguard",
                "nordvpn": "nordvpn",
                "expressvpn": "expressvpn",
                "protonvpn": "protonvpn",
                "windscribe": "windscribe",
            }
            
            for proc in psutil.process_iter(['name']):
                for vpn_name, proc_name in vpn_processes.items():
                    if proc.info['name'] and proc_name in proc.info['name'].lower():
                        return vpn_name
        except ImportError:
            print("psutil not installed. Install with: pip install psutil")
        
        return "unknown"
    
    def switch_openvpn(self):
        """Switch OpenVPN connection"""
        try:
            # Kill current OpenVPN process
            subprocess.run(["pkill", "openvpn"], check=False)
            time.sleep(2)
            
            # Start with different config
            config_dir = Path("/etc/openvpn/configs/")
            configs = list(config_dir.glob("*.ovpn"))
            
            if configs:
                config = random.choice(configs)
                subprocess.Popen(["openvpn", "--config", str(config)], 
                               stdout=subprocess.DEVNULL, 
                               stderr=subprocess.DEVNULL)
                time.sleep(10)  # Wait for connection
                return True
        except:
            pass
        
        return False
    
    def switch_nordvpn(self):
        """Switch NordVPN server"""
        try:
            # Connect to random country
            countries = ["us", "ca", "uk", "de", "fr", "nl", "jp", "sg"]
            country = random.choice(countries)
            
            subprocess.run(["nordvpn", "disconnect"], check=False)
            time.sleep(2)
            subprocess.run(["nordvpn", "connect", country], check=True)
            time.sleep(5)
            
            return True
        except:
            return False
    
    # ========== COMBINED NETWORK METHODS ==========
    
    def get_network_config(self, strategy="auto"):
        """
        Get complete network configuration based on strategy
        
        Strategies:
        - auto: Automatically choose best available
        - tor: Use Tor only
        - proxy: Use proxies only
        - vpn: Use VPN only
        - hybrid: Combine multiple methods
        """
        
        config = {
            'proxy': None,
            'user_agent': self.ua.random,
            'method': 'direct'
        }
        
        if strategy == "auto":
            # Auto-select based on availability and performance
            if self.config["use_tor"] and self.tor_controller:
                config['proxy'] = self.get_tor_proxy()
                config['method'] = 'tor'
            elif self.config["use_proxies"] and self.proxy_list:
                config['proxy'] = self.get_random_proxy()
                config['method'] = 'proxy'
            elif self.config["use_vpn"] and self.vpn_interfaces:
                config['method'] = 'vpn'
        
        elif strategy == "tor":
            if self.config["use_tor"]:
                config['proxy'] = self.get_tor_proxy()
                config['method'] = 'tor'
        
        elif strategy == "proxy":
            if self.config["use_proxies"]:
                config['proxy'] = self.get_random_proxy()
                config['method'] = 'proxy'
        
        elif strategy == "vpn":
            if self.config["use_vpn"]:
                config['method'] = 'vpn'
        
        elif strategy == "hybrid":
            # Layer proxies over Tor
            if self.config["use_tor"]:
                config['proxy'] = self.get_tor_proxy()
                config['method'] = 'tor_proxy'
                # Note: This requires special setup
        
        self.current_user_agent = config['user_agent']
        return config
    
    def rotate_network(self):
        """Rotate to a new network identity"""
        rotation_methods = []
        
        if self.config["use_tor"] and self.tor_controller:
            if self.renew_tor_circuit():
                rotation_methods.append("Tor circuit")
        
        if self.config["use_proxies"] and len(self.proxy_list) > 1:
            old_proxy = self.current_proxy
            self.current_proxy = self.get_random_proxy()
            if old_proxy != self.current_proxy:
                rotation_methods.append(f"Proxy ({old_proxy} → {self.current_proxy})")
        
        if self.config["use_vpn"]:
            if self.switch_vpn_connection():
                rotation_methods.append("VPN connection")
        
        if rotation_methods:
            print(f"Network rotated using: {', '.join(rotation_methods)}")
            return True
        
        print("No network rotation performed")
        return False
    
    def get_current_ip(self):
        """Get current public IP address"""
        try:
            network_config = self.get_network_config()
            
            if network_config['proxy']:
                proxies = {
                    'http': network_config['proxy'],
                    'https': network_config['proxy']
                }
            else:
                proxies = None
            
            response = requests.get(
                "https://api.ipify.org?format=json",
                proxies=proxies,
                headers={'User-Agent': network_config['user_agent']},
                timeout=10
            )
            
            return {
                'ip': response.json()['ip'],
                'method': network_config['method'],
                'proxy': network_config['proxy']
            }
        
        except Exception as e:
            return {'ip': 'Unknown', 'error': str(e)}       
        
class EnhancedDownloader(Downloader):
    """Enhanced downloader with proxy/VPN/Tor support"""
    
    def __init__(self):
        super().__init__()
        self.network_manager = NetworkManager()
        self.download_stats = {
            'successful': 0,
            'failed': 0,
            'rate_limits': 0,
            'network_changes': 0,
            'start_time': time.time()
        }
        self.rotation_threshold = 5  # Rotate after X downloads
    
    def get_user_preferences(self):
        """Override to add network preference"""
        super().get_user_preferences()
        
        # Add network strategy preference
        print("\n=== Network Strategy ===")
        print("1. Auto (smart selection)")
        print("2. Tor only")
        print("3. Proxy only")
        print("4. VPN only (if available)")
        print("5. Hybrid (Tor + Proxy)")
        
        strategy_choice = input("Choose network strategy (1-5, default: 1): ").strip()
        
        strategies = {
            "1": "auto",
            "2": "tor",
            "3": "proxy",
            "4": "vpn",
            "5": "hybrid"
        }
        
        self.network_strategy = strategies.get(strategy_choice, "auto")
        print(f"Using network strategy: {self.network_strategy}")
    
    def run_download_with_network(self, url: str, output_dir: Path, network_strategy="auto"):
        """Run download with network configuration"""
        
        # Get network configuration
        network_config = self.network_manager.get_network_config(network_strategy)
        
        command = [
            "spotdl",
            "download",
            url,
            "--output", str(output_dir),
            "--overwrite", "skip",
            "--bitrate", self._Downloader__bitrate,  # Access private attribute
            "--format", self._Downloader__audio_format,
        ]
        
        # Add proxy if configured
        if network_config['proxy']:
            command.extend(["--proxy", network_config['proxy']])
        
        # Add user agent
        command.extend(["--user-agent", network_config['user_agent']])
        
        print(f"Network: {network_config['method']}")
        if network_config['proxy']:
            print(f"Proxy: {network_config['proxy']}")
        
        try:
            # Show current IP
            ip_info = self.network_manager.get_current_ip()
            print(f"Current IP: {ip_info.get('ip', 'Unknown')}")
            
            # Run download
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=DOWNLOAD_TIMEOUT,
                env=self._get_env_with_proxy(network_config['proxy'])
            )
            
            # Check for rate limits
            if result.stderr and ("rate limit" in result.stderr.lower() or "429" in result.stderr):
                self.download_stats['rate_limits'] += 1
                self.log_error(f"Rate limit detected for {url}")
                
                # Rotate network if we hit rate limit
                if self.download_stats['rate_limits'] % 2 == 0:
                    print("Rotating network due to rate limit...")
                    self.network_manager.rotate_network()
                    self.download_stats['network_changes'] += 1
            
            return result
            
        except subprocess.TimeoutExpired:
            self.log_error(f"Download timeout for {url}")
            return type('obj', (object,), {
                'returncode': 102,
                'stdout': '',
                'stderr': 'Download timeout'
            })()
        except Exception as e:
            self.log_error(f"Network error: {e}")
            return e
    
    def _get_env_with_proxy(self, proxy):
        """Get environment variables with proxy settings"""
        env = os.environ.copy()
        
        if proxy:
            # Set environment variables for yt-dlp/spotdl
            if proxy.startswith('http'):
                env['HTTP_PROXY'] = proxy
                env['HTTPS_PROXY'] = proxy
                env['http_proxy'] = proxy
                env['https_proxy'] = proxy
            elif proxy.startswith('socks'):
                env['SOCKS_PROXY'] = proxy
                env['socks_proxy'] = proxy
        
        return env
    
    def download_with_rotation(self, url: str, output_template: str, max_attempts=3):
        """Download with automatic network rotation"""
        
        for attempt in range(1, max_attempts + 1):
            print(f"\n{'='*60}")
            print(f"Download Attempt {attempt}/{max_attempts}")
            print(f"URL: {url}")
            print(f"{'='*60}")
            
            # Choose network strategy
            if attempt == 1:
                strategy = getattr(self, 'network_strategy', "auto")
            elif attempt == 2:
                strategy = "tor" if self.network_manager.config["use_tor"] else "proxy"
            else:
                strategy = "vpn" if self.network_manager.config["use_vpn"] else "tor"
            
            result = self.run_download_with_network(url, output_template, strategy)
            
            if isinstance(result, subprocess.CompletedProcess) and result.returncode == 0:
                self.download_stats['successful'] += 1
                return True
            
            # Check if we should rotate network
            if result and hasattr(result, 'stderr') and ("rate limit" in str(result.stderr).lower() or "429" in str(result.stderr)):
                print("Rate limit hit - rotating network...")
                self.network_manager.rotate_network()
                time.sleep(10)
            
            # Rotate network every X attempts
            if attempt % 2 == 0:
                self.network_manager.rotate_network()
            
            if attempt < max_attempts:
                wait_time = 30 * attempt  # Exponential backoff
                print(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        self.download_stats['failed'] += 1
        return False
    
    # Override the main download methods to use network rotation
    def download_track(self):
        """Override track download with network rotation"""
        print("\n =========== Single Track Download =================")
        url = input("Enter Spotify track url:- ").strip()
        
        if not url:
            print("No URL provided")
            return False
        
        # Get user preferences (includes network strategy)
        self.get_user_preferences()
        print("===========================================================================")
        print(f"Starting Track download: {url}. This may take a few minutes...")
        
        output_template = str(self._Downloader__output_dir / "{title}.{output-ext}")
        
        return self.download_with_rotation(url, output_template)
    
    def download_album(self):
        """Override album download with network rotation"""
        url = input("Enter Spotify Album url:- ").strip()
        
        if not url:
            print("No URL provided")
            return False
        
        # Get user preferences
        self.get_user_preferences()
        print("===========================================================================")
        print(f" ============== Starting Album download. This may take a few minutes")
        
        output_template = str(self._Downloader__output_dir / "{artist}/{album}/{title}.{output-ext}")
        
        return self.download_with_rotation(url, output_template)
    
    def download_playlist(self):
        """Override playlist download with network rotation"""
        url = input("Enter Spotify Playlist url:- ").strip()
        
        if not url:
            print("No URL provided")
            return False
        
        self.get_user_preferences()
        print("===========================================================================")
        print(f"============== Starting Playlist download. This may take a few minutes")
        
        output_template = str(self._Downloader__output_dir / "{playlist}/{title}.{output-ext}")
        
        return self.download_with_rotation(url, output_template)
    
    def show_network_status(self):
        """Display current network status"""
        print("\n" + "="*60)
        print("NETWORK STATUS")
        print("="*60)
        
        # Current IP
        ip_info = self.network_manager.get_current_ip()
        print(f"Current IP: {ip_info.get('ip', 'Unknown')}")
        print(f"Method: {ip_info.get('method', 'direct')}")
        
        # Proxy info
        if self.network_manager.current_proxy:
            print(f"Current Proxy: {self.network_manager.current_proxy}")
        
        # Tor info
        if self.network_manager.tor_controller:
            print(f"Tor Controller: Connected")
            self.network_manager.print_tor_info()
        
        # VPN info
        if self.network_manager.vpn_interfaces:
            print(f"VPN Interfaces: {', '.join(self.network_manager.vpn_interfaces)}")
        
        # Statistics
        print("\nDownload Statistics:")
        print(f"  Successful: {self.download_stats['successful']}")
        print(f"  Failed: {self.download_stats['failed']}")
        print(f"  Rate Limits: {self.download_stats['rate_limits']}")
        print(f"  Network Changes: {self.download_stats['network_changes']}")
        
        elapsed = time.time() - self.download_stats['start_time']
        print(f"  Runtime: {elapsed:.0f} seconds")
        print("="*60)
    
    def configure_network_settings(self):
        """Interactive network configuration"""
        print("\n" + "="*60)
        print("NETWORK CONFIGURATION")
        print("="*60)
        
        print("\n1. Enable/Disable Features:")
        self.network_manager.config["use_proxies"] = input("Use proxies? (y/n): ").lower() == 'y'
        self.network_manager.config["use_tor"] = input("Use Tor network? (y/n): ").lower() == 'y'
        self.network_manager.config["use_vpn"] = input("Use VPN? (y/n): ").lower() == 'y'
        
        if self.network_manager.config["use_tor"]:
            print("\n2. Tor Configuration:")
            port = input(f"Tor port [{self.network_manager.config['tor_port']}]: ")
            if port:
                self.network_manager.config["tor_port"] = int(port)
            
            control_port = input(f"Tor control port [{self.network_manager.config['tor_control_port']}]: ")
            if control_port:
                self.network_manager.config["tor_control_port"] = int(control_port)
            
            password = input("Tor control password (leave empty to skip): ")
            if password:
                self.network_manager.config["tor_password"] = password
        
        print("\n3. Proxy Configuration:")
        print("Add proxy sources (one per line, empty to finish):")
        sources = []
        while True:
            source = input("Source URL: ").strip()
            if not source:
                break
            sources.append(source)
        
        if sources:
            self.network_manager.config["proxy_sources"] = sources
        
        # Save configuration
        with open('network_config.json', 'w') as f:
            json.dump(self.network_manager.config, f, indent=2)
        
        print("\nConfiguration saved. Reinitializing network manager...")
        self.network_manager.setup_network_manager()
        
def display_enhanced_menu():
    """Display enhanced menu with network options"""
    menu = """
    ========================================================================
    ENHANCED SPOTIFY DOWNLOADER WITH PROXY/VPN/TOR SUPPORT
    ========================================================================
    Select an option:
    1.  Download Track
    2.  Download Album
    3.  Download Playlist
    4.  Download from Text File
    5.  Search and Download Song
    6.  Download User Playlists (Requires Spotify Account)
    7.  Download Liked Songs (Requires Spotify Account)
    8.  Download Saved Albums (Requires Spotify Account)
    
    === NETWORK OPTIONS ===
    9.  Show Network Status
    10. Configure Network Settings
    11. Rotate Network Now
    12. Test All Proxies
    
    === HELP OPTIONS ===
    13. Check/Install spotdl
    14. Show spotdl Help
    15. Show Program Info
    16. Exit
    ========================================================================
    """
    print(menu)

def enhanced_main():
    """Main function with network support"""
    print("="*80)
    print("Enhanced Spotify Downloader with Proxy/VPN/Tor Support")
    print("="*80)
    
    # Check dependencies
    print("Checking dependencies...")
    try:
        import stem
        import fake_useragent
        print("✓ Stem and fake-useragent found")
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        install = input("Install missing dependencies? (y/n): ").lower()
        if install == 'y':
            subprocess.run([sys.executable, "-m", "pip", "install", "stem", "fake-useragent"])
    
    # Initialize enhanced downloader
    downloader = EnhancedDownloader()
    
    while True:
        display_enhanced_menu()
        choice = input("\nEnter your choice (1-16): ").strip()
        
        actions = {
            "1": downloader.download_track,
            "2": downloader.download_album,
            "3": downloader.download_playlist,
            "4": downloader.download_from_file,
            "5": downloader.search_a_song,
            "6": downloader.download_user_playlist,
            "7": downloader.download_user_liked_songs,
            "8": downloader.download_user_saved_albums,
            "9": downloader.show_network_status,
            "10": downloader.configure_network_settings,
            "11": lambda: downloader.network_manager.rotate_network(),
            "12": lambda: downloader.network_manager.load_proxies(),
            "13": downloader.check_spotdl,
            "14": Downloader.show_spotdl_help,
            "15": Downloader.program_info,
        }
        
        if choice == "16":
            print("\nThank you for using Enhanced Spotify Downloader. Goodbye!")
            break
        
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Invalid choice. Please enter a number between 1 and 16.")
            continue

if __name__ == "__main__":
    enhanced_main()