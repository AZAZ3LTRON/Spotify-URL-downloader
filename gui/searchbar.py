import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
import webbrowser
import json
import os

class SearchBar(QLineEdit):
    """Custom search bar widget with enhanced functionality"""
    
    search_requested = Signal(str)  # Signal emitted when search is performed
    text_changed_signal = Signal(str)  # Signal for text changes
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_signals()
        
        # Search history
        self.history = []
        self.history_limit = 10
        
        # Autocomplete suggestions
        self.suggestions = [
            "Python programming", "PySide6 tutorial", "Qt framework",
            "Machine learning", "Web development", "Data science",
            "GUI applications", "Desktop apps", "Software development",
            "Artificial intelligence", "Deep learning", "Computer vision"
        ]
        
        # Load search history if exists
        self.load_history()
        
    def setup_ui(self):
        """Set up the search bar appearance and behavior"""
        # Set placeholder text
        self.setPlaceholderText("Search...")
        
        # Set styles
        self.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 2px solid #444444;
                border-radius: 20px;
                padding: 8px 40px 8px 15px;
                font-size: 14px;
                selection-background-color: #4a4a4a;
            }
            QLineEdit:focus {
                border: 2px solid #0078d7;
                background-color: #1e1e1e;
            }
            QLineEdit:hover {
                border: 2px solid #555555;
            }
        """)
        
        # Set size
        self.setMinimumHeight(40)
        
        # Create search icon
        self.search_icon = QLabel(self)
        self.search_icon.setPixmap(self.create_search_icon())
        self.search_icon.setStyleSheet("background-color: transparent;")
        self.search_icon.setCursor(Qt.ArrowCursor)
        
        # Create clear button
        self.clear_button = QPushButton(self)
        self.clear_button.setIcon(QIcon(self.create_clear_icon()))
        self.clear_button.setCursor(Qt.PointingHandCursor)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                border-radius: 10px;
            }
        """)
        self.clear_button.setFixedSize(20, 20)
        self.clear_button.hide()  # Hide initially
        self.clear_button.clicked.connect(self.clear_search)
        
        # Create search button
        self.search_button = QPushButton(self)
        self.search_button.setIcon(QIcon(self.create_enter_icon()))
        self.search_button.setCursor(Qt.PointingHandCursor)
        self.search_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;
                border: none;
                border-radius: 15px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #1088e7;
            }
            QPushButton:pressed {
                background-color: #0068c7;
            }
        """)
        self.search_button.setFixedSize(30, 30)
        self.search_button.clicked.connect(self.perform_search)
        
        # Create suggestion popup
        self.suggestion_popup = QListWidget()
        self.suggestion_popup.setWindowFlags(Qt.Popup)
        self.suggestion_popup.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 8px;
                font-size: 13px;
                color: #ffffff;
            }
            QListWidget::item {
                padding: 8px 12px;
                border-bottom: 1px solid #3a3a3a;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
        """)
        self.suggestion_popup.hide()
        self.suggestion_popup.itemClicked.connect(self.select_suggestion)
        
        # Position widgets
        self.update_widget_positions()
        
    def setup_signals(self):
        """Connect signals and slots"""
        self.textChanged.connect(self.on_text_changed)
        self.returnPressed.connect(self.perform_search)
        
    def create_search_icon(self):
        """Create a search icon using QPainter"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set pen for the icon
        pen = QPen(QColor(150, 150, 150))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw search icon (magnifying glass)
        # Draw circle
        painter.drawEllipse(2, 2, 10, 10)
        # Draw handle
        painter.drawLine(10, 10, 14, 14)
        
        painter.end()
        return pixmap
        
    def create_clear_icon(self):
        """Create a clear (X) icon"""
        pixmap = QPixmap(12, 12)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(150, 150, 150))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw X
        painter.drawLine(2, 2, 10, 10)
        painter.drawLine(10, 2, 2, 10)
        
        painter.end()
        return pixmap
        
    def create_enter_icon(self):
        """Create an enter/arrow icon"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw arrow
        painter.drawLine(4, 8, 12, 8)
        painter.drawLine(12, 8, 9, 5)
        painter.drawLine(12, 8, 9, 11)
        
        painter.end()
        return pixmap
        
    def resizeEvent(self, event):
        """Update widget positions when search bar is resized"""
        super().resizeEvent(event)
        self.update_widget_positions()
        
    def update_widget_positions(self):
        """Update positions of child widgets"""
        # Position search icon on the left
        icon_x = 10
        icon_y = (self.height() - self.search_icon.pixmap().height()) // 2
        self.search_icon.move(icon_x, icon_y)
        
        # Position clear button on the right
        clear_x = self.width() - 70
        clear_y = (self.height() - self.clear_button.height()) // 2
        self.clear_button.move(clear_x, clear_y)
        
        # Position search button on the right
        search_x = self.width() - 40
        search_y = (self.height() - self.search_button.height()) // 2
        self.search_button.move(search_x, search_y)
        
    def on_text_changed(self, text):
        """Handle text changes in the search bar"""
        # Show/hide clear button
        self.clear_button.setVisible(bool(text))
        
        # Emit signal
        self.text_changed_signal.emit(text)
        
        # Show suggestions if text is not empty
        if text.strip():
            self.show_suggestions(text)
        else:
            self.suggestion_popup.hide()
            
    def show_suggestions(self, text):
        """Show autocomplete suggestions"""
        # Filter suggestions based on input
        filtered = [s for s in self.suggestions if text.lower() in s.lower()]
        
        if not filtered:
            self.suggestion_popup.hide()
            return
            
        # Update suggestion list
        self.suggestion_popup.clear()
        for suggestion in filtered[:5]:  # Show max 5 suggestions
            item = QListWidgetItem(suggestion)
            self.suggestion_popup.addItem(item)
            
        # Position and show the popup
        popup_width = 250
        popup_height = min(self.suggestion_popup.sizeHintForRow(0) * len(filtered) + 10, 200)
        
        popup_x = self.mapToGlobal(QPoint(0, self.height())).x()
        popup_y = self.mapToGlobal(QPoint(0, self.height())).y()
        
        self.suggestion_popup.setGeometry(popup_x, popup_y, popup_width, popup_height)
        self.suggestion_popup.show()
        
    def select_suggestion(self, item):
        """Handle suggestion selection"""
        self.setText(item.text())
        self.suggestion_popup.hide()
        self.setFocus()
        
    def clear_search(self):
        """Clear the search bar"""
        self.clear()
        self.suggestion_popup.hide()
        self.setFocus()
        
    def perform_search(self):
        """Perform the search action"""
        search_text = self.text().strip()
        
        if not search_text:
            return
            
        # Add to history
        if search_text not in self.history:
            self.history.insert(0, search_text)
            if len(self.history) > self.history_limit:
                self.history.pop()
            self.save_history()
            
        # Emit search signal
        self.search_requested.emit(search_text)
        
        # Hide suggestions
        self.suggestion_popup.hide()
        
        print(f"Searching for: {search_text}")
        
    def load_history(self):
        """Load search history from file"""
        try:
            history_file = "search_history.json"
            if os.path.exists(history_file):
                with open(history_file, 'r') as f:
                    self.history = json.load(f)
        except:
            self.history = []
            
    def save_history(self):
        """Save search history to file"""
        try:
            history_file = "search_history.json"
            with open(history_file, 'w') as f:
                json.dump(self.history, f)
        except:
            pass

