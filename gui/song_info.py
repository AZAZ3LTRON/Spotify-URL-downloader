import sys
import json
import re
import requests
from datetime import datetime
from typing import Optional, Dict, List, Union
from dataclasses import dataclass
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
import urllib.request
import tempfile
import os

# ================== Data Models ==================
@dataclass
class MusicInfo:
    """Data class for music information"""
    source: str  # "spotify" or "youtube"
    url: str
    title: str
    type: str  # "track", "album", "playlist"
    artist: str = "Unknown"
    duration: Optional[str] = None  # For tracks
    track_count: Optional[int] = None  # For albums/playlists
    release_date: Optional[str] = None  # For albums
    thumbnail_url: Optional[str] = None
    tracks: List[str] = None  # List of track names
    
    def __post_init__(self):
        if self.tracks is None:
            self.tracks = []
    
    def get_summary(self) -> str:
        """Get formatted summary of the music info"""
        if self.type == "track":
            return f"🎵 {self.title}\n🎤 {self.artist}\n⏱️ {self.duration}"
        elif self.type == "album":
            return f"💿 {self.title}\n🎤 {self.artist}\n📅 {self.release_date}\n🎶 {self.track_count} tracks"
        elif self.type == "playlist":
            return f"📋 {self.title}\n🎶 {self.track_count} tracks"
        return ""

# ================== Music Information Fetcher ==================
class MusicInfoFetcher:
    """Fetches music information from Spotify and YouTube Music URLs"""
    
    @staticmethod
    def fetch_from_spotify(url: str) -> Optional[MusicInfo]:
        """Fetch information from Spotify URL"""
        try:
            # Extract Spotify ID and type from URL
            pattern = r'spotify\.com/(track|album|playlist)/([a-zA-Z0-9]+)'
            match = re.search(pattern, url)
            
            if not match:
                return None
            
            item_type = match.group(1)
            item_id = match.group(2)
            
            # Note: Spotify API requires authentication in production
            # For demo purposes, we'll use mock data
            return MusicInfoFetcher._get_mock_spotify_data(item_type, item_id, url)
            
        except Exception as e:
            print(f"Error fetching Spotify data: {e}")
            return None
    
    @staticmethod
    def fetch_from_youtube(url: str) -> Optional[MusicInfo]:
        """Fetch information from YouTube Music URL"""
        try:
            # Extract YouTube ID and type from URL
            patterns = {
                'track': r'(?:youtube\.com/watch\?v=|youtu\.be/|music\.youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)',
                'playlist': r'(?:youtube\.com/playlist\?list=|music\.youtube\.com/playlist\?list=)([a-zA-Z0-9_-]+)',
                'album': r'music\.youtube\.com/album/([a-zA-Z0-9_-]+)'
            }
            
            for item_type, pattern in patterns.items():
                match = re.search(pattern, url)
                if match:
                    item_id = match.group(1)
                    # Note: YouTube API requires authentication
                    # For demo purposes, we'll use mock data
                    return MusicInfoFetcher._get_mock_youtube_data(item_type, item_id, url)
            
            return None
            
        except Exception as e:
            print(f"Error fetching YouTube data: {e}")
            return None
    
    @staticmethod
    def _get_mock_spotify_data(item_type: str, item_id: str, url: str) -> MusicInfo:
        """Generate mock Spotify data for demonstration"""
        mock_data = {
            "track": {
                "title": "Blinding Lights",
                "artist": "The Weeknd",
                "duration": "3:22",
                "thumbnail": "https://i.scdn.co/image/ab67616d0000b2738863bc11d2aa12b54f5aeb36"
            },
            "album": {
                "title": "After Hours",
                "artist": "The Weeknd",
                "track_count": 14,
                "release_date": "2020-03-20",
                "thumbnail": "https://i.scdn.co/image/ab67616d0000b2738863bc11d2aa12b54f5aeb36"
            },
            "playlist": {
                "title": "Today's Top Hits",
                "track_count": 50,
                "thumbnail": "https://i.scdn.co/image/ab67706f00000002fe24d7084be472288cd6ee6c"
            }
        }
        
        data = mock_data.get(item_type, {})
        
        if item_type == "track":
            return MusicInfo(
                source="spotify",
                url=url,
                title=data.get("title", "Unknown Track"),
                type="track",
                artist=data.get("artist", "Unknown Artist"),
                duration=data.get("duration", "0:00"),
                thumbnail_url=data.get("thumbnail")
            )
        elif item_type == "album":
            return MusicInfo(
                source="spotify",
                url=url,
                title=data.get("title", "Unknown Album"),
                type="album",
                artist=data.get("artist", "Unknown Artist"),
                track_count=data.get("track_count", 0),
                release_date=data.get("release_date", "Unknown"),
                thumbnail_url=data.get("thumbnail")
            )
        elif item_type == "playlist":
            return MusicInfo(
                source="spotify",
                url=url,
                title=data.get("title", "Unknown Playlist"),
                type="playlist",
                track_count=data.get("track_count", 0),
                thumbnail_url=data.get("thumbnail")
            )
        
        return None
    
    @staticmethod
    def _get_mock_youtube_data(item_type: str, item_id: str, url: str) -> MusicInfo:
        """Generate mock YouTube Music data for demonstration"""
        mock_data = {
            "track": {
                "title": "Stay",
                "artist": "The Kid LAROI, Justin Bieber",
                "duration": "2:21",
                "thumbnail": "https://i.ytimg.com/vi/kTJczUoc26U/maxresdefault.jpg"
            },
            "album": {
                "title": "Justice",
                "artist": "Justin Bieber",
                "track_count": 16,
                "release_date": "2021-03-19",
                "thumbnail": "https://i.ytimg.com/vi/1B0gKQ5YQvI/maxresdefault.jpg"
            },
            "playlist": {
                "title": "YouTube Music Mix",
                "track_count": 100,
                "thumbnail": "https://i.ytimg.com/vi/7NOSDKb0HlU/maxresdefault.jpg"
            }
        }
        
        data = mock_data.get(item_type, {})
        
        if item_type == "track":
            return MusicInfo(
                source="youtube",
                url=url,
                title=data.get("title", "Unknown Track"),
                type="track",
                artist=data.get("artist", "Unknown Artist"),
                duration=data.get("duration", "0:00"),
                thumbnail_url=data.get("thumbnail")
            )
        elif item_type == "album":
            return MusicInfo(
                source="youtube",
                url=url,
                title=data.get("title", "Unknown Album"),
                type="album",
                artist=data.get("artist", "Unknown Artist"),
                track_count=data.get("track_count", 0),
                release_date=data.get("release_date", "Unknown"),
                thumbnail_url=data.get("thumbnail")
            )
        elif item_type == "playlist":
            return MusicInfo(
                source="youtube",
                url=url,
                title=data.get("title", "Unknown Playlist"),
                type="playlist",
                track_count=data.get("track_count", 0),
                thumbnail_url=data.get("thumbnail")
            )
        
        return None

