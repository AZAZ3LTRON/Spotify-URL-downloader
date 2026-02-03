import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *

class SimpleSidebarTitle(QWidget):
    def __init__(self):
        super().__init__()
        
        # Create sidebar layout
        layout = QVBoxLayout()
        
        # Create sidebar title with image
        title_widget = self.create_image_title()
        layout.addWidget(title_widget)
        
        # Add sidebar buttons
        layout.addWidget(QPushButton("Home"))
        layout.addWidget(QPushButton("Settings"))
        layout.addWidget(QPushButton("Help"))
        layout.addStretch()
        
        self.setLayout(layout)
    
    def create_image_title(self):
        """Create image title for sidebar"""
        widget = QWidget()
        layout = QHBoxLayout()
        
        # 1. Image/Icon
        icon_label = QLabel()
        
        # Create a simple icon (or load from file)
        pixmap = QPixmap(32, 32)
        pixmap.fill("#0078d4")  # Blue square
        
        # Draw something on it
        painter = QPainter(pixmap)
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Arial", 16))
        painter.drawText(pixmap.rect(), Qt.AlignCenter, "A")
        painter.end()
        
        icon_label.setPixmap(pixmap)
        layout.addWidget(icon_label)
        
        # 2. Title text
        title_label = QLabel("My App")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title_label)
        
        layout.addStretch()
        widget.setLayout(layout)
        
        # Style the title widget
        widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                padding: 10px;
                border-bottom: 1px solid #444;
            }
        """)
        
        return widget

# Usage
app = QApplication(sys.argv)
window = QMainWindow()
window.setGeometry(100, 100, 800, 600)

# Create sidebar
sidebar = SimpleSidebarTitle()
sidebar.setFixedWidth(200)
sidebar.setStyleSheet("background-color: #1e1e1e;")

# Add to window
dock = QDockWidget()
dock.setWidget(sidebar)
dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
window.addDockWidget(Qt.LeftDockWidgetArea, dock)

window.show()
app.exec()