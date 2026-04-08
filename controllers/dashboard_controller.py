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
            print(f"🧠 last_sync: {last_id}")
 
            headers = TransactionData.get_sales_header(last_id, date_str)
            print(f"📊 Ditemukan {len(headers)} transaksi baru sejak ID {last_id}")

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
              
            if not payload.get("sales"):
                self.log_warning("Payload kosong setelah build")
                return False

            self.log_info(f"📦 Total transaksi: {len(payload['sales'])}")

            # 🔥 DEBUG (optional)
            print("PAYLOAD PREVIEW:")
            print(json.dumps(payload["sales"][:1], indent=2))
 
            
            # ✅ masuk queue
            self.api_client.enqueue_sales(date_str, payload)
 
            new_last_id = max(h["TransactionID"] for h in headers) 

            self.log_success(f"Sync berhasil sampai ID {new_last_id}")

            #update_last_sync(str(new_last_id))

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

        def to_iso(dt):
            if not dt:
                return None
            return dt.isoformat() if hasattr(dt, "isoformat") else str(dt)

        detail_map = {}
        self.log_error("🔹 Membangun payload untuk API...")
        # 🔹 mapping detail ke item (SUDAH SESUAI FORMAT BARU)
        for d in details:
            trx_id = int(d["TransactionID"])

            if trx_id not in detail_map:
                detail_map[trx_id] = []

            detail_map[trx_id].append({
                "order_detail_id": int(d["OrderDetailID"]),  # ✅ rename
                "transaction_id": trx_id,
                "sale_date": str(d.get("SaleDate")),

                "product_id": int(d["ProductID"]),
                "product_name": str(d.get("ProductName")),
                "product_group": str(d.get("ProductGroupName")),
                "product_dept": str(d.get("ProductDeptName")),

                "product_set_type": int(d.get("ProductSetType", 0)),
                "order_status_id": int(d.get("OrderStatusID", 2)),
                "sale_mode": int(d.get("SaleMode", 1)),

                "qty": float(d["Amount"]),
                "price": float(d["Price"]),
                "retail_price": float(d.get("RetailPrice", d.get("Price", 0))),
                "minimum_price": float(d.get("MinimumPrice", 0)),

                "comment": d.get("Comment") or "",
                "order_staff_id": int(d.get("OrderStaffID", 0)),
                "order_table_id": int(d.get("OrderTableID", 0)),
                "void_staff_id": int(d.get("VoidStaffID", 0)),
            })

        result = []

        # 🔹 mapping header ke sales (SUDAH FULL SESUAI SPEC)
        for h in headers:
            trx_id = int(h["TransactionID"]) 

            paid_time = to_iso(h.get("PaidTime"))

            result.append({
                "transaction_id": trx_id,  # ✅ rename 
                "invoice_number": h.get("ReferenceNo"),  # ✅ rename

                "sale_date": str(h.get("SaleDate")),
                "paid_time": paid_time,
                "close_time": to_iso(h.get("CloseTime")),
                "trx_date": paid_time,  # ✅ tambahan WAJIB

                "shop_id": int(h.get("ShopID", 0)),
                "transaction_status_id": int(h.get("TransactionStatusID", 1)),
                "sale_mode": int(h.get("SaleMode", 1)),
                "no_customer": int(h.get("NoCustomer", 1)),
                "deleted": int(h.get("Deleted", 0)),

                "receipt_product_retail_price": float(h.get("ReceiptProductRetailPrice", 0)),
                "receipt_sale_price": float(h.get("ReceiptSalePrice", 0)),
                "receipt_pay_price": float(h.get("ReceiptPayPrice", 0)),
                "receipt_discount": float(h.get("ReceiptDiscount", 0)),
                "receipt_total_amount": float(h.get("ReceiptTotalAmount", 0)),

                "other_percent_discount": float(h.get("OtherPercentDiscount", 0)),
                "other_amount_discount": float(h.get("OtherAmountDiscount", 0)),

                "vat_percent": float(h.get("VATPercent", 0)),
                "transaction_vat": float(h.get("TransactionVAT", 0)),
                "transaction_exclude_vat": float(h.get("TransactionExcludeVAT", 0)),
                "transaction_vatable": float(h.get("TransactionVATable", 0)),

                "service_charge_percent": float(h.get("ServiceChargePercent", 0)),
                "service_charge": float(h.get("ServiceCharge", 0)),
                "service_charge_vat": float(h.get("ServiceChargeVAT", 0)),

                "other_income": float(h.get("OtherIncome", 0)),
                "other_income_vat": float(h.get("OtherIncomeVAT", 0)),

                "void_staff_id": int(h.get("VoidStaffID", 0)),
                "void_reason": h.get("VoidReason") or "",
                "void_time": to_iso(h.get("VoidTime")),

                "transaction_note": h.get("TransactionNote") or "",
                "queue_name": h.get("QueueName") or "",
                "reference_no": h.get("ReferenceNo"),

                "is_split_transaction": int(h.get("IsSplitTransaction", 0)),
                "is_from_other_transaction": int(h.get("IsFromOtherTransaction", 0)),

                # 🔥 RELATION
                "items": detail_map.get(trx_id, [])
            })

        return { 
            "sales": result
        }