class SearchResultsWidget(QWidget):
    """Widget to display search results"""
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Results label
        self.results_label = QLabel("Search results will appear here")
        self.results_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.results_label)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #444444;
                border-radius: 8px;
                font-size: 14px;
                color: #ffffff;
                padding: 10px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #3a3a3a;
                background-color: transparent;
            }
            QListWidget::item:hover {
                background-color: #3a3a3a;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.results_list)
        
        self.setLayout(layout)
        
    def update_results(self, query):
        """Update search results based on query"""
        self.results_label.setText(f'Search results for: "{query}"')
        self.results_list.clear()
        
        # Sample results - in a real app, you would fetch actual results
        sample_results = [
            f"Result 1: Information about {query}",
            f"Result 2: Tutorial on {query}",
            f"Result 3: Advanced techniques for {query}",
            f"Result 4: {query} best practices",
            f"Result 5: Common issues with {query}"
        ]
        
        for result in sample_results:
            item = QListWidgetItem(result)
            self.results_list.addItem(item)

class AdvancedSearchWindow(QMainWindow):
    """Main window with advanced search features"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Advanced Search Bar - PySide6")
        self.setGeometry(100, 100, 900, 700)
        
        # Set application icon
        self.setWindowIcon(self.create_app_icon())
        
        self.setup_ui()
        
    def create_app_icon(self):
        """Create application icon"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 120, 215))
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(3)
        painter.setPen(pen)
        
        # Draw magnifying glass
        painter.drawEllipse(6, 6, 12, 12)
        painter.drawLine(14, 14, 22, 22)
        
        painter.end()
        return QIcon(pixmap)
        
    def setup_ui(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(20)
        
        # Title
        title_label = QLabel("Advanced Search Bar")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
                padding-bottom: 10px;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(
            "A modern search bar implementation with autocomplete, "
            "search history, and results display."
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
        main_layout.addWidget(desc_label)
        
        # Create search bar
        self.search_bar = SearchBar()
        main_layout.addWidget(self.search_bar)
        
        # Search options frame
        options_frame = QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 10px;
                border: 1px solid #444444;
            }
        """)
        
        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(15, 10, 15, 10)
        
        # Search engine selection
        engine_label = QLabel("Search with:")
        engine_label.setStyleSheet("color: #cccccc;")
        options_layout.addWidget(engine_label)
        
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["Internal Search", "Google", "Bing", "DuckDuckGo", "YouTube"])
        self.engine_combo.setStyleSheet("""
            QComboBox {
                background-color: #3a3a3a;
                color: white;
                border: 1px solid #555555;
                border-radius: 5px;
                padding: 5px 10px;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid #666666;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #cccccc;
            }
        """)
        options_layout.addWidget(self.engine_combo)
        
        options_layout.addStretch()
        
        # Case sensitive checkbox
        self.case_checkbox = QCheckBox("Case sensitive")
        self.case_checkbox.setStyleSheet("""
            QCheckBox {
                color: #cccccc;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555555;
                border-radius: 3px;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d7;
                border: 2px solid #0078d7;
            }
        """)
        options_layout.addWidget(self.case_checkbox)
        
        # Whole word checkbox
        self.whole_word_checkbox = QCheckBox("Whole word")
        self.whole_word_checkbox.setStyleSheet(self.case_checkbox.styleSheet())
        options_layout.addWidget(self.whole_word_checkbox)
        
        options_frame.setLayout(options_layout)
        main_layout.addWidget(options_frame)
        
        # Search results widget
        self.results_widget = SearchResultsWidget()
        main_layout.addWidget(self.results_widget, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to search")
        
        # Connect signals
        self.search_bar.search_requested.connect(self.handle_search)
        self.search_bar.text_changed_signal.connect(self.update_status)
        
        central_widget.setLayout(main_layout)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
        """)
        
    def handle_search(self, query):
        """Handle search requests"""
        search_engine = self.engine_combo.currentText()
        
        if search_engine == "Internal Search":
            # Perform internal search
            self.results_widget.update_results(query)
            self.status_bar.showMessage(f'Internal search for "{query}" completed')
        else:
            # Open external search engine
            self.perform_external_search(query, search_engine)
            
    def perform_external_search(self, query, engine):
        """Open external search engine in browser"""
        search_urls = {
            "Google": f"https://www.google.com/search?q={query}",
            "Bing": f"https://www.bing.com/search?q={query}",
            "DuckDuckGo": f"https://duckduckgo.com/?q={query}",
            "YouTube": f"https://www.youtube.com/results?search_query={query}"
        }
        
        url = search_urls.get(engine, search_urls["Google"])
        try:
            webbrowser.open(url)
            self.status_bar.showMessage(f'Opening {engine} search in browser...')
        except Exception as e:
            self.status_bar.showMessage(f'Error opening browser: {str(e)}')
            
    def update_status(self, text):
        """Update status bar based on search text"""
        if text:
            self.status_bar.showMessage(f'Typing: {text}')
        else:
            self.status_bar.showMessage("Ready to search")

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application-wide dark palette
    dark_palette = QPalette()
    dark_palette.setColor(QPalette.Window, QColor(30, 30, 30))
    dark_palette.setColor(QPalette.WindowText, QColor(220, 220, 220))
    dark_palette.setColor(QPalette.Base, QColor(45, 45, 45))
    dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ToolTipBase, QColor(0, 120, 215))
    dark_palette.setColor(QPalette.ToolTipText, Qt.white)
    dark_palette.setColor(QPalette.Text, Qt.white)
    dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ButtonText, Qt.white)
    dark_palette.setColor(QPalette.BrightText, Qt.red)
    dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    dark_palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(dark_palette)
    
    window = AdvancedSearchWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()