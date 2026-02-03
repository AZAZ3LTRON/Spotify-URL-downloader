import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
import urllib.request
import tempfile
import os

class ImageButton(QPushButton):
    """Custom button that displays an image with hover effects"""
    def __init__(self, image_path, text="", parent=None):
        super().__init__(parent)
        self.text = text
        
        # Load and scale the image
        self.icon = QIcon(image_path)
        self.setIcon(self.icon)
        self.setIconSize(QSize(40, 40))
        
        # Button styling
        self.setFixedSize(70, 70)
        self.setCursor(Qt.PointingHandCursor)
        
        # Tooltip
        self.setToolTip(text)
        
        # Style
        self.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                border: none;
                border-radius: 8px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border: 1px solid #5a5a5a;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
        """)

class SidebarWidget(QWidget):
    """Main sidebar widget containing image buttons"""
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_sample_images()
        
    def setup_ui(self):
        # Main layout for the sidebar
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(15)
        
        # Add a title label
        title_label = QLabel("Navigation")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
                border-bottom: 1px solid #444;
            }
        """)
        layout.addWidget(title_label)
        
        # Create 5 image buttons
        self.buttons = []
        
        # Button 1: Home
        self.btn_home = ImageButton(self.get_image_path("home"), "Home")
        self.btn_home.clicked.connect(lambda: self.button_clicked("Home"))
        self.buttons.append(self.btn_home)
        
        # Button 2: Search
        self.btn_search = ImageButton(self.get_image_path("search"), "Search")
        self.btn_search.clicked.connect(lambda: self.button_clicked("Search"))
        self.buttons.append(self.btn_search)
        
        # Button 3: Settings
        self.btn_settings = ImageButton(self.get_image_path("settings"), "Settings")
        self.btn_settings.clicked.connect(lambda: self.button_clicked("Settings"))
        self.buttons.append(self.btn_settings)
        
        # Button 4: Messages
        self.btn_messages = ImageButton(self.get_image_path("messages"), "Messages")
        self.btn_messages.clicked.connect(lambda: self.button_clicked("Messages"))
        self.buttons.append(self.btn_messages)
        
        # Button 5: Help
        self.btn_help = ImageButton(self.get_image_path("help"), "Help")
        self.btn_help.clicked.connect(lambda: self.button_clicked("Help"))
        self.buttons.append(self.btn_help)
        
        # Add buttons to layout
        for btn in self.buttons:
            layout.addWidget(btn)
            
        # Add stretch to push buttons to the top
        layout.addStretch()
        
        # Add a user/profile button at the bottom
        self.btn_profile = ImageButton(self.get_image_path("profile"), "Profile")
        self.btn_profile.clicked.connect(lambda: self.button_clicked("Profile"))
        layout.addWidget(self.btn_profile)
        
        self.setLayout(layout)
        
        # Set sidebar background
        self.setStyleSheet("""
            QWidget {
                background-color: #252525;
            }
        """)
        
    def get_image_path(self, image_type):
        """Get the path to the appropriate image based on type"""
        # Dictionary mapping button types to emoji or symbol representations
        # In a real app, you would use actual image files
        emoji_map = {
            "home": "🏠",
            "search": "🔍",
            "settings": "⚙️",
            "messages": "✉️",
            "help": "❓",
            "profile": "👤"
        }
        
        # For this example, we'll create image files with emojis
        # In a real app, you would use actual image files
        emoji = emoji_map.get(image_type, "❓")
        
        # Create a temporary image file with the emoji
        return self.create_emoji_image(emoji, image_type)
    
    def create_emoji_image(self, emoji, name):
        """Create a temporary image file with an emoji"""
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        image_path = os.path.join(temp_dir, f"sidebar_{name}.png")
        
        # Only create the file if it doesn't exist
        if not os.path.exists(image_path):
            # Create a pixmap with the emoji
            pixmap = QPixmap(100, 100)
            pixmap.fill(Qt.transparent)
            
            painter = QPainter(pixmap)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 50))
            painter.drawText(pixmap.rect(), Qt.AlignCenter, emoji)
            painter.end()
            
            # Save the pixmap
            pixmap.save(image_path)
            
        return image_path
    
    def load_sample_images(self):
        """Alternative method to download sample icons from the web"""
        try:
            # Sample icon URLs (free icons from flaticon)
            icon_urls = {
                "home": "https://cdn-icons-png.flaticon.com/512/25/25694.png",
                "search": "https://cdn-icons-png.flaticon.com/512/54/54481.png",
                "settings": "https://cdn-icons-png.flaticon.com/512/126/126472.png",
                "messages": "https://cdn-icons-png.flaticon.com/512/60/60543.png",
                "help": "https://cdn-icons-png.flaticon.com/512/0/375.png",
                "profile": "https://cdn-icons-png.flaticon.com/512/1077/1077012.png"
            }
            
            # Download and replace emoji images with real icons
            for btn_type, url in icon_urls.items():
                temp_dir = tempfile.gettempdir()
                image_path = os.path.join(temp_dir, f"sidebar_{btn_type}_web.png")
                
                # Download if not already downloaded
                if not os.path.exists(image_path):
                    urllib.request.urlretrieve(url, image_path)
                    
                # Update button icons
                if btn_type == "home":
                    self.btn_home.setIcon(QIcon(image_path))
                elif btn_type == "search":
                    self.btn_search.setIcon(QIcon(image_path))
                elif btn_type == "settings":
                    self.btn_settings.setIcon(QIcon(image_path))
                elif btn_type == "messages":
                    self.btn_messages.setIcon(QIcon(image_path))
                elif btn_type == "help":
                    self.btn_help.setIcon(QIcon(image_path))
                elif btn_type == "profile":
                    self.btn_profile.setIcon(QIcon(image_path))
                    
        except Exception as e:
            print(f"Could not download web icons: {e}. Using emoji icons instead.")
    
    def button_clicked(self, button_name):
        """Handle button click events"""
        print(f"{button_name} button clicked!")
        
        # Highlight the clicked button
        for btn in self.buttons:
            if btn.text == button_name:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4a4a4a;
                        border: 1px solid #6a6a6a;
                        border-radius: 8px;
                        padding: 5px;
                    }
                """)
            else:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        border: none;
                        border-radius: 8px;
                        padding: 5px;
                    }
                    QPushButton:hover {
                        background-color: #3a3a3a;
                        border: 1px solid #5a5a5a;
                    }
                """)

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sidebar with Image Buttons")
        self.setGeometry(100, 100, 900, 600)
        
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create and add sidebar
        self.sidebar = SidebarWidget()
        self.sidebar.setFixedWidth(100)
        main_layout.addWidget(self.sidebar)
        
        # Create content area
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
        
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(40, 40, 40, 40)
        
        # Add title
        title = QLabel("Sidebar with Image Buttons")
        title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: bold;
            }
        """)
        content_layout.addWidget(title)
        
        # Add description
        description = QLabel(
            "This application demonstrates a sidebar with 5 image buttons.\n"
            "Click on any button in the sidebar to see it in action.\n\n"
            "The buttons use both local emoji images and downloaded icons.\n"
            "Check the terminal for button click events."
        )
        description.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 14px;
                padding: 20px 0;
            }
        """)
        description.setWordWrap(True)
        content_layout.addWidget(description)
        
        # Add status label
        self.status_label = QLabel("No button clicked yet.")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #88ff88;
                font-size: 16px;
                padding: 20px;
                background-color: #2a2a2a;
                border-radius: 8px;
                border: 1px solid #444;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setFixedHeight(80)
        content_layout.addWidget(self.status_label)
        
        # Add stretch
        content_layout.addStretch()
        
        content_widget.setLayout(content_layout)
        main_layout.addWidget(content_widget)
        
        central_widget.setLayout(main_layout)
        
        # Connect sidebar signals
        self.sidebar.btn_home.clicked.connect(lambda: self.update_status("Home button clicked"))
        self.sidebar.btn_search.clicked.connect(lambda: self.update_status("Search button clicked"))
        self.sidebar.btn_settings.clicked.connect(lambda: self.update_status("Settings button clicked"))
        self.sidebar.btn_messages.clicked.connect(lambda: self.update_status("Messages button clicked"))
        self.sidebar.btn_help.clicked.connect(lambda: self.update_status("Help button clicked"))
        self.sidebar.btn_profile.clicked.connect(lambda: self.update_status("Profile button clicked"))
    
    def update_status(self, message):
        """Update the status label"""
        self.status_label.setText(message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # Use Fusion style for better dark theme support
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())