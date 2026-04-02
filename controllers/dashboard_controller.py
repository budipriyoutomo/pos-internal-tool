# controllers/dashboard_controller.py
import datetime
from core.database import TransactionData
from core.report_generator import ReportGenerator
from core.email_sender import EmailSender
from config.settings import settings
from core.api_client import APIClient
from queue_db import ( 
    get_last_sync,
    update_last_sync
)

import json
    
class DashboardController:
    def __init__(self, view):
        self.view = view
        self.report_generator = ReportGenerator()
        self.email_sender = EmailSender()
        self.api_client = APIClient()

    # ===== LOG HELPERS =====
    def log_info(self, message):
        self.view.log(message)

    def log_success(self, message):
        self.view.log(f"✅ {message}")

    def log_warning(self, message):
        self.view.log(f"⚠️ {message}")

    def log_error(self, message):
        self.view.log(f"❌ {message}")
    
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
        try:
            self.log_info("📤 Menyiapkan data untuk dikirim...")

            last_id = int(get_last_sync() or 0)
 
            headers = TransactionData.get_sales_header(last_id, date_str)

            if not headers:
                self.log_warning("Tidak ada header untuk dikirim")
                return False
 
            if isinstance(headers[0], tuple):
                raise Exception("Database return tuple, harus dict (fix execute_query)")
 
            trx_ids = [h["TransactionID"] for h in headers]
 
            details = TransactionData.get_sales_detail(trx_ids)

            if details and isinstance(details[0], tuple):
                raise Exception("Database return tuple, harus dict (fix execute_query)")
  
            payload = self.build_payload(headers, details)
            print(payload)
              
            if not payload:
                self.log_warning("Payload kosong setelah build")
                return False

            self.log_info(f"📦 Total transaksi: {len(payload)}")

            # 🔥 DEBUG (optional)
            print(json.dumps(payload[:1], indent=2))

            # ✅ masuk queue
            self.api_client.enqueue_sales(date_str, payload)
 
            new_last_id = max(h["TransactionID"] for h in headers)

            update_last_sync(str(new_last_id))

            self.log_success(f"Sync berhasil sampai ID {new_last_id}")

            return True

        except Exception as e:
            self.log_error(f"❌ Error enqueue: {str(e)}")
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
             
    def build_payload(self, headers, details):
        detail_map = {}
 
        for d in details:
            trx_id = d["TransactionID"]

            if trx_id not in detail_map:
                detail_map[trx_id] = []

            detail_map[trx_id].append({
                "order_detail_id": d["OrderDetailID"],
                "product_id": d["ProductID"],
                "product_name": d.get("Name"),
                "qty": float(d["Amount"]),
                "price": float(d["Price"]), 
            })
 
        result = []

        for h in headers:
            trx_id = h["TransactionID"]

            result.append({
                "transaction_id": trx_id,
                "outlet_code": h.get("outlet_code"),
                "sale_date": str(h.get("SaleDate")),
                "total_amount": float(h.get("ReceiptTotalAmount", 0)),
                "items": detail_map.get(trx_id, [])
            })

        return result