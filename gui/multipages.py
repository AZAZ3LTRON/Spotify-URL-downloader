import sys
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtCore import *
import random

class SidebarButton(QPushButton):
    """Custom sidebar button with icon and active state"""
    def __init__(self, text, icon_path=None, page_index=0):
        super().__init__(text)
        self.page_index = page_index
        self.is_active = False
        
        # Set icon if provided
        if icon_path:
            self.setIcon(QIcon(icon_path))
            self.setIconSize(QSize(24, 24))
        
        # Style for inactive state
        self.inactive_style = """
            QPushButton {
                background-color: transparent;
                color: #cccccc;
                border: none;
                border-radius: 8px;
                padding: 12px 15px;
                text-align: left;
                font-size: 14px;
                font-weight: 500;
                margin: 2px 5px;
            }
            QPushButton:hover {
                background-color: #2a2a2a;
                color: #ffffff;
            }
            QPushButton:pressed {
                background-color: #1e1e1e;
            }
        """
        
        # Style for active state
        self.active_style = """
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 12px 15px;
                text-align: left;
                font-size: 14px;
                font-weight: 600;
                margin: 2px 5px;
            }
            QPushButton:hover {
                background-color: #1084e0;
            }
        """
        
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(self.inactive_style)
        
    def set_active(self, active):
        """Set the button active state"""
        self.is_active = active
        if active:
            self.setStyleSheet(self.active_style)
        else:
            self.setStyleSheet(self.inactive_style)

class PageWidget(QWidget):
    """Base class for page widgets"""
    def __init__(self, page_name):
        super().__init__()
        self.page_name = page_name
        self.setup_ui()
        
    def setup_ui(self):
        """To be implemented by subclasses"""
        pass

class DashboardPage(PageWidget):
    """Dashboard page with metrics and overview"""
    def __init__(self):
        super().__init__("Dashboard")
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)
        
        # Page header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Dashboard")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Date label
        date_label = QLabel("Today, September 26, 2023")
        date_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
                padding: 8px 16px;
                background-color: #2d2d2d;
                border-radius: 6px;
            }
        """)
        header_layout.addWidget(date_label)
        
        layout.addLayout(header_layout)
        
        # Welcome message
        welcome_label = QLabel("Welcome back! Here's what's happening today.")
        welcome_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 16px;
            }
        """)
        layout.addWidget(welcome_label)
        
        # Metrics cards
        metrics_layout = QGridLayout()
        metrics_layout.setSpacing(20)
        
        metrics = [
            ("Total Users", "1,254", "#0078d4", "📊"),
            ("Revenue", "$12,580", "#107c10", "💰"),
            ("Conversion Rate", "3.2%", "#ffb900", "📈"),
            ("Active Sessions", "347", "#d13438", "👥")
        ]
        
        for i, (title, value, color, icon) in enumerate(metrics):
            card = self.create_metric_card(title, value, color, icon)
            row = i // 2
            col = i % 2
            metrics_layout.addWidget(card, row, col)
        
        layout.addLayout(metrics_layout)
        
        # Recent activity section
        activity_label = QLabel("Recent Activity")
        activity_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 20px;
                font-weight: bold;
                padding-top: 10px;
            }
        """)
        layout.addWidget(activity_label)
        
        # Activity list
        activity_list = QListWidget()
        activity_list.setStyleSheet("""
            QListWidget {
                background-color: #252525;
                border: 1px solid #333;
                border-radius: 8px;
                font-size: 14px;
                color: #cccccc;
                padding: 10px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #333;
                background-color: transparent;
            }
            QListWidget::item:last {
                border-bottom: none;
            }
            QListWidget::item:hover {
                background-color: #2a2a2a;
                border-radius: 4px;
            }
        """)
        activity_list.setMaximumHeight(200)
        
        activities = [
            "User 'JohnDoe' logged in",
            "New order #12345 placed",
            "Report 'Monthly Sales' generated",
            "User 'JaneSmith' updated profile",
            "System backup completed"
        ]
        
        for activity in activities:
            item = QListWidgetItem(f"• {activity}")
            activity_list.addItem(item)
        
        layout.addWidget(activity_list)
        
        layout.addStretch()
        self.setLayout(layout)

    def create_metric_card(self, title, value, color, icon):
        """Create a metric card widget"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #252525;
                border-radius: 12px;
                border: 1px solid #333;
            }}
        """)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)
        
        # Top row with icon and title
        top_layout = QHBoxLayout()
        
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 24px;
            }}
        """)
        top_layout.addWidget(icon_label)
        
        top_layout.addStretch()
        
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
            }
        """)
        top_layout.addWidget(title_label)
        
        card_layout.addLayout(top_layout)
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 32px;
                font-weight: bold;
            }}
        """)
        card_layout.addWidget(value_label)
        
        # Trend indicator (random for demo)
        trend = random.choice(["+2.5%", "-1.2%", "+5.3%", "+0.8%"])
        trend_color = "#107c10" if "+" in trend else "#d13438"
        
        trend_label = QLabel(f"↗ {trend}")
        trend_label.setStyleSheet(f"""
            QLabel {{
                color: {trend_color};
                font-size: 12px;
                padding: 4px 8px;
                background-color: {trend_color}20;
                border-radius: 4px;
            }}
        """)
        card_layout.addWidget(trend_label)
        
        card.setLayout(card_layout)
        return card

