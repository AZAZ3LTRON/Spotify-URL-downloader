import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt

class SimpleBlackWindow(QMainWindow):
    """Simplest black window example"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Black Window")
        self.setGeometry(100, 100, 400, 300)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Set black background using palette
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        self.setPalette(palette)
        central_widget.setPalette(palette)
        central_widget.setAutoFillBackground(True)
        
        # Add a label to show it works
        layout = QVBoxLayout()
        label = QLabel("This is a simple black window")
        label.setStyleSheet("color: white; font-size: 16px;")
        layout.addWidget(label)
        
        central_widget.setLayout(layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SimpleBlackWindow()
    window.show()
    sys.exit(app.exec())