# ================== Music Info Page ==================
class MusicInfoPage(QWidget):
    """Page for fetching and displaying music information from URLs"""
    
    def __init__(self):
        super().__init__()
        self.music_info = None
        self.thumbnail_pixmap = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(25)
        
        # Title
        title_label = QLabel("🎵 Music Information Fetcher")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
                padding-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "Enter a Spotify or YouTube Music URL to fetch information about tracks, albums, or playlists."
        )
        desc_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
                padding-bottom: 20px;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # URL Input Section
        url_frame = QFrame()
        url_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 12px;
                border: 2px solid #444444;
            }
        """)
        
        url_layout = QVBoxLayout()
        url_layout.setContentsMargins(25, 20, 25, 20)
        
        # URL input
        url_input_layout = QHBoxLayout()
        url_label = QLabel("Enter URL:")
        url_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: bold;
                min-width: 100px;
            }
        """)
        url_input_layout.addWidget(url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste Spotify or YouTube Music URL here...")
        self.url_input.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #ffffff;
                border: 2px solid #555555;
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                selection-background-color: #0078d7;
            }
            QLineEdit:focus {
                border: 2px solid #0078d7;
                background-color: #252525;
            }
            QLineEdit:hover {
                border: 2px solid #666666;
            }
        """)
        url_input_layout.addWidget(self.url_input, 1)
        
        # Clear button
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedSize(80, 50)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #555555;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #666666;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        clear_btn.clicked.connect(self.clear_input)
        url_input_layout.addWidget(clear_btn)
        
        url_layout.addLayout(url_input_layout)
        
        # Platform selection
        platform_layout = QHBoxLayout()
        platform_layout.setSpacing(20)
        
        self.spotify_radio = QRadioButton("Spotify")
        self.spotify_radio.setChecked(True)
        self.youtube_radio = QRadioButton("YouTube Music")
        self.auto_radio = QRadioButton("Auto-detect")
        
        for radio in [self.spotify_radio, self.youtube_radio, self.auto_radio]:
            radio.setStyleSheet("""
                QRadioButton {
                    color: #cccccc;
                    font-size: 14px;
                    padding: 8px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
                QRadioButton::indicator:checked {
                    background-color: #1DB954;
                    border: 2px solid #ffffff;
                    border-radius: 9px;
                }
                QRadioButton::indicator:unchecked {
                    background-color: #444444;
                    border: 2px solid #666666;
                    border-radius: 9px;
                }
            """)
            platform_layout.addWidget(radio)
        
        platform_layout.addStretch()
        url_layout.addLayout(platform_layout)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # Insert sample URLs button
        sample_btn = QPushButton("📋 Insert Sample URL")
        sample_btn.setStyleSheet("""
            QPushButton {
                background-color: #3a3a3a;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2a2a2a;
            }
        """)
        sample_btn.clicked.connect(self.insert_sample_url)
        button_layout.addWidget(sample_btn)
        
        button_layout.addStretch()
        
        # Fetch button
        fetch_btn = QPushButton("🎵 Fetch Music Info")
        fetch_btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 30px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1ed760;
            }
            QPushButton:pressed {
                background-color: #1aa34a;
            }
        """)
        fetch_btn.clicked.connect(self.fetch_music_info)
        button_layout.addWidget(fetch_btn)
        
        url_layout.addLayout(button_layout)
        url_frame.setLayout(url_layout)
        layout.addWidget(url_frame)
        
        # Results Section
        results_label = QLabel("🎵 Music Information")
        results_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                padding-top: 10px;
            }
        """)
        layout.addWidget(results_label)
        
        # Results container
        self.results_frame = QFrame()
        self.results_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                border: 2px dashed #444444;
            }
        """)
        self.results_frame.setMinimumHeight(300)
        
        results_layout = QVBoxLayout()
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        # No results placeholder
        self.no_results_label = QLabel("No music information fetched yet.\nEnter a URL and click 'Fetch Music Info'.")
        self.no_results_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 16px;
                font-style: italic;
            }
        """)
        self.no_results_label.setAlignment(Qt.AlignCenter)
        results_layout.addWidget(self.no_results_label)
        
        # Results content (initially hidden)
        self.results_content = QWidget()
        self.results_content.hide()
        
        results_content_layout = QVBoxLayout()
        results_content_layout.setContentsMargins(25, 20, 25, 20)
        
        # Thumbnail and basic info
        top_layout = QHBoxLayout()
        
        # Thumbnail
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setFixedSize(180, 180)
        self.thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                border-radius: 10px;
                border: 2px solid #444444;
            }
        """)
        self.thumbnail_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(self.thumbnail_label)
        
        # Basic info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        
        self.title_label = QLabel()
        self.title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        info_layout.addWidget(self.title_label)
        
        self.artist_label = QLabel()
        self.artist_label.setStyleSheet("""
            QLabel {
                color: #1DB954;
                font-size: 18px;
            }
        """)
        info_layout.addWidget(self.artist_label)
        
        self.type_label = QLabel()
        self.type_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 14px;
                font-style: italic;
            }
        """)
        info_layout.addWidget(self.type_label)
        
        info_layout.addStretch()
        top_layout.addLayout(info_layout, 1)
        
        results_content_layout.addLayout(top_layout)
        
        # Details
        details_frame = QFrame()
        details_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 8px;
                border: 1px solid #444444;
            }
        """)
        
        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(20, 15, 20, 15)
        
        # Details grid
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(30)
        details_grid.setVerticalSpacing(15)
        
        # Source
        source_title = QLabel("Source:")
        source_title.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        self.source_value = QLabel()
        self.source_value.setStyleSheet("color: #ffffff;")
        details_grid.addWidget(source_title, 0, 0)
        details_grid.addWidget(self.source_value, 0, 1)
        
        # Duration/Track Count
        self.detail1_title = QLabel()
        self.detail1_title.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        self.detail1_value = QLabel()
        self.detail1_value.setStyleSheet("color: #ffffff;")
        details_grid.addWidget(self.detail1_title, 1, 0)
        details_grid.addWidget(self.detail1_value, 1, 1)
        
        # Release Date (for albums)
        self.detail2_title = QLabel()
        self.detail2_title.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        self.detail2_value = QLabel()
        self.detail2_value.setStyleSheet("color: #ffffff;")
        details_grid.addWidget(self.detail2_title, 2, 0)
        details_grid.addWidget(self.detail2_value, 2, 1)
        
        # URL
        url_title = QLabel("URL:")
        url_title.setStyleSheet("color: #aaaaaa; font-weight: bold;")
        self.url_value = QLabel()
        self.url_value.setStyleSheet("color: #1DB954;")
        self.url_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        details_grid.addWidget(url_title, 3, 0)
        details_grid.addWidget(self.url_value, 3, 1)
        
        details_layout.addLayout(details_grid)
        details_frame.setLayout(details_layout)
        
        results_content_layout.addWidget(details_frame)
        
        # Copy button
        copy_btn = QPushButton("📋 Copy Information")
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1088e7;
            }
            QPushButton:pressed {
                background-color: #0068c7;
            }
        """)
        copy_btn.clicked.connect(self.copy_info_to_clipboard)
        results_content_layout.addWidget(copy_btn)
        
        self.results_content.setLayout(results_content_layout)
        results_layout.addWidget(self.results_content)
        
        self.results_frame.setLayout(results_layout)
        layout.addWidget(self.results_frame, 1)
        
        self.setLayout(layout)
        
    def clear_input(self):
        """Clear the URL input field"""
        self.url_input.clear()
        
    def insert_sample_url(self):
        """Insert a sample URL based on selected platform"""
        sample_urls = {
            "spotify": {
                "track": "https://open.spotify.com/track/0VjIjW4GlUZAMYd2vXMi3b",
                "album": "https://open.spotify.com/album/4yP0hdKOZPNshxUOjY0cZj",
                "playlist": "https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M"
            },
            "youtube": {
                "track": "https://music.youtube.com/watch?v=kTJczUoc26U",
                "album": "https://music.youtube.com/playlist?list=OLAK5uy_n8h5WCx2E7YQnE1hE_5WkNG98pzbN1r0w",
                "playlist": "https://music.youtube.com/playlist?list=RDCLAK5uy_lpVSQKqEKjC38lJ69Yt8sOZqsn_-DvUfU"
            }
        }
        
        platform = "spotify" if self.spotify_radio.isChecked() else "youtube"
        
        # Show selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Sample URL")
        dialog.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
        """)
        
        layout = QVBoxLayout()
        layout.addWidget(QLabel(f"Select a {platform.capitalize()} sample URL:"))
        
        track_btn = QPushButton("🎵 Track")
        album_btn = QPushButton("💿 Album")
        playlist_btn = QPushButton("📋 Playlist")
        
        for btn in [track_btn, album_btn, playlist_btn]:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #3a3a3a;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px;
                    margin: 5px;
                }
                QPushButton:hover {
                    background-color: #4a4a4a;
                }
            """)
            layout.addWidget(btn)
        
        def insert_url(url_type):
            url = sample_urls[platform][url_type]
            self.url_input.setText(url)
            dialog.accept()
        
        track_btn.clicked.connect(lambda: insert_url("track"))
        album_btn.clicked.connect(lambda: insert_url("album"))
        playlist_btn.clicked.connect(lambda: insert_url("playlist"))
        
        dialog.setLayout(layout)
        dialog.exec()
        
    def fetch_music_info(self):
        """Fetch music information from the entered URL"""
        url = self.url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Input Required", "Please enter a URL.")
            return
        
        # Determine platform
        platform = None
        if self.spotify_radio.isChecked() or "spotify.com" in url:
            platform = "spotify"
        elif self.youtube_radio.isChecked() or any(x in url for x in ["youtube.com", "youtu.be"]):
            platform = "youtube"
        elif self.auto_radio.isChecked():
            if "spotify.com" in url:
                platform = "spotify"
            elif any(x in url for x in ["youtube.com", "youtu.be"]):
                platform = "youtube"
        
        if not platform:
            QMessageBox.warning(self, "Invalid URL", 
                               "Please enter a valid Spotify or YouTube Music URL.")
            return
        
        # Show loading
        self.no_results_label.setText("Fetching music information...")
        self.no_results_label.show()
        self.results_content.hide()
        QApplication.processEvents()
        
        # Fetch music info
        if platform == "spotify":
            self.music_info = MusicInfoFetcher.fetch_from_spotify(url)
        else:
            self.music_info = MusicInfoFetcher.fetch_from_youtube(url)
        
        if self.music_info:
            self.display_music_info()
        else:
            self.no_results_label.setText("Could not fetch music information.\nPlease check the URL and try again.")
            QMessageBox.warning(self, "Fetch Error", 
                               "Could not fetch music information. Please check the URL.")
    
    def display_music_info(self):
        """Display the fetched music information"""
        if not self.music_info:
            return
        
        # Update thumbnail
        self.thumbnail_label.clear()
        if self.music_info.thumbnail_url:
            # Load thumbnail in background
            self.load_thumbnail(self.music_info.thumbnail_url)
        else:
            # Create placeholder thumbnail
            pixmap = QPixmap(180, 180)
            pixmap.fill(QColor("#1e1e1e"))
            painter = QPainter(pixmap)
            painter.setPen(QColor("#444444"))
            painter.setFont(QFont("Arial", 36))
            
            # Draw icon based on type
            icon_text = "🎵" if self.music_info.type == "track" else "💿" if self.music_info.type == "album" else "📋"
            painter.drawText(pixmap.rect(), Qt.AlignCenter, icon_text)
            painter.end()
            
            self.thumbnail_label.setPixmap(pixmap)
        
        # Update labels
        self.title_label.setText(self.music_info.title)
        
        if self.music_info.artist and self.music_info.artist != "Unknown":
            self.artist_label.setText(f"by {self.music_info.artist}")
            self.artist_label.show()
        else:
            self.artist_label.hide()
        
        source_icon = "🎵" if self.music_info.source == "spotify" else "▶️"
        self.type_label.setText(f"{source_icon} {self.music_info.type.capitalize()}")
        
        # Update source
        source_text = "Spotify" if self.music_info.source == "spotify" else "YouTube Music"
        self.source_value.setText(f"{source_text}")
        
        # Update details based on type
        if self.music_info.type == "track":
            self.detail1_title.setText("Duration:")
            self.detail1_value.setText(self.music_info.duration or "Unknown")
            self.detail2_title.setText("")
            self.detail2_value.setText("")
        elif self.music_info.type == "album":
            self.detail1_title.setText("Track Count:")
            self.detail1_value.setText(str(self.music_info.track_count) if self.music_info.track_count else "Unknown")
            self.detail2_title.setText("Release Date:")
            self.detail2_value.setText(self.music_info.release_date or "Unknown")
        elif self.music_info.type == "playlist":
            self.detail1_title.setText("Track Count:")
            self.detail1_value.setText(str(self.music_info.track_count) if self.music_info.track_count else "Unknown")
            self.detail2_title.setText("")
            self.detail2_value.setText("")
        
        # Update URL (shortened)
        short_url = self.music_info.url
        if len(short_url) > 50:
            short_url = short_url[:47] + "..."
        self.url_value.setText(short_url)
        
        # Show results
        self.no_results_label.hide()
        self.results_content.show()
    
    def load_thumbnail(self, url: str):
        """Load thumbnail image from URL"""
        try:
            # Download image in a separate thread to avoid blocking UI
            def download_image():
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        image_data = response.read()
                    
                    pixmap = QPixmap()
                    pixmap.loadFromData(image_data)
                    return pixmap.scaled(180, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                except:
                    return None
            
            # Create a simple placeholder while downloading
            placeholder = QPixmap(180, 180)
            placeholder.fill(QColor("#2d2d2d"))
            painter = QPainter(placeholder)
            painter.setPen(QColor("#555555"))
            painter.drawText(placeholder.rect(), Qt.AlignCenter, "Loading...")
            painter.end()
            
            self.thumbnail_label.setPixmap(placeholder)
            
            # Download in background (simplified for demo)
            QTimer.singleShot(500, lambda: self.set_thumbnail(download_image()))
            
        except Exception as e:
            print(f"Error loading thumbnail: {e}")
    
    def set_thumbnail(self, pixmap: Optional[QPixmap]):
        """Set the thumbnail image"""
        if pixmap and not pixmap.isNull():
            self.thumbnail_label.setPixmap(pixmap)
        else:
            # Create error thumbnail
            error_pixmap = QPixmap(180, 180)
            error_pixmap.fill(QColor("#2d2d2d"))
            painter = QPainter(error_pixmap)
            painter.setPen(QColor("#ff5555"))
            painter.setFont(QFont("Arial", 16))
            painter.drawText(error_pixmap.rect(), Qt.AlignCenter, "No Image")
            painter.end()
            self.thumbnail_label.setPixmap(error_pixmap)
    
    def copy_info_to_clipboard(self):
        """Copy music information to clipboard"""
        if not self.music_info:
            return
        
        clipboard = QApplication.clipboard()
        
        # Format the information
        info_text = f"""🎵 Music Information