class AnalyticsPage(PageWidget):
    """Analytics page with charts and data visualization"""
    def __init__(self):
        super().__init__("Analytics")
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)
        
        # Page header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Analytics")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Time range selector
        time_combo = QComboBox()
        time_combo.addItems(["Today", "Last 7 Days", "Last 30 Days", "Last Quarter", "Last Year"])
        time_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 16px;
                min-width: 150px;
            }
            QComboBox:hover {
                border: 1px solid #555;
            }
        """)
        header_layout.addWidget(time_combo)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel("Visualize your data with interactive charts and insights.")
        desc_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 16px;
            }
        """)
        layout.addWidget(desc_label)
        
        # Chart area
        chart_container = QFrame()
        chart_container.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 12px;
                border: 1px solid #333;
            }
        """)
        chart_container.setMinimumHeight(300)
        
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(20, 20, 20, 20)
        
        # Chart header
        chart_header = QHBoxLayout()
        
        chart_title = QLabel("Traffic Overview")
        chart_title.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        chart_header.addWidget(chart_title)
        
        chart_header.addStretch()
        
        # Chart legend
        legend_layout = QHBoxLayout()
        legend_layout.setSpacing(15)
        
        legend_items = [
            ("Visitors", "#0078d4"),
            ("Page Views", "#107c10"),
            ("Conversion", "#ffb900")
        ]
        
        for text, color in legend_items:
            legend_item = QHBoxLayout()
            legend_item.setSpacing(8)
            
            color_label = QLabel("■")
            color_label.setStyleSheet(f"""
                QLabel {{
                    color: {color};
                    font-size: 16px;
                }}
            """)
            legend_item.addWidget(color_label)
            
            text_label = QLabel(text)
            text_label.setStyleSheet("""
                QLabel {
                    color: #aaaaaa;
                    font-size: 12px;
                }
            """)
            legend_item.addWidget(text_label)
            
            legend_layout.addLayout(legend_item)
        
        chart_header.addLayout(legend_layout)
        chart_layout.addLayout(chart_header)
        
        # Simulated chart (using progress bars for demo)
        chart_data = [
            ("Mon", 65, 45, 25),
            ("Tue", 70, 50, 30),
            ("Wed", 80, 60, 35),
            ("Thu", 75, 55, 32),
            ("Fri", 85, 65, 40),
            ("Sat", 60, 40, 22),
            ("Sun", 55, 35, 20)
        ]
        
        for day, visitors, page_views, conversion in chart_data:
            day_layout = QHBoxLayout()
            day_layout.setSpacing(10)
            
            # Day label
            day_label = QLabel(day)
            day_label.setFixedWidth(40)
            day_label.setStyleSheet("""
                QLabel {
                    color: #cccccc;
                    font-size: 12px;
                }
            """)
            day_layout.addWidget(day_label)
            
            # Visitors bar
            visitors_bar = self.create_chart_bar(visitors, "#0078d4", f"{visitors} visitors")
            day_layout.addWidget(visitors_bar)
            
            # Page views bar
            page_views_bar = self.create_chart_bar(page_views, "#107c10", f"{page_views} views")
            day_layout.addWidget(page_views_bar)
            
            # Conversion bar
            conversion_bar = self.create_chart_bar(conversion, "#ffb900", f"{conversion}% conversion")
            day_layout.addWidget(conversion_bar)
            
            chart_layout.addLayout(day_layout)
        
        chart_container.setLayout(chart_layout)
        layout.addWidget(chart_container)
        
        # KPI cards
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(20)
        
        kpis = [
            ("Avg. Session Duration", "4m 32s", "+12%"),
            ("Bounce Rate", "42%", "-5%"),
            ("New Users", "312", "+8%"),
            ("Pages/Session", "3.8", "+2%")
        ]
        
        for title, value, change in kpis:
            kpi_card = self.create_kpi_card(title, value, change)
            kpi_layout.addWidget(kpi_card)
        
        layout.addLayout(kpi_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def create_chart_bar(self, value, color, tooltip):
        """Create a chart bar widget"""
        bar = QFrame()
        bar.setFixedHeight(20)
        bar.setStyleSheet(f"""
            QFrame {{
                background-color: {color}40;
                border-radius: 4px;
                border: 1px solid {color}80;
            }}
        """)
        
        bar_layout = QHBoxLayout()
        bar_layout.setContentsMargins(0, 0, 0, 0)
        
        # Fill bar
        fill = QFrame()
        fill_width = max(20, int(value * 2))  # Scale for demo
        fill.setFixedWidth(fill_width)
        fill.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        bar_layout.addWidget(fill)
        
        bar_layout.addStretch()
        bar.setLayout(bar_layout)
        
        # Tooltip
        bar.setToolTip(tooltip)
        
        return bar
    
    def create_kpi_card(self, title, value, change):
        """Create a KPI card widget"""
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 10px;
                border: 1px solid #333;
            }
        """)
        
        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(10)
        
        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #aaaaaa;
                font-size: 14px;
            }
        """)
        card_layout.addWidget(title_label)
        
        # Value
        value_label = QLabel(value)
        value_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        card_layout.addWidget(value_label)
        
        # Change indicator
        change_color = "#107c10" if "+" in change else "#d13438"
        change_icon = "↗" if "+" in change else "↘"
        
        change_label = QLabel(f"{change_icon} {change}")
        change_label.setStyleSheet(f"""
            QLabel {{
                color: {change_color};
                font-size: 12px;
                padding: 4px 8px;
                background-color: {change_color}20;
                border-radius: 4px;
            }}
        """)
        card_layout.addWidget(change_label)
        
        card.setLayout(card_layout)
        return card

class SettingsPage(PageWidget):
    """Settings page with configuration options"""
    def __init__(self):
        super().__init__("Settings")
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 30, 40, 30)
        layout.setSpacing(25)
        
        # Page header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("Settings")
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 32px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel("Configure your application preferences and settings.")
        desc_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 16px;
            }
        """)
        layout.addWidget(desc_label)
        
        # Settings tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #333;
                border-radius: 8px;
                background-color: #252525;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #aaaaaa;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
            }
            QTabBar::tab:selected {
                background-color: #252525;
                color: #ffffff;
                border-bottom: 2px solid #0078d4;
            }
            QTabBar::tab:hover {
                background-color: #353535;
            }
        """)
        
        # General Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        general_layout.setContentsMargins(20, 20, 20, 20)
        general_layout.setSpacing(15)
        
        general_settings = [
            ("Application Theme", ["Light", "Dark", "System Default"], 1),
            ("Language", ["English", "Spanish", "French", "German"], 0),
            ("Timezone", ["UTC", "EST", "PST", "CET"], 0),
            ("Date Format", ["MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD"], 0)
        ]
        
        for setting_name, options, default_index in general_settings:
            setting_widget = self.create_dropdown_setting(setting_name, options, default_index)
            general_layout.addWidget(setting_widget)
        
        general_layout.addStretch()
        general_tab.setLayout(general_layout)
        
        # Account Tab
        account_tab = QWidget()
        account_layout = QVBoxLayout()
        account_layout.setContentsMargins(20, 20, 20, 20)
        account_layout.setSpacing(15)
        
        account_settings = [
            ("Email Notifications", True),
            ("SMS Notifications", False),
            ("Marketing Emails", True),
            ("Two-Factor Authentication", True),
            ("Show Online Status", True)
        ]
        
        for setting_name, default_value in account_settings:
            setting_widget = self.create_toggle_setting(setting_name, default_value)
            account_layout.addWidget(setting_widget)
        
        account_layout.addStretch()
        account_tab.setLayout(account_layout)
        
        # Privacy Tab
        privacy_tab = QWidget()
        privacy_layout = QVBoxLayout()
        privacy_layout.setContentsMargins(20, 20, 20, 20)
        privacy_layout.setSpacing(15)
        
        privacy_settings = [
            ("Data Collection", "Allow anonymous usage data collection to help improve the application.", False),
            ("Personalized Ads", "Show personalized advertisements based on your usage.", True),
            ("Share Analytics", "Share aggregated analytics with partners.", False),
            ("Cookie Consent", "Remember my cookie preferences.", True)
        ]
        
        for setting_name, description, default_value in privacy_settings:
            setting_widget = self.create_privacy_setting(setting_name, description, default_value)
            privacy_layout.addWidget(setting_widget)
        
        privacy_layout.addStretch()
        privacy_tab.setLayout(privacy_layout)
        
        # Add tabs
        self.tab_widget.addTab(general_tab, "General")
        self.tab_widget.addTab(account_tab, "Account")
        self.tab_widget.addTab(privacy_tab, "Privacy")
        
        layout.addWidget(self.tab_widget)
        
        # Save buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        reset_button = QPushButton("Reset to Defaults")
        reset_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: #cccccc;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #353535;
                border-color: #555;
            }
        """)
        reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_button)
        
        save_button = QPushButton("Save Changes")
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                padding: 10px 30px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1084e0;
            }
        """)
        save_button.clicked.connect(self.save_settings)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        self.setLayout(layout)
    
    def create_dropdown_setting(self, name, options, default_index):
        """Create a dropdown setting widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Setting name
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        name_label.setFixedWidth(200)
        layout.addWidget(name_label)
        
        # Dropdown
        dropdown = QComboBox()
        dropdown.addItems(options)
        dropdown.setCurrentIndex(default_index)
        dropdown.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #444;
                border-radius: 6px;
                padding: 8px 12px;
                min-width: 200px;
            }
            QComboBox:hover {
                border: 1px solid #555;
            }
        """)
        layout.addWidget(dropdown)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_toggle_setting(self, name, default_value):
        """Create a toggle switch setting widget"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Setting name
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        name_label.setFixedWidth(200)
        layout.addWidget(name_label)
        
        # Toggle switch
        toggle = QCheckBox()
        toggle.setChecked(default_value)
        toggle.setStyleSheet("""
            QCheckBox {
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 50px;
                height: 24px;
                border-radius: 12px;
                border: 2px solid #555;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1084e0;
                border-color: #1084e0;
            }
            QCheckBox::indicator:hover {
                border-color: #666;
            }
        """)
        layout.addWidget(toggle)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_privacy_setting(self, name, description, default_value):
        """Create a privacy setting widget with description"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Top row with toggle
        top_layout = QHBoxLayout()
        
        # Setting name
        name_label = QLabel(name)
        name_label.setStyleSheet("""
            QLabel {
                color: #cccccc;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        top_layout.addWidget(name_label)
        
        top_layout.addStretch()
        
        # Toggle switch
        toggle = QCheckBox()
        toggle.setChecked(default_value)
        toggle.setStyleSheet("""
            QCheckBox {
                spacing: 10px;
            }
            QCheckBox::indicator {
                width: 50px;
                height: 24px;
                border-radius: 12px;
                border: 2px solid #555;
                background-color: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background-color: #0078d4;
                border-color: #0078d4;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #1084e0;
                border-color: #1084e0;
            }
            QCheckBox::indicator:hover {
                border-color: #666;
            }
        """)
        top_layout.addWidget(toggle)
        
        layout.addLayout(top_layout)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
                padding-left: 5px;
            }
        """)
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        widget.setLayout(layout)
        return widget
    
    def reset_settings(self):
        """Reset all settings to default"""
        reply = QMessageBox.question(
            self, "Reset Settings",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "Settings Reset", "Settings have been reset to default values.")
    
    def save_settings(self):
        """Save settings"""
        QMessageBox.information(self, "Settings Saved", "Your settings have been saved successfully.")

class SidebarWidget(QWidget):
    """Sidebar with navigation buttons"""
    def __init__(self):
        super().__init__()
        self.buttons = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(5)
        
        # Logo/App name
        logo_layout = QHBoxLayout()
        logo_label = QLabel("🚀 App")
        logo_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                padding: 10px;
            }
        """)
        logo_layout.addWidget(logo_label)
        layout.addLayout(logo_layout)
        
        layout.addSpacing(30)
        
        # Navigation label
        nav_label = QLabel("NAVIGATION")
        nav_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 11px;
                font-weight: bold;
                padding: 10px 15px 5px 15px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
        """)
        layout.addWidget(nav_label)
        
        # Create navigation buttons
        self.create_button("Dashboard", "📊", 0, layout)
        self.create_button("Analytics", "📈", 1, layout)
        self.create_button("Settings", "⚙️", 2, layout)
        
        layout.addStretch()
        
        # User profile at bottom
        user_widget = self.create_user_widget()
        layout.addWidget(user_widget)
        
        self.setLayout(layout)
        
        # Set sidebar background
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
            }
        """)
    
    def create_button(self, text, icon, page_index, layout):
        """Create a navigation button"""
        # For this demo, we'll use emoji as icons. In a real app, use QIcon with image files
        btn = SidebarButton(f"  {icon}  {text}", None, page_index)
        self.buttons.append(btn)
        layout.addWidget(btn)
    
    def create_user_widget(self):
        """Create user profile widget"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background-color: #252525;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Avatar
        avatar = QLabel("👤")
        avatar.setStyleSheet("""
            QLabel {
                font-size: 24px;
                padding: 5px;
            }
        """)
        layout.addWidget(avatar)
        
        # User info
        user_layout = QVBoxLayout()
        user_layout.setSpacing(2)
        
        name_label = QLabel("John Doe")
        name_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 14px;
                font-weight: 500;
            }
        """)
        user_layout.addWidget(name_label)
        
        role_label = QLabel("Administrator")
        role_label.setStyleSheet("""
            QLabel {
                color: #888888;
                font-size: 12px;
            }
        """)
        user_layout.addWidget(role_label)
        
        layout.addLayout(user_layout)
        
        widget.setLayout(layout)
        return widget

