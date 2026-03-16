# core/database.py
import os 
import locale 

os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except:
    pass
import mysql.connector
from mysql.connector import Error
from config.settings import settings

class DatabaseConnection:
    def __init__(self):
        self.connection = None
        self.config = settings.get_db_config()
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def connect(self):
        try:
            self.connection = mysql.connector.MySQLConnection(**self.config)
            return self.connection
        except Error as e:
            raise Exception(f"Database connection failed: {e}")
    
    def close(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()
    
    def execute_query(self, query, params=None):
        cursor = None
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                self.connection.commit()
                return cursor.rowcount
        finally:
            if cursor:
                cursor.close()

class TransactionData:
    @staticmethod
    def get_transactions(saledate):
        with DatabaseConnection() as db:
            return db.execute_query("SELECT * FROM bsum_trans WHERE saledate = %s", (saledate,))
    
    @staticmethod
    def get_dine_in(saledate):
        with DatabaseConnection() as db:
            return db.execute_query("SELECT * FROM bsum_menu WHERE saledate = %s AND salemode = 1", (saledate,))
    
    @staticmethod
    def get_takeaway(saledate):
        with DatabaseConnection() as db:
            return db.execute_query("SELECT * FROM bsum_menu WHERE saledate = %s AND salemode = 2", (saledate,))
     
    @staticmethod
    def get_detail_menu(saledate):
        """Get detail menu for API"""
        query = "SELECT * FROM detail_menu WHERE saledate = %s"
        with DatabaseConnection() as db:
            return db.execute_query(query, (saledate,))
        
    @staticmethod
    def get_detail_menu_columns():
        """Get column names for detail_menu table"""
        query = "SHOW COLUMNS FROM detail_menu"
        with DatabaseConnection() as db:
            columns = db.execute_query(query)
            return [col[0] for col in columns]   