Title: {self.music_info.title}
Type: {self.music_info.type.capitalize()}
Source: {"Spotify" if self.music_info.source == "spotify" else "YouTube Music"}

"""
        
        if self.music_info.artist and self.music_info.artist != "Unknown":
            info_text += f"Artist: {self.music_info.artist}\n"
        
        if self.music_info.type == "track" and self.music_info.duration:
            info_text += f"Duration: {self.music_info.duration}\n"
        elif self.music_info.type in ["album", "playlist"] and self.music_info.track_count:
            info_text += f"Track Count: {self.music_info.track_count}\n"
        
        if self.music_info.type == "album" and self.music_info.release_date:
            info_text += f"Release Date: {self.music_info.release_date}\n"
        
        info_text += f"\nURL: {self.music_info.url}"
        
        clipboard.setText(info_text)
        QMessageBox.information(self, "Copied", "Music information copied to clipboard!")

# ================== Simplified Page Classes ==================
class PageWidget(QWidget):
    """Base class for all pages"""
    def __init__(self, page_name):
        super().__init__()
        self.page_name = page_name
        self.setup_ui()
    
    def setup_ui(self):
        """Implemented by subclasses"""
        pass

# Update DownloadPage to be the music info page
class DownloadPage(MusicInfoPage):
    def __init__(self):
        super().__init__()

class BatchDownloadPage(PageWidget):
    def __init__(self):
        super().__init__("Batch Download")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Batch Download Page - Coming Soon")
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)

class SettingsPage(PageWidget):
    def __init__(self):
        super().__init__("Settings")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Settings Page - Coming Soon")
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)

class LogsPage(PageWidget):
    def __init__(self):
        super().__init__("Logs")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Logs Page - Coming Soon")
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)

class InfoPage(PageWidget):
    def __init__(self):
        super().__init__("Info")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("Info Page - Coming Soon")
        label.setStyleSheet("color: white; font-size: 24px;")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        self.setLayout(layout)

# ================================== Sidebar Classes ===========================================
class ImageButton(QPushButton):
    """Custom button that displays an image with hover effects, works with Sidebar class"""
    def __init__(self, image_path, text="", parent=None):
        super().__init__(parent)
        self.button_name = text
        self.is_selected = False
        
        # Load and scale the image if it exists
        if os.path.exists(image_path):
            self.icon = QIcon(image_path)
        else:
            # Create a fallback icon
            pixmap = QPixmap(40, 40)
            pixmap.fill(QColor("#444444"))
            painter = QPainter(pixmap)
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Arial", 16))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, text[0] if text else "?")
            painter.end()
            self.icon = QIcon(pixmap)
            
        self.setIcon(self.icon)
        self.setIconSize(QSize(40, 40))
        self.setFixedSize(70, 70)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(text)
        self.update_style()
    
    def update_style(self):
        """Update button style based on selection state"""
        if self.is_selected:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #4a4a4a;
                    border: 1px solid #6a6a6a;
                    border-radius: 8px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #5a5a5a;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #2d2d2d;
                    border: none;
                    border-radius: 8px;
                    padding: 5px;
                }
                QPushButton:hover {
                    background-color: #3a3a3a;
                    border: 1px solid #5a5a6a;
                }
            """)
    
    def set_selected(self, selected):
        """Set the selection state of the button"""
        self.is_selected = selected
        self.update_style()

