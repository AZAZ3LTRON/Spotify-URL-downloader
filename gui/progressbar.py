import sys
import os
import time
import random
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
from concurrent.futures import ThreadPoolExecutor
import urllib.request
from dataclasses import dataclass
from typing import Optional, List
import json

@dataclass
class DownloadItem:
    """Data class for download items"""
    id: str
    url: str
    filename: str
    size: int = 0
    downloaded: int = 0
    speed: float = 0.0
    status: str = "Pending"  # Pending, Downloading, Paused, Completed, Error
    error: Optional[str] = None
    start_time: Optional[float] = None
    
    @property
    def progress(self) -> float:
        """Calculate download progress percentage"""
        if self.size == 0:
            return 0
        return (self.downloaded / self.size) * 100
    
    @property
    def remaining_time(self) -> Optional[float]:
        """Calculate estimated remaining time in seconds"""
        if self.speed <= 0 or self.size <= self.downloaded:
            return None
        return (self.size - self.downloaded) / self.speed

class DownloadWorker(QObject):
    """Worker thread for downloading files"""
    progress_updated = Signal(str, int, float)  # id, downloaded, speed
    download_completed = Signal(str)
    download_error = Signal(str, str)
    
    def __init__(self, download_item: DownloadItem):
        super().__init__()
        self.download_item = download_item
        self._is_paused = False
        self._is_cancelled = False
        
    def download(self):
        """Main download method"""
        try:
            self.download_item.status = "Downloading"
            self.download_item.start_time = time.time()
            
            # Create request with headers
            req = urllib.request.Request(
                self.download_item.url,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            
            # Open connection
            with urllib.request.urlopen(req) as response:
                # Get file size
                self.download_item.size = int(response.headers.get('Content-Length', 0))
                
                # Create download directory if it doesn't exist
                os.makedirs("downloads", exist_ok=True)
                filepath = os.path.join("downloads", self.download_item.filename)
                
                # Download file in chunks
                chunk_size = 8192  # 8KB chunks
                last_update_time = time.time()
                downloaded_since_update = 0
                
                with open(filepath, 'wb') as file:
                    while True:
                        if self._is_cancelled:
                            os.remove(filepath)
                            return
                            
                        if self._is_paused:
                            time.sleep(0.1)
                            continue
                            
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                            
                        file.write(chunk)
                        self.download_item.downloaded += len(chunk)
                        downloaded_since_update += len(chunk)
                        
                        # Calculate and emit speed every 0.5 seconds
                        current_time = time.time()
                        if current_time - last_update_time >= 0.5:
                            elapsed = current_time - last_update_time
                            self.download_item.speed = downloaded_since_update / elapsed
                            
                            self.progress_updated.emit(
                                self.download_item.id,
                                self.download_item.downloaded,
                                self.download_item.speed
                            )
                            
                            last_update_time = current_time
                            downloaded_since_update = 0
                
                # Download completed successfully
                self.download_completed.emit(self.download_item.id)
                
        except Exception as e:
            self.download_error.emit(self.download_item.id, str(e))
    
    def pause(self):
        """Pause the download"""
        self._is_paused = True
        
    def resume(self):
        """Resume the download"""
        self._is_paused = False
        
    def cancel(self):
        """Cancel the download"""
        self._is_cancelled = True

class DownloadItemWidget(QWidget):
    """Widget for displaying individual download items"""
    
    def __init__(self, download_item: DownloadItem):
        super().__init__()
        self.download_item = download_item
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Top row: Filename and status
        top_layout = QHBoxLayout()
        
        # File icon and name
        file_info_layout = QHBoxLayout()
        file_icon = QLabel()
        file_icon.setPixmap(self.create_file_icon().scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        file_info_layout.addWidget(file_icon)
        
        self.filename_label = QLabel(self.download_item.filename)
        self.filename_label.setStyleSheet("font-weight: bold; color: #ffffff;")
        file_info_layout.addWidget(self.filename_label)
        
        file_info_layout.addStretch()
        top_layout.addLayout(file_info_layout)
        
        # Status label
        self.status_label = QLabel(self.download_item.status)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 12px;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: #3a3a3a;
            }
        """)
        top_layout.addWidget(self.status_label)
        
        layout.addLayout(top_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 6px;
                text-align: center;
                background-color: #2d2d2d;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #0078d7;
                border-radius: 5px;
            }
        """)
        
        # Set initial progress
        self.progress_bar.setValue(int(self.download_item.progress))
        
        # Custom progress text
        self.update_progress_text()
        
        layout.addWidget(self.progress_bar)
        
        # Bottom row: Speed and details
        bottom_layout = QHBoxLayout()
        
        # Speed indicator
        speed_layout = QHBoxLayout()
        speed_icon = QLabel()
        speed_icon.setPixmap(self.create_speed_icon().scaled(16, 16, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        speed_layout.addWidget(speed_icon)
        
        self.speed_label = QLabel("0 B/s")
        self.speed_label.setStyleSheet("color: #888888; font-size: 11px;")
        speed_layout.addWidget(self.speed_label)
        bottom_layout.addLayout(speed_layout)
        
        # Size and remaining time
        details_layout = QHBoxLayout()
        
        self.size_label = QLabel(self.format_size(self.download_item.downloaded))
        self.size_label.setStyleSheet("color: #888888; font-size: 11px;")
        details_layout.addWidget(self.size_label)
        
        details_layout.addWidget(QLabel("•"))
        
        self.time_label = QLabel("Estimating...")
        self.time_label.setStyleSheet("color: #888888; font-size: 11px;")
        details_layout.addWidget(self.time_label)
        
        bottom_layout.addLayout(details_layout)
        
        bottom_layout.addStretch()
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        self.pause_btn = QPushButton("⏸")
        self.pause_btn.setFixedSize(28, 28)
        self.pause_btn.setStyleSheet(self.get_button_style("#ffb900"))
        self.pause_btn.setToolTip("Pause download")
        
        self.cancel_btn = QPushButton("✕")
        self.cancel_btn.setFixedSize(28, 28)
        self.cancel_btn.setStyleSheet(self.get_button_style("#d13438"))
        self.cancel_btn.setToolTip("Cancel download")
        
        button_layout.addWidget(self.pause_btn)
        button_layout.addWidget(self.cancel_btn)
        
        bottom_layout.addLayout(button_layout)
        
        layout.addLayout(bottom_layout)
        
        self.setLayout(layout)
        
        # Set widget background
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                border: 1px solid #333;
            }
        """)
        
        # Set fixed height
        self.setFixedHeight(120)
        
    def get_button_style(self, color):
        """Get style sheet for action buttons"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}cc;
            }}
            QPushButton:pressed {{
                background-color: {color}99;
            }}
        """
        
    def create_file_icon(self):
        """Create a file icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw file shape
        painter.setBrush(QColor(66, 133, 244))
        painter.setPen(QPen(QColor(30, 30, 30), 1))
        
        # File body
        painter.drawRoundedRect(4, 2, 24, 26, 2, 2)
        
        # File tab
        painter.drawRect(4, 2, 8, 6)
        painter.drawRect(12, 2, 16, 2)
        
        painter.end()
        return pixmap
        
    def create_speed_icon(self):
        """Create a speedometer icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw speedometer
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.drawArc(4, 4, 24, 24, 30 * 16, 120 * 16)
        
        # Draw needle
        painter.setPen(QPen(QColor(66, 133, 244), 2))
        center_x, center_y = 16, 16
        painter.drawLine(center_x, center_y, center_x + 8, center_y - 8)
        
        painter.end()
        return pixmap
        
    def format_size(self, size_bytes):
        """Format bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
        
    def format_time(self, seconds):
        """Format seconds to human readable time"""
        if seconds is None:
            return "--:--"
        
        seconds = int(seconds)
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}:{seconds % 60:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}:{minutes:02d}:{seconds % 60:02d}"
        
    def update_progress(self, downloaded: int, speed: float):
        """Update progress display"""
        self.download_item.downloaded = downloaded
        self.download_item.speed = speed
        
        # Update progress bar
        self.progress_bar.setValue(int(self.download_item.progress))
        
        # Update labels
        self.update_progress_text()
        self.speed_label.setText(f"{self.format_size(speed)}/s")
        self.size_label.setText(f"{self.format_size(downloaded)} / {self.format_size(self.download_item.size)}")
        
        # Update time estimate
        if self.download_item.remaining_time:
            self.time_label.setText(f"{self.format_time(self.download_item.remaining_time)} remaining")
        else:
            self.time_label.setText("Calculating...")
            
    def update_progress_text(self):
        """Update the progress bar text"""
        progress_text = f"{self.download_item.progress:.1f}%"
        if self.download_item.size > 0:
            progress_text += f" ({self.format_size(self.download_item.downloaded)} / {self.format_size(self.download_item.size)})"
        self.progress_bar.setFormat(progress_text)
        
    def update_status(self, status: str):
        """Update download status"""
        self.download_item.status = status
        self.status_label.setText(status)
        
        # Update status color
        colors = {
            "Downloading": "#107c10",
            "Paused": "#ffb900",
            "Completed": "#107c10",
            "Error": "#d13438",
            "Pending": "#888888"
        }
        
        color = colors.get(status, "#888888")
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-size: 12px;
                padding: 2px 8px;
                border-radius: 10px;
                background-color: {color};
            }}
        """)

class DownloadManager(QMainWindow):
    """Main download manager window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Download Manager - PySide6")
        self.setGeometry(100, 100, 900, 700)
        
        # Initialize download tracking
        self.downloads: List[DownloadItem] = []
        self.workers: dict[str, DownloadWorker] = {}
        self.threads: dict[str, QThread] = {}
        
        # Thread pool for downloads
        self.thread_pool = ThreadPoolExecutor(max_workers=3)
        
        # Load saved downloads
        self.load_downloads()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Title
        title_label = QLabel("Download Manager")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
                padding-bottom: 5px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Download files with progress tracking, pause/resume support, "
            "and detailed statistics."
        )
        desc_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
                padding-bottom: 10px;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        main_layout.addWidget(desc_label)
        
        # Download controls
        controls_frame = QFrame()
        controls_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 10px;
                border: 1px solid #444444;
            }
        """)
        
        controls_layout = QVBoxLayout()
        controls_layout.setContentsMargins(20, 15, 20, 15)
        
        # URL input
        url_layout = QHBoxLayout()
        url_label = QLabel("Download URL:")
        url_label.setStyleSheet("color: #cccccc; font-weight: bold;")
        url_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Enter download URL here...")
        self.url_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #0078d7;
            }
        """)
        url_layout.addWidget(self.url_input, 1)
        
        # Add sample URLs button
        sample_btn = QPushButton("📋")
        sample_btn.setToolTip("Insert sample URL")
        sample_btn.setFixedSize(40, 40)
        sample_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #1088e7;
            }
        """)
        sample_btn.clicked.connect(self.insert_sample_url)
        url_layout.addWidget(sample_btn)
        
        controls_layout.addLayout(url_layout)
        
        # Download button
        download_btn = QPushButton("Start Download")
        download_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #128c12;
            }
            QPushButton:pressed {
                background-color: #0e6c0e;
            }
        """)
        download_btn.clicked.connect(self.start_download)
        controls_layout.addWidget(download_btn)
        
        controls_frame.setLayout(controls_layout)
        main_layout.addWidget(controls_frame)
        
        # Downloads header
        header_layout = QHBoxLayout()
        
        downloads_label = QLabel("Active Downloads")
        downloads_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(downloads_label)
        
        header_layout.addStretch()
        
        # Global controls
        global_controls = QHBoxLayout()
        global_controls.setSpacing(10)
        
        self.pause_all_btn = QPushButton("Pause All")
        self.pause_all_btn.setStyleSheet(self.get_global_button_style("#ffb900"))
        self.pause_all_btn.clicked.connect(self.pause_all_downloads)
        
        self.resume_all_btn = QPushButton("Resume All")
        self.resume_all_btn.setStyleSheet(self.get_global_button_style("#107c10"))
        self.resume_all_btn.clicked.connect(self.resume_all_downloads)
        
        self.cancel_all_btn = QPushButton("Cancel All")
        self.cancel_all_btn.setStyleSheet(self.get_global_button_style("#d13438"))
        self.cancel_all_btn.clicked.connect(self.cancel_all_downloads)
        
        global_controls.addWidget(self.pause_all_btn)
        global_controls.addWidget(self.resume_all_btn)
        global_controls.addWidget(self.cancel_all_btn)
        
        header_layout.addLayout(global_controls)
        main_layout.addLayout(header_layout)
        
        # Scroll area for downloads
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #555555;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #666666;
            }
        """)
        
        # Container for download widgets
        self.downloads_container = QWidget()
        self.downloads_layout = QVBoxLayout()
        self.downloads_layout.setSpacing(10)
        self.downloads_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add stretch to push items to top
        self.downloads_layout.addStretch()
        
        self.downloads_container.setLayout(self.downloads_layout)
        self.scroll_area.setWidget(self.downloads_container)
        
        main_layout.addWidget(self.scroll_area, 1)
        
        # Statistics bar
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                border: 1px solid #444;
                padding: 10px;
            }
        """)
        
        stats_layout = QHBoxLayout()
        
        # Total downloads
        self.total_label = QLabel("Total: 0")
        self.total_label.setStyleSheet("color: #cccccc;")
        stats_layout.addWidget(self.total_label)
        
        # Active downloads
        self.active_label = QLabel("Active: 0")
        self.active_label.setStyleSheet("color: #107c10; font-weight: bold;")
        stats_layout.addWidget(self.active_label)
        
        # Completed downloads
        self.completed_label = QLabel("Completed: 0")
        self.completed_label.setStyleSheet("color: #107c10;")
        stats_layout.addWidget(self.completed_label)
        
        # Failed downloads
        self.failed_label = QLabel("Failed: 0")
        self.failed_label.setStyleSheet("color: #d13438;")
        stats_layout.addWidget(self.failed_label)
        
        stats_layout.addStretch()
        
        # Download directory button
        dir_btn = QPushButton("📂 Open Downloads Folder")
        dir_btn.setStyleSheet("""
            QPushButton {
                background-color: #555;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #666;
            }
        """)
        dir_btn.clicked.connect(self.open_downloads_folder)
        stats_layout.addWidget(dir_btn)
        
        stats_frame.setLayout(stats_layout)
        main_layout.addWidget(stats_frame)
        
        central_widget.setLayout(main_layout)
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
        # Update statistics
        self.update_statistics()
        
    def get_global_button_style(self, color):
        """Get style for global control buttons"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-size: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}cc;
            }}
        """
        
    def insert_sample_url(self):
        """Insert a sample download URL"""
        sample_urls = [
            "https://download.samplelib.com/mp4/sample-5s.mp4",
            "https://file-examples.com/storage/fef1706276640fa2f99d5cd/2017/11/file_example_MP3_1MG.mp3",
            "https://file-examples.com/storage/fef1706276640fa2f99d5cd/2017/10/file_example_PDF_1MB.pdf",
            "https://speed.hetzner.de/100MB.bin",
            "https://www.learningcontainer.com/wp-content/uploads/2020/05/sample-zip-file.zip"
        ]
        
        self.url_input.setText(random.choice(sample_urls))
        
    def start_download(self):
        """Start a new download"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a download URL")
            return
            
        # Extract filename from URL
        filename = os.path.basename(url) or f"download_{int(time.time())}.bin"
        
        # Create download item
        download_id = f"dl_{int(time.time())}_{random.randint(1000, 9999)}"
        download_item = DownloadItem(
            id=download_id,
            url=url,
            filename=filename
        )
        
        # Add to downloads list
        self.downloads.append(download_item)
        
        # Create and add widget
        widget = DownloadItemWidget(download_item)
        self.downloads_layout.insertWidget(0, widget)
        
        # Connect widget buttons
        widget.pause_btn.clicked.connect(lambda: self.toggle_download(download_id))
        widget.cancel_btn.clicked.connect(lambda: self.cancel_download(download_id))
        
        # Start download in thread
        self.start_download_thread(download_item)
        
        # Clear URL input
        self.url_input.clear()
        
        # Update statistics
        self.update_statistics()
        
        # Save downloads
        self.save_downloads()
        
    def start_download_thread(self, download_item: DownloadItem):
        """Start download in a separate thread"""
        # Create worker and thread
        worker = DownloadWorker(download_item)
        thread = QThread()
        
        # Move worker to thread
        worker.moveToThread(thread)
        
        # Connect signals
        thread.started.connect(worker.download)
        worker.progress_updated.connect(self.on_download_progress)
        worker.download_completed.connect(self.on_download_completed)
        worker.download_error.connect(self.on_download_error)
        
        # Clean up thread when done
        worker.download_completed.connect(thread.quit)
        worker.download_error.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        
        # Store references
        self.workers[download_item.id] = worker
        self.threads[download_item.id] = thread
        
        # Start thread
        thread.start()
        
    def on_download_progress(self, download_id: str, downloaded: int, speed: float):
        """Handle download progress updates"""
        # Find the widget
        widget = self.find_widget_by_id(download_id)
        if widget:
            widget.update_progress(downloaded, speed)
            widget.update_status("Downloading")
            
    def on_download_completed(self, download_id: str):
        """Handle download completion"""
        widget = self.find_widget_by_id(download_id)
        if widget:
            widget.update_status("Completed")
            widget.pause_btn.setEnabled(False)
            widget.cancel_btn.setEnabled(False)
            
        # Update statistics
        self.update_statistics()
        self.save_downloads()
        
    def on_download_error(self, download_id: str, error: str):
        """Handle download error"""
        widget = self.find_widget_by_id(download_id)
        if widget:
            widget.update_status("Error")
            widget.time_label.setText(f"Error: {error[:30]}...")
            
        # Update statistics
        self.update_statistics()
        self.save_downloads()
        
    def find_widget_by_id(self, download_id: str) -> Optional[DownloadItemWidget]:
        """Find a widget by download ID"""
        for i in range(self.downloads_layout.count()):
            item = self.downloads_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if hasattr(widget, 'download_item') and widget.download_item.id == download_id:
                    return widget
        return None
        
    def toggle_download(self, download_id: str):
        """Toggle pause/resume for a download"""
        worker = self.workers.get(download_id)
        widget = self.find_widget_by_id(download_id)
        
        if worker and widget:
            if widget.download_item.status == "Paused":
                worker.resume()
                widget.update_status("Downloading")
            else:
                worker.pause()
                widget.update_status("Paused")
                
    def cancel_download(self, download_id: str):
        """Cancel a download"""
        worker = self.workers.get(download_id)
        if worker:
            worker.cancel()
            
        widget = self.find_widget_by_id(download_id)
        if widget:
            widget.update_status("Cancelled")
            
        # Update statistics
        self.update_statistics()
        
    def pause_all_downloads(self):
        """Pause all active downloads"""
        for download_id, worker in self.workers.items():
            widget = self.find_widget_by_id(download_id)
            if widget and widget.download_item.status == "Downloading":
                worker.pause()
                widget.update_status("Paused")
                
    def resume_all_downloads(self):
        """Resume all paused downloads"""
        for download_id, worker in self.workers.items():
            widget = self.find_widget_by_id(download_id)
            if widget and widget.download_item.status == "Paused":
                worker.resume()
                widget.update_status("Downloading")
                
    def cancel_all_downloads(self):
        """Cancel all downloads"""
        reply = QMessageBox.question(
            self, "Cancel All",
            "Are you sure you want to cancel all downloads?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for download_id, worker in self.workers.items():
                worker.cancel()
                
            # Clear all widgets
            while self.downloads_layout.count():
                item = self.downloads_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
                    
            # Clear data
            self.downloads.clear()
            self.workers.clear()
            self.threads.clear()
            
            # Update statistics
            self.update_statistics()
            self.save_downloads()
            
    def update_statistics(self):
        """Update download statistics"""
        total = len(self.downloads)
        active = len([d for d in self.downloads if d.status == "Downloading"])
        completed = len([d for d in self.downloads if d.status == "Completed"])
        failed = len([d for d in self.downloads if d.status in ["Error", "Cancelled"]])
        
        self.total_label.setText(f"Total: {total}")
        self.active_label.setText(f"Active: {active}")
        self.completed_label.setText(f"Completed: {completed}")
        self.failed_label.setText(f"Failed: {failed}")
        
    def open_downloads_folder(self):
        """Open the downloads folder"""
        downloads_path = os.path.join(os.getcwd(), "downloads")
        os.makedirs(downloads_path, exist_ok=True)
        
        if sys.platform == "win32":
            os.startfile(downloads_path)
        elif sys.platform == "darwin":
            os.system(f"open '{downloads_path}'")
        else:
            os.system(f"xdg-open '{downloads_path}'")
            
    def save_downloads(self):
        """Save download list to file"""
        try:
            data = []
            for d in self.downloads:
                if d.status in ["Completed", "Error", "Cancelled"]:
                    data.append({
                        'id': d.id,
                        'url': d.url,
                        'filename': d.filename,
                        'size': d.size,
                        'status': d.status
                    })
                    
            with open('downloads_history.json', 'w') as f:
                json.dump(data, f)
        except:
            pass
            
    def load_downloads(self):
        """Load download list from file"""
        try:
            if os.path.exists('downloads_history.json'):
                with open('downloads_history.json', 'r') as f:
                    data = json.load(f)
                    
                for item_data in data:
                    download_item = DownloadItem(
                        id=item_data['id'],
                        url=item_data['url'],
                        filename=item_data['filename'],
                        size=item_data['size'],
                        status=item_data['status']
                    )
                    self.downloads.append(download_item)
        except:
            pass
            
    def closeEvent(self, event):
        """Handle application close"""
        # Cancel all ongoing downloads
        for worker in self.workers.values():
            worker.cancel()
            
        # Save downloads
        self.save_downloads()
        
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set dark palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Base, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    
    window = DownloadManager()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()