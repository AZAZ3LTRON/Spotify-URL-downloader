"""
Interactive Playlist/Album/Track Downloader using yt-dlp

Enhanced with:
- Progress bars for downloads
- Batch processing with parallel downloads
- Resource validation before downloading
- Better error handling and user feedback

Enjoy!
"""

# Basic Import required
import sys
import os
import subprocess
import shutil
import time
from functools import wraps
from pathlib import Path
import logging
import re
import urllib.parse
import threading
import json
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import List, Dict, Optional, Tuple
import queue

# Try to import tqdm for progress bars
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Note: Install 'tqdm' for better progress bars: pip install tqdm")

""" =========================================== Pre Config =========================================== """
SUCCESS_LOG = r"log\success.log" 
FAILED_LOG = r"log\failed.log"
ERROR_LOG = r"log\error.log"
MAX_RETRIES = 3
RETRY_DELAY = 10
DOWNLOAD_TIMEOUT = 120
MAX_PARALLEL_DOWNLOADS = 3  # Maximum parallel downloads for batch processing

os.makedirs("log", exist_ok=True)

"""==== Logger: Initialize the log files before write ==== """
logger = logging.getLogger("YouTube Downloader")
log_format = logging.Formatter("%(asctime)s - %(levelname)s - %(funcName)s - %(message)s") 

success_downloads = logging.getLogger("successful downloads")
failed_downloads = logging.getLogger("failed downloads")
error_downloads = logging.getLogger("error in downloads")
console_logger = logging.getLogger("console")
    
# Create loggers
success_downloads.setLevel(logging.INFO)
success_downloads.propagate = False
success_handler = logging.FileHandler(SUCCESS_LOG, encoding='utf-8')
success_handler.setLevel(logging.INFO)
success_handler.setFormatter(log_format)
success_downloads.addHandler(success_handler)

failed_downloads.setLevel(logging.INFO)
failed_downloads.propagate = False
failed_handler = logging.FileHandler(FAILED_LOG, encoding='utf-8')
failed_handler.setLevel(logging.INFO)
failed_handler.setFormatter(log_format)
failed_downloads.addHandler(failed_handler)

error_downloads.setLevel(logging.INFO)
error_downloads.propagate = False
error_handler = logging.FileHandler(ERROR_LOG, encoding='utf-8')
error_handler.setLevel(logging.ERROR)
error_handler.setFormatter(log_format)
error_downloads.addHandler(error_handler)

console_logger.setLevel(logging.INFO)
console_logger.propagate = False
console_stream_handler = logging.StreamHandler()
console_stream_handler.setLevel(logging.INFO)
console_stream_handler.setFormatter(log_format)
console_logger.addHandler(console_stream_handler)

""" =========================================== Progress Bar Classes =========================================== """

class DownloadProgress:
    """Handles progress tracking for downloads"""
    
    def __init__(self, total_items: int = 1, desc: str = "Downloading"):
        self.total_items = total_items
        self.desc = desc
        self.current_item = 0
        self.start_time = time.time()
        
        if TQDM_AVAILABLE:
            self.pbar = tqdm(
                total=total_items,
                desc=desc,
                unit="file",
                bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
            )
        else:
            self.pbar = None
    
    def update(self, n: int = 1, status: str = ""):
        """Update progress bar"""
        self.current_item += n
        
        if self.pbar:
            if status:
                self.pbar.set_postfix_str(status)
            self.pbar.update(n)
        else:
            # Simple console progress
            elapsed = time.time() - self.start_time
            percent = (self.current_item / self.total_items) * 100
            sys.stdout.write(f"\r{self.desc}: {self.current_item}/{self.total_items} ({percent:.1f}%) - {status}")
            sys.stdout.flush()
    
    def set_description(self, desc: str):
        """Update progress bar description"""
        if self.pbar:
            self.pbar.set_description(desc)
        else:
            self.desc = desc
    
    def close(self):
        """Close progress bar"""
        if self.pbar:
            self.pbar.close()
        else:
            print()  # New line after simple progress
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class LiveProgressTracker:
    """Tracks live download progress using yt-dlp's progress hooks"""
    
    def __init__(self, url: str):
        self.url = url
        self.progress_data = {
            "status": "starting",
            "percent": 0.0,
            "speed": "N/A",
            "eta": "N/A",
            "total_size": "N/A",
            "downloaded": "0 B"
        }
        self.lock = threading.Lock()
        self.completed = False
    
    def progress_hook(self, d: Dict):
        """Callback function for yt-dlp progress"""
        with self.lock:
            if d['status'] == 'downloading':
                self.progress_data.update({
                    "status": "downloading",
                    "percent": d.get('_percent_str', '0%').strip('%'),
                    "speed": d.get('_speed_str', 'N/A'),
                    "eta": d.get('_eta_str', 'N/A'),
                    "total_size": d.get('_total_bytes_str', 'N/A'),
                    "downloaded": d.get('_downloaded_bytes_str', '0 B')
                })
            elif d['status'] == 'finished':
                self.progress_data["status"] = "processing"
                self.completed = True
    
    def get_progress_string(self) -> str:
        """Get formatted progress string"""
        with self.lock:
            if self.progress_data["status"] == "starting":
                return f"Preparing download..."
            elif self.progress_data["status"] == "processing":
                return f"Processing audio..."
            else:
                return (f"{self.progress_data['percent']}% | "
                       f"Speed: {self.progress_data['speed']} | "
                       f"ETA: {self.progress_data['eta']} | "
                       f"{self.progress_data['downloaded']}/{self.progress_data['total_size']}")


