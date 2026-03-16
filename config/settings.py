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
        
        
        # Colors
        self.THEME_COLORS = {
            'primary': '#2c3e50',
            'secondary': '#34495e',
            'accent': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'light': '#ecf0f1',
            'white': '#ffffff',
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

settings = Settings()