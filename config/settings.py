# config/settings.py
import configparser
from pathlib import Path
import os
import sys

class Settings:
    def __init__(self):
        self.config = configparser.ConfigParser()
        
        # Tentukan lokasi config.ini
        if getattr(sys, 'frozen', False):
            # Jika running sebagai exe
            self.config_path = Path(sys.executable).parent / 'config.ini'
        else:
            # Jika running sebagai script
            self.config_path = Path(__file__).parent.parent / 'config.ini'
        
        self.load_config()
        
        # App settings
        self.APP_NAME = "Promise POS Internal Tool"
        self.APP_VERSION = "1.0.0"
        
        # Paths
        if getattr(sys, 'frozen', False):
            self.BASE_DIR = Path(sys.executable).parent
        else:
            self.BASE_DIR = Path(__file__).parent.parent
            
        self.REPORTS_DIR = self.BASE_DIR / 'reports'
        self.LOGS_DIR = self.BASE_DIR / 'logs'
        
        # Create directories
        self.REPORTS_DIR.mkdir(exist_ok=True)
        self.LOGS_DIR.mkdir(exist_ok=True)
        
        
        # Colors - Modern Premium Palette
        self.THEME_COLORS = {
            'primary': '#4338ca',     # Indigo 700 - Headers
            'secondary': '#1e1b4b',   # Indigo 950 - Status bar
            'accent': '#4f46e5',      # Indigo 600 - Buttons
            'success': '#059669',     # Emerald 600 - Main action
            'warning': '#d97706',     # Amber 600
            'danger': '#dc2626',      # Red 600
            'light': '#f3f4f6',       # Gray 100 - Background
            'white': '#ffffff',       # White - Cards
            'text': '#1f2937',        # Gray 800
            'border': '#e5e7eb',      # Gray 200
        }
    
    def load_config(self):
        """Load configuration from file with defaults"""
        # Set default values
        self.config['DEFAULT'] = {
            'SERVERNAME': 'localhost',
            'USERNAME': 'root',
            'PASSWORD': '',
            'PORT': '3306',
            'DATABASE': 'pos_db',
            'OUTLET': 'OUTLET01'
        }
        
        self.config['MAIL'] = {
            'SENDER': 'email@gmail.com',
            'PASSWORD': '',
            'RECEIVER': 'tujuan@gmail.com',
            'CC': '',
            'SMTPSERVER': 'smtp.gmail.com',
            'SMTPPORT': '465'
        }
        
        self.config['APP'] = {
            'AUTO_LOGIN': 'False',
            'LOG_LEVEL': 'INFO',
            'REPORT_FORMAT': 'txt'
        }
        
        self.config['API'] = {
            'BASE_URL': 'http://localhost:8080/api',
            'TIMEOUT': '30',
            'API_KEY': ''
        }
        

        # Try to load existing config file
        if self.config_path.exists():
            try:
                self.config.read(self.config_path)
                print(f"✅ Config loaded from: {self.config_path}")
            except Exception as e:
                print(f"⚠️ Error loading config: {e}")
        else:
            print(f"⚠️ Config not found at: {self.config_path}")
            print("📝 Using default configuration")
            self.save_default_config()
    
    def save_default_config(self):
        """Save default config to file"""
        try:
            with open(self.config_path, 'w') as f:
                self.config.write(f)
            print(f"✅ Default config saved to: {self.config_path}")
        except Exception as e:
            print(f"⚠️ Could not save default config: {e}")
    
    def get_db_config(self):
        """Get database configuration"""
        return {
            'host': self.config['DEFAULT']['SERVERNAME'],
            'user': self.config['DEFAULT']['USERNAME'],
            'password': self.config['DEFAULT']['PASSWORD'],
            'port': int(self.config['DEFAULT']['PORT']),
            'database': self.config['DEFAULT']['DATABASE'],
            'charset': 'utf8'
        }
    
    def get_mail_config(self):
        """Get email configuration"""
        return {
            'sender': self.config['MAIL']['SENDER'],
            'password': self.config['MAIL']['PASSWORD'],
            'receiver': self.config['MAIL']['RECEIVER'],
            'cc': self.config['MAIL']['CC'],
            'smtp_server': self.config['MAIL']['SMTPSERVER'],
            'smtp_port': int(self.config['MAIL']['SMTPPORT'])
        }
    
    def get_outlet(self):
        """Get outlet code"""
        return self.config['DEFAULT']['OUTLET']
    
    def get_api_config(self):
        """Get API configuration"""
        return {
            'base_url': self.config['API']['BASE_URL'],
            'timeout': int(self.config['API']['TIMEOUT']),
            'api_key': self.config['API']['API_KEY']
        }

settings = Settings()