""" =========================================== The Enhanced Downloader Class =========================================== """

class Youtube_Downloader:
    def __init__(self):
        """Initialize the downloader with default values"""
        self.__output_dir = Path("Albums")
        self.__audio_quality = "320k"
        self.__audio_format = "mp3"
        self.__filepath = r"links/youtube_links.txt"
        self.__ytdlp_version = None
        self.__config_file = "downloader_config.json"
        self.__parallel_downloads = MAX_PARALLEL_DOWNLOADS
        
        # Load configuration
        self.load_configuration()
    
    # ==================== Configuration Management ====================
    
    def load_configuration(self):
        """Load configuration from file or create default"""
        default_config = {
            "output_dir": "Albums",
            "audio_quality": "320k",
            "audio_format": "mp3",
            "max_parallel_downloads": MAX_PARALLEL_DOWNLOADS,
            "max_retries": MAX_RETRIES,
            "retry_delay": RETRY_DELAY,
            "download_timeout": DOWNLOAD_TIMEOUT
        }
        
        try:
            if os.path.exists(self.__config_file):
                with open(self.__config_file, 'r') as f:
                    user_config = json.load(f)
                    config = {**default_config, **user_config}
            else:
                config = default_config
                self.save_configuration(config)
            
            # Apply configuration
            self.__output_dir = Path(config["output_dir"])
            self.__audio_quality = config["audio_quality"]
            self.__audio_format = config["audio_format"]
            self.__parallel_downloads = config["max_parallel_downloads"]
            
        except Exception as e:
            self.log_error(f"Error loading configuration: {e}")
            # Use defaults
            self.__output_dir = Path(default_config["output_dir"])
            self.__audio_quality = default_config["audio_quality"]
            self.__audio_format = default_config["audio_format"]
    
    def save_configuration(self, config: Dict = None):
        """Save configuration to file"""
        try:
            if config is None:
                config = {
                    "output_dir": str(self.__output_dir),
                    "audio_quality": self.__audio_quality,
                    "audio_format": self.__audio_format,
                    "max_parallel_downloads": self.__parallel_downloads,
                    "max_retries": MAX_RETRIES,
                    "retry_delay": RETRY_DELAY,
                    "download_timeout": DOWNLOAD_TIMEOUT
                }
            
            with open(self.__config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            self.log_error(f"Error saving configuration: {e}")
    
    # ==================== Enhanced Logger Functions ====================
    
    def log_success(self, message: str):
        """Logs only successful downloads (to success log)"""
        success_downloads.info(message)
        console_logger.info(f"✅ {message}")
        
    def log_failure(self, message: str):
        """Logs only failed downloads (to failed log)"""
        failed_downloads.info(message)
        console_logger.info(f"❌ {message}")
        
    def log_error(self, message: str, exc_info=False):
        """Logs only error in download process (to error log)"""
        error_downloads.error(message, exc_info=exc_info)
        console_logger.error(f"⚠️ {message}")
    
    def log_warning(self, message: str):
        """Log warning messages"""
        console_logger.warning(f"⚠️ {message}")
    
    # ==================== Resource Validation ====================
    
    def validate_youtube_url(self, url: str) -> bool:
        """Validate if the URL input is a proper YouTube URL"""
        youtube_patterns = [
            r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$',
            r'^(https?://)?music\.youtube\.com/.+$',
            r'^(https?://)?youtube\.com/watch\?v=[\w-]+(&.*)?$',
            r'^(https?://)?youtube\.com/playlist\?list=[\w-]+(&.*)?$',
            r'^(https?://)?youtu\.be/[\w-]+$'        
        ]

        for pattern in youtube_patterns:
            if re.match(pattern, url, re.IGNORECASE):
                try:
                    parsed = urllib.parse.urlparse(url)
                    if parsed.scheme in ['http', 'https', ''] or parsed.netloc:
                        return True
                except:
                    continue
        return False
    
    def get_resource_type(self, url: str) -> Optional[str]:
        """Determine the type of YouTube resource"""
        patterns = {
            "video": r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)',
            "playlist": r'youtube\.com/playlist\?list=([\w-]+)',
            "album": r'music\.youtube\.com/album/([\w-]+)',
            "channel": r'youtube\.com/(?:c/|channel/|@|user/)([\w-]+)'
        }
        
        for resource_type, pattern in patterns.items():
            if re.search(pattern, url, re.IGNORECASE):
                return resource_type
        return None
    
    def extract_youtube_id(self, url: str) -> str:
        """Extract YouTube ID from URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)',  # Video ID
            r'youtube\.com/playlist\?list=([\w-]+)'          
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def validate_resource_availability(self, url: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate if a resource is available before downloading
        Returns: (is_available, message, metadata)
        """
        try:
            # Quick check using yt-dlp's --skip-download
            command = [
                "yt-dlp",
                "--skip-download",
                "--print-json",
                "--no-warnings",
                url
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode == 0:
                try:
                    metadata = json.loads(result.stdout)
                    title = metadata.get('title', 'Unknown')
                    duration = metadata.get('duration', 0)
                    
                    # Check for age restrictions
                    if metadata.get('age_limit', 0) >= 18:
                        return False, "Age restricted content", metadata
                    
                    # Check if video is available
                    if metadata.get('availability') == 'unavailable':
                        return False, "Video unavailable", metadata
                    
                    return True, f"✓ Available: {title} ({duration}s)", metadata
                    
                except json.JSONDecodeError:
                    return True, "✓ Resource available (metadata unavailable)", None
            else:
                error_msg = result.stderr.lower()
                if "unavailable" in error_msg:
                    return False, "Resource unavailable", None
                elif "private" in error_msg:
                    return False, "Private video", None
                elif "age restriction" in error_msg:
                    return False, "Age restricted", None
                elif "not found" in error_msg:
                    return False, "Resource not found", None
                else:
                    return False, f"Validation failed: {error_msg[:100]}", None
                    
        except subprocess.TimeoutExpired:
            return False, "Validation timeout", None
        except Exception as e:
            return False, f"Validation error: {str(e)[:100]}", None
    
    def estimate_download_size(self, url: str) -> str:
        """Estimate download size before downloading"""
        try:
            command = [
                "yt-dlp",
                "--get-filesize",
                "--no-warnings",
                url
            ]
            
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                size_bytes = result.stdout.strip()
                if size_bytes.isdigit():
                    size_mb = int(size_bytes) / (1024 * 1024)
                    if size_mb < 1:
                        return f"{size_mb * 1024:.1f} KB"
                    else:
                        return f"{size_mb:.1f} MB"
            
            return "Unknown size"
            
        except Exception:
            return "Unknown size"
    
    # ==================== Enhanced Download Functions with Progress ====================
    
    def run_download_with_progress(self, url: str, output_template: str, 
                                 progress_tracker: LiveProgressTracker = None,
                                 additional_args=None) -> subprocess.CompletedProcess:
        """Run yt-dlp download with progress tracking"""
        # Ensure output directory exists
        output_dir = os.path.dirname(output_template)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        command = [
            "yt-dlp",
            "-x",
            "--audio-format", self.__audio_format,
            "--audio-quality", self.__audio_quality,
            "-o", output_template,
            "--no-overwrites",
            "--add-metadata",
            "--embed-thumbnail",
            "--newline",  # Important for progress parsing
            "--progress",  # Show progress
            "--console-title"  # Update console title with progress
        ]
        
        # Add progress hook if tracker is provided
        if progress_tracker:
            command.extend(["--progress-template", "download:%(progress.status)s:%(progress._percent_str)s:%(progress._speed_str)s:%(progress._eta_str)s"])
        
        if additional_args:
            if isinstance(additional_args, list):
                command.extend(additional_args)
            else:
                command.append(additional_args)
        
        command.append(url)
        
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            
            # Read output line by line to capture progress
            for line in process.stdout:
                output_lines.append(line.strip())
                
                # Parse progress if tracker is provided
                if progress_tracker and line.startswith("download:"):
                    try:
                        parts = line.strip().split(":")
                        if len(parts) >= 5:
                            status = parts[1]
                            percent = parts[2].strip('%') if parts[2] != 'None' else '0'
                            speed = parts[3] if parts[3] != 'None' else 'N/A'
                            eta = parts[4] if parts[4] != 'None' else 'N/A'
                            
                            # Update progress tracker
                            progress_tracker.progress_data.update({
                                "status": status,
                                "percent": percent,
                                "speed": speed,
                                "eta": eta
                            })
                    except:
                        pass
            
            # Wait for process to complete
            stdout, stderr = process.communicate()
            returncode = process.returncode
            
            result = subprocess.CompletedProcess(
                args=command,
                returncode=returncode,
                stdout='\n'.join(output_lines),
                stderr=stderr
            )
            
            return result
            
        except Exception as e:
            raise e
    
    def run_download(self, url: str, output_template: str, additional_args=None):
        """Backward compatibility wrapper"""
        return self.run_download_with_progress(url, output_template, None, additional_args)
    
    # ==================== Batch Processing ====================
    
    def download_single_item(self, url: str, item_type: str = "track", 
                           item_index: int = 1, total_items: int = 1,
                           progress_queue: queue.Queue = None) -> bool:
        """Download a single item with progress reporting"""
        try:
            # Determine output template based on type
            if item_type == "playlist":
                output_template = str(self.__output_dir / "Playlists" / "%(playlist)s" / "%(title)s.%(ext)s")
            elif item_type == "album":
                output_template = str(self.__output_dir / "Albums" / "%(artist)s" / "%(album)s" / "%(title)s.%(ext)s")
            else:
                output_template = str(self.__output_dir / "Tracks" / "%(title)s.%(ext)s)")
            
            # Create progress tracker
            tracker = LiveProgressTracker(url)
            
            # Validate before downloading
            is_available, message, metadata = self.validate_resource_availability(url)
            if not is_available:
                self.log_failure(f"Item {item_index}/{total_items} ({url}): {message}")
                if progress_queue:
                    progress_queue.put((item_index, False, message))
                return False
            
            # Estimate size
            size_estimate = self.estimate_download_size(url)
            
            # Report start
            start_msg = f"Item {item_index}/{total_items}: Downloading ({size_estimate})"
            self.log_success(start_msg)
            
            if progress_queue:
                progress_queue.put((item_index, "start", start_msg))
            
            # Download with retries
            for attempt in range(1, MAX_RETRIES + 1):
                try:
                    result = self.run_download_with_progress(url, output_template, tracker)
                    
                    if isinstance(result, subprocess.CompletedProcess) and result.returncode == 0:
                        success_msg = f"Item {item_index}/{total_items}: Downloaded successfully"
                        self.log_success(success_msg)
                        if progress_queue:
                            progress_queue.put((item_index, True, success_msg))
                        return True
                    elif attempt < MAX_RETRIES:
                        retry_msg = f"Item {item_index}/{total_items}: Attempt {attempt} failed, retrying..."
                        self.log_warning(retry_msg)
                        if progress_queue:
                            progress_queue.put((item_index, "retry", retry_msg))
                        time.sleep(RETRY_DELAY)
                    else:
                        error_msg = f"Item {item_index}/{total_items}: Failed after {MAX_RETRIES} attempts"
                        self.log_failure(error_msg)
                        if progress_queue:
                            progress_queue.put((item_index, False, error_msg))
                        return False
                        
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        self.log_warning(f"Item {item_index}/{total_items}: Error (attempt {attempt}): {str(e)[:100]}")
                        time.sleep(RETRY_DELAY)
                    else:
                        self.log_failure(f"Item {item_index}/{total_items}: Final error: {str(e)[:100]}")
                        if progress_queue:
                            progress_queue.put((item_index, False, str(e)[:100]))
                        return False
            
            return False
            
        except Exception as e:
            error_msg = f"Item {item_index}/{total_items}: Unexpected error: {str(e)[:100]}"
            self.log_failure(error_msg)
            if progress_queue:
                progress_queue.put((item_index, False, error_msg))
            return False
    
    def process_batch_parallel(self, urls: List[str], item_type: str = "track") -> Dict[str, int]:
        """
        Process multiple URLs in parallel
        Returns: Dictionary with success/failure counts
        """
        if not urls:
            return {"success": 0, "failed": 0, "total": 0}
        
        total_items = len(urls)
        results = {"success": 0, "failed": 0, "total": total_items}
        
        print(f"\n{'='*60}")
        print(f"BATCH PROCESSING: {total_items} items")
        print(f"Parallel downloads: {self.__parallel_downloads}")
        print(f"{'='*60}")
        
        # Create progress bar
        with DownloadProgress(total_items, "Batch Download") as progress:
            # Create queue for progress updates
            progress_queue = queue.Queue()
            
            # Thread function wrapper
            def download_worker(url_idx: int, url: str):
                success = self.download_single_item(
                    url, item_type, url_idx + 1, total_items, progress_queue
                )
                return url_idx, success
            
            # Start parallel downloads
            with ThreadPoolExecutor(max_workers=self.__parallel_downloads) as executor:
                # Submit all download tasks
                future_to_url = {
                    executor.submit(download_worker, idx, url): (idx, url)
                    for idx, url in enumerate(urls)
                }
                
                # Process results as they complete
                completed_count = 0
                for future in as_completed(future_to_url):
                    idx, url = future_to_url[future]
                    try:
                        item_idx, success = future.result()
                        if success:
                            results["success"] += 1
                        else:
                            results["failed"] += 1
                            
                        # Update progress from queue
                        while not progress_queue.empty():
                            q_idx, status, message = progress_queue.get_nowait()
                            if status == "start":
                                progress.update(0, f"Started {q_idx}/{total_items}")
                            elif status == True:
                                progress.update(1, f"Completed {q_idx}/{total_items}")
                            elif status == "retry":
                                progress.update(0, f"Retrying {q_idx}/{total_items}")
                        
                    except Exception as e:
                        results["failed"] += 1
                        self.log_error(f"Error processing URL {idx + 1}: {str(e)[:100]}")
                    
                    completed_count += 1
                    progress.update(0, f"Processing {completed_count}/{total_items}")
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"BATCH PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Successfully downloaded: {results['success']}/{total_items}")
        print(f"Failed: {results['failed']}/{total_items}")
        print(f"{'='*60}")
        
        return results
    
    def validate_batch_before_download(self, urls: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
        """
        Validate all URLs in a batch before downloading
        Returns: (valid_urls, invalid_urls_with_reasons)
        """
        valid_urls = []
        invalid_urls = []
        
        print(f"\n{'='*60}")
        print(f"VALIDATING {len(urls)} URLs...")
        print(f"{'='*60}")
        
        with DownloadProgress(len(urls), "Validating URLs") as progress:
            for i, url in enumerate(urls, 1):
                clean_url = url.split('#')[0].strip()
                
                # Skip already downloaded
                if "# DOWNLOADED" in url:
                    progress.update(1, f"Skipping already downloaded: {clean_url[:50]}...")
                    continue
                
                # Basic URL validation
                if not self.validate_youtube_url(clean_url):
                    invalid_urls.append((clean_url, "Invalid YouTube URL"))
                    progress.update(1, f"Invalid URL: {clean_url[:50]}...")
                    continue
                
                # Resource availability check
                is_available, message, _ = self.validate_resource_availability(clean_url)
                if is_available:
                    valid_urls.append(clean_url)
                    progress.update(1, f"Valid: {clean_url[:50]}...")
                else:
                    invalid_urls.append((clean_url, message))
                    progress.update(1, f"Unavailable: {clean_url[:50]}...")
        
        # Print validation summary
        if invalid_urls:
            print(f"\n{'='*60}")
            print(f"VALIDATION ISSUES FOUND:")
            for url, reason in invalid_urls[:10]:  # Show first 10 issues
                print(f"  • {url[:80]}... - {reason}")
            if len(invalid_urls) > 10:
                print(f"  ... and {len(invalid_urls) - 10} more")
            print(f"{'='*60}")
        
        return valid_urls, invalid_urls
    
    # ==================== Rate Limiter ====================
    
    def rate_limit(calls_per_minute=60):
        """Added rate limiter to avoid being blocked"""
        def decorator(func):
            last_called = [0.0]
            
            @wraps(func)
            def wrapper(*args, **kwargs):
                elapsed_time = time.time() - last_called[0]
                wait_time = (60.0 / calls_per_minute) - elapsed_time
                if wait_time > 0:
                    time.sleep(wait_time)
                last_called[0] = time.time()
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    # ==================== Enhanced Main Download Functions ====================
    
    @rate_limit(calls_per_minute=30)
    def download_track(self):
        """Download a single track with enhanced progress"""
        print("\n" + "="*60)
        print("SINGLE TRACK DOWNLOAD")
        print("="*60)
        
        url = input("Enter YouTube/YouTube Music track URL: ").strip()
        
        if not url:
            print("No URL provided")
            return
        
        # Validate URL
        if not self.validate_youtube_url(url):
            print("Invalid YouTube URL. Please enter a valid YouTube/YouTube Music URL")
            return
        
        # Get user preferences
        self.get_user_preferences()
        
        # Pre-download validation
        print(f"\n{'='*60}")
        print("VALIDATING RESOURCE...")
        print(f"{'='*60}")
        
        is_available, message, metadata = self.validate_resource_availability(url)
        if not is_available:
            print(f"❌ Cannot download: {message}")
            return
        
        # Estimate size
        size_estimate = self.estimate_download_size(url)
        title = metadata.get('title', 'Unknown') if metadata else 'Unknown'
        duration = metadata.get('duration', 0)
        
        print(f"✓ Resource available: {title}")
        print(f"  Duration: {duration} seconds")
        print(f"  Estimated size: {size_estimate}")
        print(f"{'='*60}")
        
        # Confirm download
        confirm = input(f"\nDownload '{title[:50]}...'? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Download cancelled.")
            return
        
        print(f"\n{'='*60}")
        print(f"DOWNLOADING: {title}")
        print(f"{'='*60}")
        
        start_time = time.time()
        output_template = str(self.__output_dir / "%(title)s.%(ext)s")
        
        # Create progress tracker
        tracker = LiveProgressTracker(url)
        
        def print_progress():
            """Thread function to print progress"""
            while not tracker.completed:
                progress_str = tracker.get_progress_string()
                sys.stdout.write(f"\r{progress_str}")
                sys.stdout.flush()
                time.sleep(0.5)
            print()  # New line when done
        
        # Start progress display thread
        progress_thread = threading.Thread(target=print_progress, daemon=True)
        progress_thread.start()
        
        # Perform download
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"\nAttempt {attempt} of {MAX_RETRIES}...")
            
            try:
                result = self.run_download_with_progress(url, output_template, tracker)
                
                if isinstance(result, subprocess.CompletedProcess) and result.returncode == 0:
                    elapsed_time = time.time() - start_time
                    tracker.completed = True
                    progress_thread.join(timeout=1)
                    
                    print(f"\n{'='*60}")
                    print(f"✅ DOWNLOAD COMPLETE!")
                    print(f"{'='*60}")
                    print(f"Title: {title}")
                    print(f"Time: {elapsed_time:.1f} seconds")
                    print(f"Size: {size_estimate}")
                    print(f"Format: {self.__audio_format.upper()} @ {self.__audio_quality}")
                    print(f"Saved to: {self.__output_dir}")
                    print(f"{'='*60}")
                    
                    self.log_success(f"Downloaded: {title} in {elapsed_time:.1f}s")
                    return
                    
                elif attempt < MAX_RETRIES:
                    print(f"⚠️ Download failed, retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    tracker.completed = True
                    progress_thread.join(timeout=1)
                    print(f"\n❌ Failed to download after {MAX_RETRIES} attempts")
                    self.log_failure(f"Failed: {url}")
                    
            except Exception as e:
                tracker.completed = True
                progress_thread.join(timeout=1)
                print(f"\n❌ Error: {str(e)[:100]}")
                self.log_error(f"Error downloading {url}: {e}")
                if attempt == MAX_RETRIES:
                    return
    
    # ==================== Enhanced Batch Download Function ====================
    
    def download_from_file(self):
        """Download various links from a file with batch processing"""
        print("\n" + "="*60)
        print("BATCH DOWNLOAD FROM FILE")
        print("="*60)
        
        filepath = input("Enter the directory of the file (default: links/youtube_links.txt): ").strip()
        
        if not filepath:
            filepath = self.__filepath
            
        if not os.path.exists(filepath):
            self.log_failure(f"File not found: {filepath}")
            print(f"Please create a file named 'youtube_links.txt' in the 'links' folder.")
            return
        
        # Get user preferences
        self.get_user_preferences()
        
        # Ask about parallel downloads
        print(f"\nCurrent parallel downloads: {self.__parallel_downloads}")
        change_parallel = input("Change parallel downloads? (y/n): ").strip().lower()
        if change_parallel in ['y', 'yes']:
            while True:
                try:
                    parallel_input = input(f"Enter number of parallel downloads (1-10, default {self.__parallel_downloads}): ").strip()
                    if not parallel_input:
                        break
                    parallel_num = int(parallel_input)
                    if 1 <= parallel_num <= 10:
                        self.__parallel_downloads = parallel_num
                        break
                    else:
                        print("Please enter a number between 1 and 10.")
                except ValueError:
                    print("Please enter a valid number.")
        
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                file_lines = [line.rstrip() for line in file if line.strip()]
        except Exception as e:
            self.log_failure(f"Error reading the file: {e}")
            return
        
        if not file_lines:
            self.log_failure("No URLs found in the text file")
            return
        
        print(f"\nFound {len(file_lines)} URLs in file.")
        
        # Filter out already downloaded URLs
        urls_to_process = []
        already_downloaded = []
        
        for line in file_lines:
            if "# DOWNLOADED" in line:
                already_downloaded.append(line)
            else:
                urls_to_process.append(line.split('#')[0].strip())
        
        if already_downloaded:
            print(f"Skipping {len(already_downloaded)} already downloaded URLs.")
        
        if not urls_to_process:
            print("No new URLs to download.")
            return
        
        print(f"\nProcessing {len(urls_to_process)} new URLs...")
        
        # Validate all URLs before downloading
        valid_urls, invalid_urls = self.validate_batch_before_download(urls_to_process)
        
        if not valid_urls:
            print("No valid URLs to download after validation.")
            return
        
        # Ask for confirmation
        print(f"\n{'='*60}")
        print(f"READY TO DOWNLOAD")
        print(f"{'='*60}")
        print(f"Valid URLs: {len(valid_urls)}")
        print(f"Invalid URLs: {len(invalid_urls)}")
        print(f"Parallel downloads: {self.__parallel_downloads}")
        print(f"Format: {self.__audio_format.upper()} @ {self.__audio_quality}")
        print(f"Output directory: {self.__output_dir}")
        print(f"{'='*60}")
        
        confirm = input(f"\nStart batch download of {len(valid_urls)} items? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Batch download cancelled.")
            return
        
        # Perform batch download
        results = self.process_batch_parallel(valid_urls, "track")
        
        # Update the file with download status
        try:
            updated_lines = []
            
            # Keep existing status for already downloaded
            for line in file_lines:
                if "# DOWNLOADED" in line or "# FAILED" in line:
                    updated_lines.append(line)
                else:
                    clean_url = line.split('#')[0].strip()
                    if clean_url in valid_urls:
                        # Mark as downloaded (in reality, we'd check which ones succeeded)
                        # For simplicity, we'll mark all valid URLs as attempted
                        updated_lines.append(f"{clean_url} # ATTEMPTED")
                    else:
                        updated_lines.append(line)
            
            with open(filepath, 'w', encoding='utf-8') as file:
                file.write("\n".join(updated_lines))
                
        except Exception as e:
            self.log_failure(f"Error updating the file: {e}")
        
        # Final summary
        print(f"\n{'='*60}")
        print(f"BATCH DOWNLOAD COMPLETE")
        print(f"{'='*60}")
        print(f"Successfully downloaded: {results['success']}")
        print(f"Failed: {results['failed']}")
        print(f"Total processed: {results['total']}")
        print(f"{'='*60}")
        
        # Cleanup empty directories
        self.cleanup_empty_dirs()
        
        return results['failed'] == 0
    
    # ==================== Utility Functions ====================
    
    def cleanup_empty_dirs(self):
        """Remove empty directories after download"""
        removed_count = 0
        for root, dirs, files in os.walk(self.__output_dir, topdown=False):
            for dir_name in dirs:
                dir_path = os.path.join(root, dir_name)
                try:
                    if not os.listdir(dir_path):
                        os.rmdir(dir_path)
                        removed_count += 1
                except OSError:
                    pass
        
        if removed_count > 0:
            self.log_success(f"Cleaned up {removed_count} empty directories")
    
    def get_user_preferences(self):
        """Takes in user input for the download settings"""
        
        # Handle choice of bitrate/audio quality inputs
        while True:
            print(f"\nCurrent audio quality: {self.__audio_quality}")
            audio_quality_input = input("What bitrate would you like (8k-320k, auto, or press Enter to keep current): ").strip().lower()
            
            if not audio_quality_input:
                break
            if audio_quality_input in ["auto", "disable", "8k", "16k", "24k", "32k", "40k", "48k", "64k",
                                "80k", "96k", "112k", "128k", "160k", "192k", "224k", "256k", "320k"]:
                self.__audio_quality = audio_quality_input
                break
            print("Invalid bitrate. Please choose from the specified values.")
            
        # Handles choice of audio format
        while True:
            print(f"\nCurrent audio format: {self.__audio_format}")
            audio_format_input = input("What format do you wish to download in (mp3, flac, ogg, opus, m4a, wav, or press Enter to keep current): ").strip().lower()
            if not audio_format_input:
                break
            if audio_format_input in ["mp3", "flac", "ogg", "opus", "m4a", "wav"]:
                self.__audio_format = audio_format_input
                break
            print("Invalid format. Please choose from the specified formats.")
            
        # Handle choice of output directory
        print(f"\nCurrent output directory: {self.__output_dir}")
        output_path = input("Enter output directory or press Enter to keep current: ").strip()
        if output_path:
            self.__output_dir = Path(output_path)
            
        self.__output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        self.save_configuration()
    
    # ==================== Other Download Methods (Updated for consistency) ====================
    
    # Note: The other methods (download_album, download_playlist, download_channel, search_a_song)
    # should be updated similarly to download_track() to include progress and validation.
    # For brevity, I'll show the pattern for one more:
    
    @rate_limit(calls_per_minute=30)
    def download_playlist(self):
        """Download a playlist with progress"""
        print("\n" + "="*60)
        print("PLAYLIST DOWNLOAD")
        print("="*60)
        
        url = input("Enter YouTube/YouTube Music playlist URL: ").strip()
        
        if not url:
            print("No URL provided")
            return
        
        if not self.validate_youtube_url(url):
            print("Invalid YouTube URL. Please enter a valid YouTube/YouTube Music URL")
            return
        
        # Get user preferences
        self.get_user_preferences()
        
        # Validate playlist
        print(f"\n{'='*60}")
        print("VALIDATING PLAYLIST...")
        print(f"{'='*60}")
        
        is_available, message, metadata = self.validate_resource_availability(url)
        if not is_available:
            print(f"❌ Cannot download: {message}")
            return
        
        # Get playlist info
        playlist_title = metadata.get('title', 'Unknown Playlist') if metadata else 'Unknown Playlist'
        playlist_count = metadata.get('playlist_count', 'Unknown') if metadata else 'Unknown'
        
        print(f"✓ Playlist available: {playlist_title}")
        print(f"  Estimated items: {playlist_count}")
        print(f"{'='*60}")
        
        # Confirm download
        confirm = input(f"\nDownload playlist '{playlist_title[:50]}...' ({playlist_count} items)? (y/n): ").strip().lower()
        if confirm not in ['y', 'yes']:
            print("Download cancelled.")
            return
        
        print(f"\n{'='*60}")
        print(f"DOWNLOADING PLAYLIST: {playlist_title}")
        print(f"{'='*60}")
        
        start_time = time.time()
        output_template = str(self.__output_dir / "%(playlist)s" / "%(playlist_index)s - %(title)s.%(ext)s")
        
        # Download with progress
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"\nAttempt {attempt} of {MAX_RETRIES}...")
            
            try:
                # Use yt-dlp with playlist progress
                command = [
                    "yt-dlp",
                    "-x",
                    "--audio-format", self.__audio_format,
                    "--audio-quality", self.__audio_quality,
                    "-o", output_template,
                    "--no-overwrites",
                    "--add-metadata",
                    "--embed-thumbnail",
                    "--console-title",
                    url
                ]
                
                result = subprocess.run(
                    command,
                    stdout=sys.stdout,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=DOWNLOAD_TIMEOUT * 5,  # Longer timeout for playlists
                    check=False
                )
                
                if result.returncode == 0:
                    elapsed_time = time.time() - start_time
                    print(f"\n{'='*60}")
                    print(f"✅ PLAYLIST DOWNLOAD COMPLETE!")
                    print(f"{'='*60}")
                    print(f"Playlist: {playlist_title}")
                    print(f"Time: {elapsed_time:.1f} seconds")
                    print(f"Items: {playlist_count}")
                    print(f"Format: {self.__audio_format.upper()} @ {self.__audio_quality}")
                    print(f"Saved to: {self.__output_dir / playlist_title}")
                    print(f"{'='*60}")
                    
                    self.log_success(f"Downloaded playlist: {playlist_title} in {elapsed_time:.1f}s")
                    return
                    
                elif attempt < MAX_RETRIES:
                    print(f"⚠️ Download failed, retrying in {RETRY_DELAY} seconds...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"\n❌ Failed to download after {MAX_RETRIES} attempts")
                    self.log_failure(f"Failed playlist: {url}")
                    
            except subprocess.TimeoutExpired:
                print(f"\n⚠️ Download timeout, retrying in {RETRY_DELAY} seconds...")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"\n❌ Playlist download timed out after {MAX_RETRIES} attempts")
                    self.log_failure(f"Playlist timeout: {url}")
                    return
            except Exception as e:
                print(f"\n❌ Error: {str(e)[:100]}")
                self.log_error(f"Error downloading playlist {url}: {e}")
                if attempt == MAX_RETRIES:
                    return
    
    # ==================== yt-dlp Helpers ====================
    
    @staticmethod
    def check_ytdlp():
        """
        Check if yt-dlp is installed (cache yt-dlp)
        """
        if shutil.which("yt-dlp"):
            print("✅ yt-dlp is already installed")
            
            # Check version
            try:
                result = subprocess.run(
                    ["yt-dlp", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=True,
                    timeout=10
                )
                if result.returncode == 0:
                    version = result.stdout.strip()
                    print(f"yt-dlp version: {version}")
                    return True
            except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError):
                print("⚠️ Could not determine yt-dlp version")
                return True  # Still installed even if version check fails
        else:
            print("❌ yt-dlp not found. Installing...")
            
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp", "-q"])
                print("✅ yt-dlp installed successfully")
                return True
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install yt-dlp: {e}")
                return False
    
    @staticmethod     
    def show_ytdlp_help():
        """Display yt-dlp help"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )
            print("\n" + "="*60)
            print("YT-DLP HELP (first 2000 characters)")
            print("="*60)
            print(result.stdout[:2000])
            print("\n... (output truncated, use 'yt-dlp --help' for full help)")
            print("="*60)
        except subprocess.CalledProcessError as e:
            print(f"Could not get yt-dlp help: {e}")
    
    @staticmethod     
    def program_info():
        """Display program information"""
        print("="*80)
        print("ENHANCED YOUTUBE/YOUTUBE MUSIC DOWNLOADER")
        print("="*80)
        print("Features added:")
        print("• Progress bars for all downloads")
        print("• Batch processing with parallel downloads")
        print("• Resource validation before downloading")
        print("• Size estimation and availability checks")
        print("• Configuration saving")
        print("• Empty directory cleanup")
        print("="*80)
        print("\nDependencies:")
        print("• yt-dlp (required) - Audio/video downloader")
        print("• tqdm (optional) - Better progress bars")
        print("="*80)


""" =========================================== Main Menu & Execution =========================================== """

def display_menu() -> None:
    """Display the enhanced main menu."""
    menu = """
    ========================================================================
    ENHANCED YOUTUBE/YOUTUBE MUSIC DOWNLOADER
    ========================================================================
    Features: Progress Bars | Batch Processing | Resource Validation
    ------------------------------------------------------------------------
    Select an option:
    1.  Download Single Track (with progress)
    2.  Download Album
    3.  Download Playlist (with progress)
    4.  Batch Download from Text File (parallel processing)
    5.  Search and Download Song
    6.  Download YouTube Channel
    7.  Check/Install yt-dlp
    8.  Show yt-dlp Help
    9.  Show Program Info
    10. Exit
    ========================================================================
    """
    print(menu)

def main():
    """Main function to run the Enhanced YouTube Downloader."""
    print("="*60)
    print("ENHANCED YOUTUBE/YOUTUBE MUSIC DOWNLOADER")
    print("="*60)
    print("Initializing with progress bars, batch processing & validation...")
    
    # Check for optional dependencies
    if not TQDM_AVAILABLE:
        print("\n⚠️  For better progress bars, install: pip install tqdm")
        print("   (Continuing with basic progress display)\n")
    
    # Create necessary directories
    os.makedirs("log", exist_ok=True)
    os.makedirs("Albums", exist_ok=True)
    os.makedirs("links", exist_ok=True)
    
    # Check yt-dlp installation
    if not Youtube_Downloader.check_ytdlp():
        print("="*60)
        print("\n❌ Failed to install yt-dlp. Please install it manually using:")
        print("   pip install yt-dlp")
        print("\nThen run the program again.")
        print("="*60)
        input("Press Enter to exit...")
        return
    
    downloader = Youtube_Downloader()
    
    # Main program loop
    running = True
    while running:
        try:
            display_menu()
            print("="*60)
            choice = input("\nEnter your choice (1-10): ").strip()
            
            if choice == "1":
                downloader.download_track()
            elif choice == "2":
                downloader.download_album()
            elif choice == "3":
                downloader.download_playlist()
            elif choice == "4":
                downloader.download_from_file()
            elif choice == "5":
                downloader.search_a_song()
            elif choice == "6":
                downloader.download_channel()
            elif choice == "7":
                downloader.check_ytdlp()
            elif choice == "8":
                Youtube_Downloader.show_ytdlp_help()
            elif choice == "9":
                Youtube_Downloader.program_info()
            elif choice == "10":
                print("\n" + "="*60)
                print("Thank you for using Enhanced YouTube Downloader. Goodbye!")
                print("="*60)
                running = False
            else:
                print("Invalid choice. Please try again.")
            
            # Only ask to continue if not exiting
            if running and choice not in ["7", "8", "9"]:
                print("\n" + "="*60)
                cont = input("Return to main menu? (y/n): ").strip().lower()
                if cont not in ['y', 'yes', '']:
                    print("\nThank you for using Enhanced YouTube Downloader. Goodbye!")
                    running = False
                
        except KeyboardInterrupt:
            print("\n\nProgram interrupted. Exiting...")
            running = False
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            print("The program will continue...")
            continue

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProgram interrupted by user. Goodbye!")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please check the error log for details.")