# controllers/dashboard_controller.py
import datetime
from core.database import TransactionData
from core.report_generator import ReportGenerator
from core.email_sender import EmailSender
from config.settings import settings

class DashboardController:
    def __init__(self, view):
        self.view = view
        self.report_generator = ReportGenerator()
        self.email_sender = EmailSender()
    
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
            self.view.log(f"❌ Error: {str(e)}")
            self.view.show_error("Error", str(e))
            return False