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
    def get_sales_detail(transaction_ids, date_str):
        if not transaction_ids:
            return []

        placeholders = ",".join(["%s"] * len(transaction_ids))

        query = f"""
            SELECT *
            FROM vw_orderdetail
            WHERE TransactionID IN ({placeholders}) AND  CAST(SaleDate AS DATE) = %s    
        """

        with DatabaseConnection() as db:
            return db.execute_query(query, tuple(transaction_ids) + (date_str,))

    # Error MySQL yang berarti view vw_orderpaydetail belum siap di outlet ini:
    # 1146 = tabel/view tidak ada, 1356 = view ada tapi merujuk kolom/tabel
    # yang tidak ada.
    VIEW_BELUM_SIAP = (1146, 1356)

    @staticmethod
    def get_sales_payment(transaction_ids, date_str):
        """
        Baris pembayaran dari vw_orderpaydetail.

        Mengembalikan None (bukan []) kalau view belum dibuat di outlet ini,
        supaya pemanggil bisa membedakan "tidak diketahui" dari "tidak ada
        pembayaran". Lihat docs/perubahan-agen-pos-payments.md bagian 5.2.
        """
        if not transaction_ids:
            return []

        placeholders = ",".join(["%s"] * len(transaction_ids))

        query = f"""
            SELECT *
            FROM vw_orderpaydetail
            WHERE TransactionID IN ({placeholders}) AND CAST(SaleDate AS DATE) = %s
        """

        try:
            with DatabaseConnection() as db:
                return db.execute_query(query, tuple(transaction_ids) + (date_str,))
        except pymysql.err.MySQLError as e:
            if e.args and e.args[0] in TransactionData.VIEW_BELUM_SIAP:
                return None
            raise