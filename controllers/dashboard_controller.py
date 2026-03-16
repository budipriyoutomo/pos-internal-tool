# controllers/dashboard_controller.py
import datetime
from core.database import TransactionData
from core.report_generator import ReportGenerator
from core.email_sender import EmailSender
from config.settings import settings
from core.api_client import APIClient
import json
    
class DashboardController:
    def __init__(self, view):
        self.view = view
        self.report_generator = ReportGenerator()
        self.email_sender = EmailSender()
        self.api_client = APIClient()
    
    def process_closing(self, date_str):
        try:
            self.view.log("📊 Mengambil data transaksi...")
            
            # Get data sesuai format original
            transactions = TransactionData.get_transactions(date_str)  # bsum_trans
            dine_in = TransactionData.get_dine_in(date_str)           # bsum_menu salemode=1
            takeaway = TransactionData.get_takeaway(date_str)         # bsum_menu salemode=2
            
            self.view.log(f"✅ Ditemukan: {len(dine_in)} Dine In, {len(takeaway)} Take Away")
            
            if transactions:
                self.view.log(f"✅ Data transaksi: {len(transactions)} record")
            
            # Generate report dengan format original
            self.view.log("📝 Membuat laporan dengan format original...")
            outlet = settings.get_outlet()
            filename = self.report_generator.generate(
                outlet, 
                date_str, 
                transactions,  # bsum_trans
                dine_in,       # bsum_menu salemode=1
                takeaway       # bsum_menu salemode=2
            )
            self.view.log(f"✅ Laporan dibuat: {filename}")
            
            # Send email
            if self.view.ask_yes_no("Konfirmasi", "Kirim laporan via email?"):
                self.view.log("📧 Mengirim email...")
                subject = f"Consolidate Report {outlet} {date_str}"
                body = f"""
Consolidate Report from Promise System
Outlet: {outlet}
Tanggal: {date_str}
Waktu Generate: {datetime.datetime.now().strftime('%d %B %Y %H:%M:%S')}

Terlampir laporan penjualan dalam format text.

--
Promise POS System
                """
                self.email_sender.send_report(subject, body, filename)
                self.view.log("✅ Email terkirim!")
            
            return True
        except Exception as e:
            import traceback
            traceback.print_exc()   # tampilkan error asli di console
            self.view.log(f"❌ Error: {str(e)}")
            self.view.show_error("Error", str(e))
            return False

    def send_to_api(self, date_str):
        """Send menu data to API"""
        try:
            self.log_info("📤 Mengirim data ke API...")
            
            # Ambil data dari database
            menu_data = TransactionData.get_detail_menu(date_str)
            columns = TransactionData.get_detail_menu_columns()
            
            if not menu_data:
                self.log_warning("Tidak ada data menu untuk tanggal ini")
                return False
            
            self.log_info(f"📊 Data menu: {len(menu_data)} rows, columns: {columns}")
            
            # Kirim ke API
            result = self.api_client.send_sales_menu(date_str, menu_data, columns)
            
            if result['success']:
                self.log_success(f"Data terkirim! Response: {result.get('response', 'OK')}")
                
                # Simpan log pengiriman
                self.save_api_log(date_str, result)
                return True
            else:
                self.log_error(f"Gagal kirim: {result.get('error', 'Unknown error')}")
                self.log_error(f"Status code: {result.get('status_code', 'N/A')}")
                
                # Tampilkan saran
                self.show_api_error_suggestions(result)
                return False
                
        except Exception as e:
            self.log_error(f"Error API: {str(e)}")
            return False

    def save_api_log(self, date_str, result):
        """Simpan log pengiriman API"""
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'date': date_str,
            'success': result['success'],
            'endpoint': result.get('endpoint', 'N/A'),
            'status_code': result.get('status_code', 'N/A'),
            'response': result.get('response', '')
        }
        
        # Simpan ke file log
        log_file = settings.LOGS_DIR / f"api_log_{date_str}.json"
        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)

    def show_api_error_suggestions(self, result):
        """Tampilkan saran untuk error API"""
        suggestions = [
            "\n💡 SARAN PERBAIKAN:",
            "1. Cek URL API yang benar (mungkin berbeda)",
            "2. Pastikan API server sedang running",
            "3. Cek koneksi internet",
            "4. Tanyakan dokumentasi API ke tim backend",
            "5. Coba endpoint: /api/upload, /api/menu, /api/sales"
        ]
        
        if 'tried_endpoints' in result:
            suggestions.append(f"\nEndpoint yang dicoba: {', '.join(result['tried_endpoints'])}")
        
        for s in suggestions:
            self.log_warning(s)