class Sidebar(QWidget):
    """Main sidebar widget containing image buttons"""
    buttonClicked = Signal(str)
    
    def __init__(self):
        super().__init__()
        self.buttons = {}
        self.current_button = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(15)
        
        # Title
        title_widget = QWidget()
        title_widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                padding: 10px;
                border-bottom: 1px solid #444;
            }
        """)
        title_widget.setFixedHeight(60)
        
        title_layout = QHBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        icon_label = QLabel("🎵")
        icon_label.setStyleSheet("font-size: 24px;")
        title_layout.addWidget(icon_label)
        
        title_label = QLabel("Yt DLP")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        title_widget.setLayout(title_layout)
        layout.addWidget(title_widget)
        
        # Buttons
        button_configs = [
            ("download", "Download"),
            ("batch_download", "Batch"),
            ("settings", "Settings"),
            ("theme", "Theme"),
            ("log", "Logs"),
            ("info", "Info")
        ]
        
        for image_name, button_text in button_configs:
            btn = ImageButton(self.get_image_path(image_name), button_text)
            btn.clicked.connect(lambda checked, name=button_text: self.on_button_clicked(name))
            self.buttons[button_text] = btn
            layout.addWidget(btn)
        
        layout.addStretch()
        self.setLayout(layout)
        self.setStyleSheet("QWidget { background-color: #2D2D2D; }")
        self.select_button("Download")
    
    def get_image_path(self, image_name):
        """Helper method to get image path from assets folder"""
        base_path = r"C:\Users\Ayomide Ajimuda\Documents\Projects\Personal\Music-URL-downloader\assets"
        filename_map = {
            "download": "download_icon.png",
            "batch_download": "batch_download_icon.png",
            "settings": "settings_icon.png",
            "theme": "theme_icon.png",
            "log": "log_icon.png",
            "info": "info_icon.png",
            "main": "main_icon.png"
        }
        
        filename = filename_map.get(image_name, f"{image_name}_icon.png")
        full_path = os.path.join(base_path, filename)
        
        if os.path.exists(full_path):
            return full_path
        
        print(f"Warning: Image not found for {image_name} at {full_path}")
        return full_path
    
    def on_button_clicked(self, button_name):
        """Handle button click events"""
        self.select_button(button_name)
        self.buttonClicked.emit(button_name)
    
    def select_button(self, button_name):
        """Select a button and deselect others"""
        for name, btn in self.buttons.items():
            btn.set_selected(name == button_name)
        self.current_button = button_name

# ================== Main Window ======================
class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Music URL Info Fetcher")
        self.setGeometry(100, 100, 1000, 700)
        
        # Initialize pages
        self.pages = {
            "Download": DownloadPage(),
            "Batch": BatchDownloadPage(),
            "Settings": SettingsPage(),
            "Theme": SettingsPage(),
            "Logs": LogsPage(),
            "Info": InfoPage()
        }
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create and add sidebar
        self.sidebar = Sidebar()
        self.sidebar.setFixedWidth(100)
        main_layout.addWidget(self.sidebar)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        # Add all pages to stacked widget
        for page_name, page_widget in self.pages.items():
            self.stacked_widget.addWidget(page_widget)
        
        main_layout.addWidget(self.stacked_widget)
        central_widget.setLayout(main_layout)
        
        # Connect sidebar button clicks to switch pages
        self.sidebar.buttonClicked.connect(self.switch_page)
        self.switch_page("Download")
        
        # Apply dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
        """)
    
    def switch_page(self, page_name):
        """Switch to the requested page"""
        page_mapping = {
            "Download": "Download",
            "Batch": "Batch",
            "Settings": "Settings",
            "Theme": "Theme",
            "Logs": "Logs",
            "Info": "Info"
        }
        
        target_page = page_mapping.get(page_name, "Download")
        
        if target_page in self.pages:
            self.stacked_widget.setCurrentWidget(self.pages[target_page])
            print(f"Switched to {target_page} page")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application-wide style
    app.setStyleSheet("""
        QWidget {
            font-family: 'Segoe UI', Arial, sans-serif;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())