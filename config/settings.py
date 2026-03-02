# config/settings.py
import configparser
from pathlib import Path

class Settings:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_path = Path(__file__).parent.parent / 'config.ini'
        self.load_config()
        
        self.APP_NAME = "Promise POS Internal Tool"
        self.APP_VERSION = "1.0.0"
        
        # Paths
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
        if self.config_path.exists():
            self.config.read(self.config_path)
    
    def get_db_config(self):
        return {
            'host': self.config['DEFAULT']['SERVERNAME'],
            'user': self.config['DEFAULT']['USERNAME'],
            'password': self.config['DEFAULT']['PASSWORD'],
            'port': int(self.config['DEFAULT']['PORT']),
            'database': self.config['DEFAULT']['DATABASE'],
            'charset': self.config['DEFAULT']['CHARSET']
        }
    
    def get_mail_config(self):
        return {
            'sender': self.config['MAIL']['SENDER'],
            'password': self.config['MAIL']['PASSWORD'],
            'receiver': self.config['MAIL']['RECEIVER'],
            'cc': self.config['MAIL']['CC'],
            'smtp_server': self.config['MAIL']['SMTPSERVER'],
            'smtp_port': int(self.config['MAIL']['SMTPPORT'])
        }
    
    def get_outlet(self):
        return self.config['DEFAULT']['OUTLET']

settings = Settings()