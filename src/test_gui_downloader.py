# gui_downloader.py
import sys
import os
import json
from pathlib import Path
from typing import Optional, Dict, List
import threading
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QLineEdit, QTextEdit, QLabel, QProgressBar,
    QFileDialog, QMessageBox, QGroupBox, QFormLayout, QTabWidget,
    QSpinBox, QCheckBox, QListWidget, QListWidgetItem, QSplitter,
    QDialog, QDialogButtonBox
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer
from PySide6.QtGui import QFont, QTextCursor, QIcon

# Import the existing downloader class
from main_downloader import Youtube_Downloader, SUCCESS_LOG, FAILED_LOG, ERROR_LOG

# Create log directory if it doesn't exist
os.makedirs("log", exist_ok=True)
os.makedirs("links", exist_ok=True)

class DownloadWorker(QObject):
    """Worker thread for downloads"""
    progress = Signal(str, int)  # url, percentage
    status = Signal(str, str)    # type, message
    finished = Signal(bool, str) # success, message
    
    def __init__(self, downloader: Youtube_Downloader, url: str, download_type: str):
        super().__init__()
        self.downloader = downloader
        self.url = url
        self.download_type = download_type
        self._is_running = True
        
    def run(self):
        """Execute download in thread"""
        try:
            # Set downloader parameters from GUI
            self.downloader._Youtube_Downloader__output_directory = Path(self.downloader._Youtube_Downloader__output_directory)
            self.downloader._Youtube_Downloader__output_directory.mkdir(parents=True, exist_ok=True)
            
            # Determine output template based on type
            if self.download_type == "track":
                output_template = str(self.downloader._Youtube_Downloader__output_directory / "%(title)s.%(ext)s")
                func = lambda: self.downloader.run_download(self.url, output_template)
            elif self.download_type == "album":
                output_template = str(self.downloader._Youtube_Downloader__output_directory / "%(artist)s/%(album)s/%(title)s.%(ext)s")
                func = lambda: self.downloader.run_download(self.url, output_template)
            elif self.download_type == "playlist":
                output_template = str(self.downloader._Youtube_Downloader__output_directory / "%(playlist)s/%(title)s.%(ext)s")
                func = lambda: self.downloader.run_download(self.url, output_template)
            else:
                self.finished.emit(False, f"Unknown download type: {self.download_type}")
                return
            
            # Run the download
            result = func()
            
            if hasattr(result, 'returncode') and result.returncode == 0:
                self.finished.emit(True, f"Successfully downloaded {self.download_type}")
            else:
                self.finished.emit(False, f"Download failed")
                
        except Exception as e:
            self.downloader.log_error(f"Download error: {e}")
            self.finished.emit(False, f"Error: {str(e)}")
    
    def stop(self):
        """Stop the download"""
        self._is_running = False

class BatchDownloadWorker(QObject):
    """Worker for batch downloads from file"""
    progress = Signal(str, int)  # current_url, percentage
    item_complete = Signal(str, bool, str)  # url, success, message
    status = Signal(str, str)    # type, message
    finished = Signal(bool, str) # success, message
    
    def __init__(self, downloader: Youtube_Downloader, filepath: str):
        super().__init__()
        self.downloader = downloader
        self.filepath = filepath
        self._is_running = True
        
    def run(self):
        """Execute batch download"""
        try:
            if not os.path.exists(self.filepath):
                self.finished.emit(False, f"File not found: {self.filepath}")
                return
            
            with open(self.filepath, 'r', encoding='utf-8') as file:
                urls = [line.strip() for line in file if line.strip() and not line.startswith('#')]
            
            if not urls:
                self.finished.emit(False, "No URLs found in file")
                return
            
            total = len(urls)
            success_count = 0
            
            for i, url in enumerate(urls, 1):
                if not self._is_running:
                    break
                    
                self.status.emit("progress", f"Processing {i}/{total}: {url}")
                
                # Validate URL
                if not self.downloader.validate_youtube_url(url):
                    self.item_complete.emit(url, False, "Invalid URL")
                    continue
                
                # Determine output template
                if "playlist" in url.lower():
                    output_template = str(self.downloader._Youtube_Downloader__output_directory / "%(playlist)s/%(title)s.%(ext)s")
                elif "album" in url.lower():
                    output_template = str(self.downloader._Youtube_Downloader__output_directory / "%(artist)s/%(album)s/%(title)s.%(ext)s")
                else:
                    output_template = str(self.downloader._Youtube_Downloader__output_directory / "%(title)s.%(ext)s")
                
                # Download
                result = self.downloader.run_download(url, output_template)
                
                if hasattr(result, 'returncode') and result.returncode == 0:
                    self.item_complete.emit(url, True, "Success")
                    success_count += 1
                else:
                    self.item_complete.emit(url, False, "Failed")
                
                # Update progress
                self.progress.emit(url, int((i / total) * 100))
            
            self.finished.emit(
                success_count > 0, 
                f"Batch complete: {success_count}/{total} successful"
            )
            
        except Exception as e:
            self.finished.emit(False, f"Batch error: {str(e)}")
    
    def stop(self):
        """Stop batch download"""
        self._is_running = False