class MainWindow(QMainWindow):
    """Main application window with sidebar and page switching"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Page Application - PySide6")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create pages
        self.pages = [
            DashboardPage(),
            AnalyticsPage(),
            SettingsPage()
        ]
        
        self.current_page_index = 0
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = SidebarWidget()
        self.sidebar.setFixedWidth(250)
        main_layout.addWidget(self.sidebar)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("""
            QStackedWidget {
                background-color: #141414;
            }
        """)
        
        # Add pages to stacked widget
        for page in self.pages:
            self.stacked_widget.addWidget(page)
        
        # Set initial page
        self.stacked_widget.setCurrentIndex(self.current_page_index)
        
        # Connect sidebar buttons
        for i, button in enumerate(self.sidebar.buttons):
            button.clicked.connect(lambda checked, idx=i: self.switch_page(idx))
        
        # Set first button as active
        if self.sidebar.buttons:
            self.sidebar.buttons[0].set_active(True)
        
        main_layout.addWidget(self.stacked_widget)
        central_widget.setLayout(main_layout)
        
        # Apply window style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #141414;
            }
        """)
    
    def switch_page(self, page_index):
        """Switch to a different page"""
        if page_index < 0 or page_index >= len(self.pages):
            return
        
        # Update button states
        for i, button in enumerate(self.sidebar.buttons):
            button.set_active(i == page_index)
        
        # Switch page
        self.current_page_index = page_index
        self.stacked_widget.setCurrentIndex(page_index)

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
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()