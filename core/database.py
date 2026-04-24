# core/database.py
import os
import locale
import pymysql
from config.settings import settings

# Fix locale
os.environ["LC_ALL"] = "en_US.UTF-8"
os.environ["LANG"] = "en_US.UTF-8"

try:
    locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
except:
    pass


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
        if self.connection:
            return self.connection

        try:
            self.connection = pymysql.connect(
                host=self.config.get("host"),
                user=self.config.get("user"),
                password=self.config.get("password"),
                database=self.config.get("database"),
                port=int(self.config.get("port", 3306)),
                charset=self.config.get("charset", "utf8"),
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
            return self.connection
        except Exception as e:
            raise Exception(f"Database connection failed: {e}")

    def close(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def execute_query(self, query, params=None):
        if not self.connection:
            self.connect()

        self.connection.ping(reconnect=True)
        
        with self.connection.cursor() as cursor:
            cursor.execute(query, params or ())

            if query.strip().upper().startswith("SELECT"):
                return cursor.fetchall()
            else:
                return cursor.rowcount

class TransactionData:
    @staticmethod
    def get_transactions(saledate):
        with DatabaseConnection() as db:
            return db.execute_query(
                "SELECT * FROM bsum_trans WHERE saledate = %s",
                (saledate,)
            )

    @staticmethod
    def get_dine_in(saledate):
        with DatabaseConnection() as db:
            return db.execute_query(
                "SELECT * FROM bsum_menu WHERE saledate = %s AND salemode = 1",
                (saledate,)
            )

    @staticmethod
    def get_takeaway(saledate):
        with DatabaseConnection() as db:
            return db.execute_query(
                "SELECT * FROM bsum_menu WHERE saledate = %s AND salemode = 2",
                (saledate,)
            )

    @staticmethod
    def get_sales_header(last_id, saledate):
        query = """
            SELECT *
            FROM vw_ordertransaction
            WHERE ReceiptID > %s AND saledate = %s
        """
        with DatabaseConnection() as db:
            return db.execute_query(query, (last_id, saledate))

    @staticmethod
    def get_sales_detail(transaction_ids):
        if not transaction_ids:
            return []

        placeholders = ",".join(["%s"] * len(transaction_ids))

        query = f"""
            SELECT *
            FROM vw_orderdetail
            WHERE TransactionID IN ({placeholders})
        """

        with DatabaseConnection() as db:
            return db.execute_query(query, tuple(transaction_ids))