class LogMonitor(QThread):
    """Thread to monitor log files"""
    log_updated = Signal(str, str)  # log_type, content
    
    def __init__(self, log_files: Dict[str, str]):
        super().__init__()
        self.log_files = log_files
        self.last_positions = {log_type: 0 for log_type in log_files}
        self._is_running = True
        
    def run(self):
        """Monitor log files for changes"""
        while self._is_running:
            for log_type, filepath in self.log_files.items():
                try:
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            f.seek(self.last_positions[log_type])
                            new_content = f.read()
                            if new_content:
                                self.log_updated.emit(log_type, new_content)
                            self.last_positions[log_type] = f.tell()
                except Exception:
                    pass
            self.msleep(1000)  # Check every second
    
    def stop(self):
        """Stop monitoring"""
        self._is_running = False

class SettingsDialog(QDialog):
    """Settings dialog"""
    def __init__(self, downloader: Youtube_Downloader, parent=None):
        super().__init__(parent)
        self.downloader = downloader
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Audio settings group
        audio_group = QGroupBox("Audio Settings")
        audio_layout = QFormLayout()
        
        self.format_combo = QComboBox()
        self.format_combo.addItems(["mp3", "flac", "ogg", "opus", "m4a", "wav"])
        audio_layout.addRow("Audio Format:", self.format_combo)
        
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["320k", "256k", "192k", "160k", "128k", "96k", "64k"])
        audio_layout.addRow("Audio Quality:", self.quality_combo)
        
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)
        
        # Download settings group
        dl_group = QGroupBox("Download Settings")
        dl_layout = QFormLayout()
        
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(1, 10)
        dl_layout.addRow("Max Retries:", self.max_retries_spin)
        
        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(1, 60)
        self.retry_delay_spin.setSuffix(" seconds")
        dl_layout.addRow("Retry Delay:", self.retry_delay_spin)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 600)
        self.timeout_spin.setSuffix(" seconds")
        dl_layout.addRow("Download Timeout:", self.timeout_spin)
        
        self.parallel_spin = QSpinBox()
        self.parallel_spin.setRange(1, 10)
        dl_layout.addRow("Parallel Downloads:", self.parallel_spin)
        
        dl_group.setLayout(dl_layout)
        layout.addWidget(dl_group)
        
        # Output directory
        out_group = QGroupBox("Output Directory")
        out_layout = QHBoxLayout()
        
        self.output_edit = QLineEdit()
        self.output_edit.setReadOnly(True)
        out_layout.addWidget(self.output_edit)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_output)
        out_layout.addWidget(self.browse_btn)
        
        out_group.setLayout(out_layout)
        layout.addWidget(out_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.resize(400, 400)
        
    def browse_output(self):
        """Browse for output directory"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory",
            self.output_edit.text() or str(Path.home())
        )
        if directory:
            self.output_edit.setText(directory)
    
    def load_settings(self):
        """Load current settings"""
        # Load from config file if exists
        config_file = self.downloader._Youtube_Downloader__configuration_file
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    
                self.output_edit.setText(config.get("output_dir", "Albums"))
                self.quality_combo.setCurrentText(config.get("audio_quality", "320k"))
                self.format_combo.setCurrentText(config.get("audio_format", "mp3"))
                self.max_retries_spin.setValue(config.get("max_retries", 3))
                self.retry_delay_spin.setValue(config.get("retry_delay", 10))
                self.timeout_spin.setValue(config.get("download_timeout", 120))
                self.parallel_spin.setValue(config.get("max_parallel_downloads", 4))
                return
            except:
                pass
        
        # Defaults
        self.output_edit.setText("Albums")
        self.quality_combo.setCurrentText("320k")
        self.format_combo.setCurrentText("mp3")
        self.max_retries_spin.setValue(3)
        self.retry_delay_spin.setValue(10)
        self.timeout_spin.setValue(120)
        self.parallel_spin.setValue(4)
    
    def get_settings(self) -> Dict:
        """Get current settings"""
        return {
            "output_dir": self.output_edit.text(),
            "audio_quality": self.quality_combo.currentText(),
            "audio_format": self.format_combo.currentText(),
            "max_retries": self.max_retries_spin.value(),
            "retry_delay": self.retry_delay_spin.value(),
            "download_timeout": self.timeout_spin.value(),
            "max_parallel_downloads": self.parallel_spin.value()
        }

class YouTubeDownloaderGUI(QMainWindow):
    """Main GUI window"""
    
    def __init__(self):
        super().__init__()
        self.downloader = Youtube_Downloader()
        self.download_thread = None
        self.download_worker = None
        self.batch_thread = None
        self.batch_worker = None
        self.log_monitor = None
        
        self.setup_ui()
        self.setup_connections()
        self.start_log_monitor()
        
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("YouTube/YouTube Music Downloader")
        self.setGeometry(100, 100, 1000, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # Header
        header_label = QLabel("YouTube/YouTube Music Downloader")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header_label.setFont(header_font)
        header_label.setAlignment(Qt.AlignCenter)
        header_label.setStyleSheet("color: #2196F3; padding: 10px;")
        main_layout.addWidget(header_label)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Download tab
        self.setup_download_tab()
        
        # Batch tab
        self.setup_batch_tab()
        
        # Logs tab
        self.setup_logs_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Progress area
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setFixedWidth(100)
        
        self.validate_btn = QPushButton("Validate Links")
        self.validate_btn.setFixedWidth(100)
        
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(100)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.settings_btn)
        button_layout.addWidget(self.validate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
        
        central_widget.setLayout(main_layout)
        
    def setup_download_tab(self):
        """Setup the download tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Type selection
        type_group = QGroupBox("Download Type")
        type_layout = QHBoxLayout()
        
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Track", "Album", "Playlist", "Channel"])
        type_layout.addWidget(QLabel("Type:"))
        type_layout.addWidget(self.type_combo)
        type_layout.addStretch()
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # URL input
        url_group = QGroupBox("URL")
        url_layout = QVBoxLayout()
        
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("Enter YouTube/YouTube Music URL...")
        url_layout.addWidget(self.url_edit)
        
        url_group.setLayout(url_layout)
        layout.addWidget(url_group)
        
        # Quick actions
        action_group = QGroupBox("Quick Actions")
        action_layout = QHBoxLayout()
        
        self.paste_btn = QPushButton("Paste URL")
        self.paste_btn.clicked.connect(self.paste_url)
        
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.clicked.connect(self.clear_url)
        
        action_layout.addWidget(self.paste_btn)
        action_layout.addWidget(self.clear_btn)
        action_layout.addStretch()
        
        action_group.setLayout(action_layout)
        layout.addWidget(action_group)
        
        # Download button
        self.download_btn = QPushButton("Start Download")
        self.download_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        layout.addWidget(self.download_btn)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Download")
        
    def setup_batch_tab(self):
        """Setup the batch download tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # File selection
        file_group = QGroupBox("Batch File")
        file_layout = QHBoxLayout()
        
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Select a text file with URLs...")
        file_layout.addWidget(self.file_edit)
        
        self.file_browse_btn = QPushButton("Browse...")
        self.file_browse_btn.clicked.connect(self.browse_batch_file)
        file_layout.addWidget(self.file_browse_btn)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # URL list
        list_group = QGroupBox("URLs in File")
        list_layout = QVBoxLayout()
        
        self.url_list = QListWidget()
        list_layout.addWidget(self.url_list)
        
        list_group.setLayout(list_layout)
        layout.addWidget(list_group)
        
        # Batch controls
        control_layout = QHBoxLayout()
        
        self.load_btn = QPushButton("Load URLs")
        self.load_btn.clicked.connect(self.load_urls_from_file)
        
        self.start_batch_btn = QPushButton("Start Batch Download")
        self.start_batch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        
        control_layout.addWidget(self.load_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.start_batch_btn)
        
        layout.addLayout(control_layout)
        
        layout.addStretch()
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Batch Download")
        
    def setup_logs_tab(self):
        """Setup the logs tab"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Log type selector
        log_type_layout = QHBoxLayout()
        log_type_layout.addWidget(QLabel("Log Type:"))
        
        self.log_combo = QComboBox()
        self.log_combo.addItems(["Success", "Failed", "Error", "Console"])
        self.log_combo.currentTextChanged.connect(self.update_log_display)
        log_type_layout.addWidget(self.log_combo)
        
        self.clear_log_btn = QPushButton("Clear Log")
        self.clear_log_btn.clicked.connect(self.clear_current_log)
        log_type_layout.addWidget(self.clear_log_btn)
        
        log_type_layout.addStretch()
        layout.addLayout(log_type_layout)
        
        # Log display
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.log_text)
        
        # Refresh button
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        
        self.refresh_logs_btn = QPushButton("Refresh All Logs")
        self.refresh_logs_btn.clicked.connect(self.refresh_all_logs)
        refresh_layout.addWidget(self.refresh_logs_btn)
        
        layout.addLayout(refresh_layout)
        
        tab.setLayout(layout)
        self.tab_widget.addTab(tab, "Logs")
        
    def setup_connections(self):
        """Setup signal connections"""
        # Buttons
        self.download_btn.clicked.connect(self.start_download)
        self.start_batch_btn.clicked.connect(self.start_batch_download)
        self.settings_btn.clicked.connect(self.show_settings)
        self.validate_btn.clicked.connect(self.validate_urls)
        self.stop_btn.clicked.connect(self.stop_download)
        
        # Tab change
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
    def start_log_monitor(self):
        """Start monitoring log files"""
        log_files = {
            "Success": SUCCESS_LOG,
            "Failed": FAILED_LOG,
            "Error": ERROR_LOG
        }
        
        self.log_monitor = LogMonitor(log_files)
        self.log_monitor.log_updated.connect(self.on_log_updated)
        self.log_monitor.start()
        
    def on_log_updated(self, log_type: str, content: str):
        """Handle log updates"""
        if self.log_combo.currentText() == log_type:
            cursor = self.log_text.textCursor()
            cursor.movePosition(QTextCursor.End)
            cursor.insertText(content)
            self.log_text.setTextCursor(cursor)
            self.log_text.ensureCursorVisible()
            
    def update_log_display(self, log_type: str):
        """Update log display when type changes"""
        self.log_text.clear()
        
        log_file_map = {
            "Success": SUCCESS_LOG,
            "Failed": FAILED_LOG,
            "Error": ERROR_LOG,
            "Console": None  # Console log is in-memory
        }
        
        if log_type in log_file_map and log_file_map[log_type]:
            filepath = log_file_map[log_type]
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.log_text.setText(f.read())
                except:
                    self.log_text.setText(f"Error reading {log_type} log")
        elif log_type == "Console":
            # For console log, we'd need to capture stdout/stderr
            # This is a placeholder - you'd need to implement proper console capture
            self.log_text.setText("Console output would appear here...")
            
    def clear_current_log(self):
        """Clear the currently displayed log"""
        log_type = self.log_combo.currentText()
        log_file_map = {
            "Success": SUCCESS_LOG,
            "Failed": FAILED_LOG,
            "Error": ERROR_LOG
        }
        
        if log_type in log_file_map:
            filepath = log_file_map[log_type]
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write("")
                    self.log_text.clear()
                    QMessageBox.information(self, "Log Cleared", f"{log_type} log has been cleared.")
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Could not clear log: {e}")
                    
    def refresh_all_logs(self):
        """Refresh all log displays"""
        current_log = self.log_combo.currentText()
        self.update_log_display(current_log)
        
    def paste_url(self):
        """Paste URL from clipboard"""
        clipboard = QApplication.clipboard()
        self.url_edit.setText(clipboard.text())
        
    def clear_url(self):
        """Clear URL field"""
        self.url_edit.clear()
        
    def browse_batch_file(self):
        """Browse for batch file"""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Select Text File", 
            str(Path.home()), 
            "Text Files (*.txt);;All Files (*.*)"
        )
        if filepath:
            self.file_edit.setText(filepath)
            self.load_urls_from_file()
            
    def load_urls_from_file(self):
        """Load URLs from selected file"""
        filepath = self.file_edit.text()
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, "Error", "Please select a valid file first.")
            return
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
            self.url_list.clear()
            for url in urls:
                item = QListWidgetItem(url)
                # Validate URL color coding
                if self.downloader.validate_youtube_url(url):
                    item.setForeground(Qt.darkGreen)
                else:
                    item.setForeground(Qt.red)
                self.url_list.addItem(item)
                
            self.status_label.setText(f"Loaded {len(urls)} URLs from file")
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load file: {e}")
            
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.downloader, self)
        if dialog.exec():
            settings = dialog.get_settings()
            
            # Update downloader
            self.downloader._Youtube_Downloader__output_directory = Path(settings["output_dir"])
            self.downloader._Youtube_Downloader__audio_quality = settings["audio_quality"]
            self.downloader._Youtube_Downloader__audio_format = settings["audio_format"]
            self.downloader._Youtube_Downloader__parallel_downloads = settings["max_parallel_downloads"]
            
            # Save to config file
            config_file = self.downloader._Youtube_Downloader__configuration_file
            try:
                with open(config_file, 'w') as f:
                    json.dump(settings, f, indent=2)
                QMessageBox.information(self, "Settings Saved", "Settings have been saved successfully.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not save settings: {e}")
                
    def validate_urls(self):
        """Validate URLs in the current view"""
        if self.tab_widget.currentIndex() == 0:  # Single download tab
            url = self.url_edit.text().strip()
            if not url:
                QMessageBox.warning(self, "Warning", "Please enter a URL first.")
                return
                
            self.status_label.setText("Validating URL...")
            QApplication.processEvents()
            
            if self.downloader.validate_youtube_url(url):
                valid, message, _ = self.downloader.resource_validation(url)
                if valid:
                    QMessageBox.information(self, "Valid", f"URL is valid and accessible.\n{message}")
                else:
                    QMessageBox.warning(self, "Invalid", f"URL may not be accessible: {message}")
            else:
                QMessageBox.warning(self, "Invalid", "URL is not a valid YouTube/YouTube Music URL.")
                
        elif self.tab_widget.currentIndex() == 1:  # Batch tab
            if self.url_list.count() == 0:
                QMessageBox.warning(self, "Warning", "Please load URLs first.")
                return
                
            valid_count = 0
            total_count = self.url_list.count()
            
            self.status_label.setText(f"Validating {total_count} URLs...")
            
            for i in range(self.url_list.count()):
                item = self.url_list.item(i)
                url = item.text()
                
                if self.downloader.validate_youtube_url(url):
                    valid, _, _ = self.downloader.resource_validation(url)
                    if valid:
                        valid_count += 1
                        item.setForeground(Qt.darkGreen)
                    else:
                        item.setForeground(Qt.darkYellow)
                else:
                    item.setForeground(Qt.red)
                    
                QApplication.processEvents()
                
            self.status_label.setText(f"Validation complete: {valid_count}/{total_count} valid URLs")
            
    def start_download(self):
        """Start a single download"""
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Error", "Please enter a URL.")
            return
            
        if not self.downloader.validate_youtube_url(url):
            QMessageBox.warning(self, "Error", "Invalid YouTube/YouTube Music URL.")
            return
            
        download_type = self.type_combo.currentText().lower()
        
        # Disable controls
        self.download_btn.setEnabled(False)
        self.settings_btn.setEnabled(False)
        self.validate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText(f"Starting {download_type} download...")
        
        # Create worker and thread
        self.download_worker = DownloadWorker(self.downloader, url, download_type)
        self.download_thread = QThread()
        
        self.download_worker.moveToThread(self.download_thread)
        
        # Connect signals
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.status.connect(self.on_download_status)
        self.download_worker.finished.connect(self.on_download_finished)
        
        self.download_thread.started.connect(self.download_worker.run)
        self.download_thread.finished.connect(self.download_thread.deleteLater)
        
        # Start thread
        self.download_thread.start()
        
    def start_batch_download(self):
        """Start batch download"""
        filepath = self.file_edit.text()
        if not filepath or not os.path.exists(filepath):
            QMessageBox.warning(self, "Error", "Please select a valid file first.")
            return
            
        # Disable controls
        self.start_batch_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.settings_btn.setEnabled(False)
        self.validate_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("Starting batch download...")
        
        # Create worker and thread
        self.batch_worker = BatchDownloadWorker(self.downloader, filepath)
        self.batch_thread = QThread()
        
        self.batch_worker.moveToThread(self.batch_thread)
        
        # Connect signals
        self.batch_worker.progress.connect(self.on_batch_progress)
        self.batch_worker.item_complete.connect(self.on_batch_item_complete)
        self.batch_worker.status.connect(self.on_download_status)
        self.batch_worker.finished.connect(self.on_batch_finished)
        
        self.batch_thread.started.connect(self.batch_worker.run)
        self.batch_thread.finished.connect(self.batch_thread.deleteLater)
        
        # Start thread
        self.batch_thread.start()
        
    def stop_download(self):
        """Stop current download"""
        if self.download_worker:
            self.download_worker.stop()
            self.download_thread.quit()
            self.download_thread.wait()
            
        if self.batch_worker:
            self.batch_worker.stop()
            self.batch_thread.quit()
            self.batch_thread.wait()
            
        self.status_label.setText("Download stopped by user.")
        self.reset_controls()
        
    def on_download_progress(self, url: str, percentage: int):
        """Handle download progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Downloading: {url} ({percentage}%)")
        
    def on_batch_progress(self, current_url: str, percentage: int):
        """Handle batch download progress"""
        self.progress_bar.setValue(percentage)
        self.status_label.setText(f"Batch: {current_url[:50]}... ({percentage}%)")
        
    def on_batch_item_complete(self, url: str, success: bool, message: str):
        """Handle batch item completion"""
        # Update list item color
        for i in range(self.url_list.count()):
            item = self.url_list.item(i)
            if item.text() == url:
                if success:
                    item.setForeground(Qt.darkGreen)
                else:
                    item.setForeground(Qt.red)
                break
                
    def on_download_status(self, status_type: str, message: str):
        """Handle status updates"""
        self.status_label.setText(f"{status_type}: {message}")
        
    def on_download_finished(self, success: bool, message: str):
        """Handle download completion"""
        self.download_thread.quit()
        self.download_thread.wait()
        
        if success:
            self.status_label.setText(f"Download completed successfully! {message}")
            QMessageBox.information(self, "Success", "Download completed successfully!")
        else:
            self.status_label.setText(f"Download failed: {message}")
            QMessageBox.warning(self, "Error", f"Download failed: {message}")
            
        self.reset_controls()
        
    def on_batch_finished(self, success: bool, message: str):
        """Handle batch download completion"""
        self.batch_thread.quit()
        self.batch_thread.wait()
        
        self.status_label.setText(f"Batch download complete: {message}")
        
        if success:
            QMessageBox.information(self, "Batch Complete", message)
        else:
            QMessageBox.warning(self, "Batch Error", message)
            
        self.reset_controls()
        
    def reset_controls(self):
        """Reset control states"""
        self.download_btn.setEnabled(True)
        self.start_batch_btn.setEnabled(True)
        self.load_btn.setEnabled(True)
        self.settings_btn.setEnabled(True)
        self.validate_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        
    def on_tab_changed(self, index: int):
        """Handle tab changes"""
        if index == 1:  # Batch tab
            if self.file_edit.text():
                self.load_urls_from_file()
                
    def closeEvent(self, event):
        """Handle window close"""
        if self.log_monitor:
            self.log_monitor.stop()
            self.log_monitor.wait()
            
        if self.download_thread and self.download_thread.isRunning():
            self.stop_download()
            
        if self.batch_thread and self.batch_thread.isRunning():
            self.stop_download()
            
        event.accept()

def main():
    """Main function to run the GUI"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Check for yt-dlp
    if not shutil.which("yt-dlp"):
        reply = QMessageBox.question(
            None, "yt-dlp Required",
            "yt-dlp is not installed. Do you want to install it now?\n\n"
            "This will run: pip install yt-dlp",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], 
                             check=True, capture_output=True)
                QMessageBox.information(None, "Success", "yt-dlp installed successfully!")
            except subprocess.CalledProcessError as e:
                QMessageBox.critical(
                    None, "Installation Failed",
                    f"Failed to install yt-dlp. Please install manually:\n\n"
                    f"pip install yt-dlp\n\nError: {e.stderr.decode() if e.stderr else str(e)}"
                )
                sys.exit(1)
        else:
            QMessageBox.warning(
                None, "Warning",
                "yt-dlp is required for this program to work.\n"
                "Please install it manually using: pip install yt-dlp"
            )
            sys.exit(1)
    
    window = YouTubeDownloaderGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()