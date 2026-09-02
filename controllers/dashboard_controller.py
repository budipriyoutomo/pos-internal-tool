# controllers/dashboard_controller.py
import datetime
import os
import time
from urllib import response
from core.database import TransactionData
from core.report_generator import ReportGenerator
from core.email_sender import EmailSender
from config.settings import settings
from core.api_client import APIClient
from core.worker_lock import worker_running
from queue_db import (
    get_base_path,
    queue_stats
)

import json
    
def _to_iso(value):
    """Datetime/date -> ISO string, None tetap None."""
    if not value:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _date_only(value):
    """
    Tanggal saja, tanpa jam: "2026-08-31".

    Kolom SaleDate di view berupa DATETIME, sehingga str() menghasilkan
    "2026-08-31 00:00:00" — tidak cocok dengan tanggal yang dipakai endpoint
    /sales/publish ("2026-08-31").
    """
    if value is None or value == "":
        return None

    if hasattr(value, "date"):
        return value.date().isoformat()

    if hasattr(value, "isoformat"):
        return value.isoformat()

    text = str(value).strip()

    # "2026-08-31 00:00:00" / "2026-08-31T00:00:00" -> "2026-08-31"
    for pisah in (" ", "T"):
        if pisah in text:
            return text.split(pisah, 1)[0]

    return text


def _group(value):
    """
    Samakan penamaan product group dengan yang diharapkan server.

    Master data TSTSM menulis "COLOR PLATE" (pakai spasi), sedangkan
    /api/sales/publish menyaring persis "COLORPLATE" — akibatnya seluruh item
    colorplate outlet itu tidak pernah ikut terpublish.
    """
    teks = _text(value)

    if teks.replace(" ", "").upper() == "COLORPLATE":
        return "COLORPLATE"

    return teks


def _text(value, default=""):
    """String, NULL -> default (bukan literal "None")."""
    if value is None:
        return default
    return str(value)


def _to_float(value, default=0.0):
    """float() yang aman terhadap kolom NULL / string kosong dari DB."""
    if value is None or value == "":
        return float(default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _to_int(value, default=0):
    """int() yang aman terhadap kolom NULL / string kosong / desimal dari DB."""
    if value is None or value == "":
        return int(default)
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return int(default)


# Kolom yang dibaca dari vw_ordertransaction / vw_orderdetail. Dipakai untuk
# memperingatkan kalau nama kolom di view tidak sesuai — tanpa ini kolom yang
# hilang diam-diam jadi 0 atau "".
HEADER_FIELDS = (
    "TransactionID", "ReferenceNo", "SaleDate", "PaidTime", "CloseTime",
    "ShopID", "TransactionStatusID", "SaleMode", "NoCustomer", "Deleted",
    "ReceiptID", "ReceiptMonth", "ReceiptYear",
    "ReceiptProductRetailPrice", "ReceiptSalePrice", "ReceiptPayPrice",
    "ReceiptDiscount", "ReceiptTotalAmount",
    "OtherPercentDiscount", "OtherAmountDiscount",
    "VATPercent", "TransactionVAT", "TransactionExcludeVAT",
    "TransactionVATable",
    "ServiceChargePercent", "ServiceCharge", "ServiceChargeVAT",
    "OtherIncome", "OtherIncomeVAT",
    "OpenStaffID", "PaidStaffID", "CommStaffID",
    "VoidStaffID", "VoidReason", "VoidTime",
    "TransactionNote", "QueueName",
    "IsSplitTransaction", "IsFromOtherTransaction",
)

DETAIL_FIELDS = (
    "TransactionID", "OrderDetailID", "SaleDate",
    "ProductID", "ProductName", "ProductGroupName", "ProductDeptName",
    "ProductSetType", "OrderStatusID", "SaleMode",
    "Amount", "Price", "RetailPrice", "MinimumPrice",
    "Comment", "OrderStaffID", "OrderTableID", "VoidStaffID",
)


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
        
    def close_colorplate(self, date_str):
        try:
            self.view.log(f"🔒 Menutup Colorplate tanggal {date_str}...")

            if not self.send_to_api(date_str):
                raise Exception("Gagal enqueue sales")

            # enqueue_sales() hanya menulis ke queue lokal; upload ke server
            # dikerjakan worker di proses terpisah. Tanpa menunggu queue kosong,
            # /sales/publish pasti menjawab "No sales data to publish".
            if not self.wait_for_queue_drain():
                raise Exception(
                    "Data belum sampai ke server, publish dibatalkan"
                )

            max_retry = 30
            pesan_terakhir = ""

            for i in range(max_retry):

                self.view.log(f"⏳ Checking sales publish readiness ({i+1}/{max_retry})")

                response = self.api_client.close_colorplate(date_str)
                self.view.log(f"Response: {response.text}")

                data = response.json()
                pesan_terakhir = data.get("message", "") or ""

                # SUCCESS PUBLISH
                if "published" in pesan_terakhir.lower():
                    self.view.log(f"✅ Colorplate tanggal {date_str} ditutup!")
                    return True

                time.sleep(2)

            # Bawa jawaban server apa adanya — "belum siap" saja menyembunyikan
            # alasan sebenarnya, padahal server sudah menyebutkannya.
            raise Exception(
                f"Server menolak publish setelah {max_retry} percobaan. "
                f"Jawaban terakhir: \"{pesan_terakhir}\". "
                "Data sudah masuk ke server, jadi masalahnya ada di syarat "
                "publish sisi server — bukan pengiriman."
            )

        except Exception as e:
            import traceback
            traceback.print_exc()   # tampilkan error asli di console
            self.view.log(f"❌ Error: {str(e)}")
            self.view.show_error("Error", str(e))
            return False
        
    def wait_for_queue_drain(self, timeout=300, interval=2):
        """
        Tunggu worker mengosongkan queue lokal.

        False kalau worker tidak jalan, berhenti di tengah jalan, atau data
        tidak terkirim sampai timeout.
        """
        pending, _ = queue_stats()

        if pending == 0:
            return True

        if not worker_running():
            self.log_error(
                "Worker tidak berjalan — data tertahan di queue lokal. "
                "Tutup aplikasi lalu buka lagi, atau jalankan worker.exe manual."
            )
            return False

        self.log_info(
            f"📡 Menunggu worker mengirim {pending} batch ke server..."
        )

        deadline = time.time() + timeout
        reported_retry = 0

        while time.time() < deadline:
            pending, max_retry = queue_stats()

            if pending == 0:
                self.log_success("Semua data terkirim ke server")
                return True

            if max_retry > reported_retry:
                reported_retry = max_retry
                self.log_warning(
                    f"Worker gagal mengirim (percobaan ke-{max_retry}) — "
                    "detail ada di logs/worker.log"
                )

            if not worker_running():
                self.log_error(
                    "Worker berhenti saat pengiriman — cek logs/worker.log"
                )
                return False

            time.sleep(interval)

        self.log_error(
            f"Timeout {timeout} detik, {pending} batch masih tertahan di queue"
        )
        return False

    def send_to_api(self, date_str): 
        try:

            self.log_info(f"📤 Menyiapkan data tanggal {date_str}")

            # =========================
            # HEADER
            # =========================
            # Selalu ambil SELURUH transaksi tanggal ini, tanpa saringan
            # ReceiptID. Watermark last_sync global tidak bisa dipakai di sini:
            # ReceiptID hanya menaik dalam satu bulan (ada kolom ReceiptMonth /
            # ReceiptYear), sehingga menutup tanggal yang lebih lama atau
            # tanggal di bulan baru akan menghasilkan 0 baris dan gagal diam-
            # diam. Server melakukan upsert, jadi mengirim ulang aman sekaligus
            # membuat koreksi transaksi lama ikut terkirim.
            headers = TransactionData.get_sales_header(0, date_str)

            print(f"📊 Header ditemukan: {len(headers)}")

            if not headers:
                self.log_error(
                    f"Tidak ada transaksi untuk tanggal {date_str}"
                )
                return False

            if isinstance(headers[0], tuple):
                raise Exception(
                    "Database return tuple, harus dict (fix execute_query)"
                )

            trx_ids = [h["TransactionID"] for h in headers]

            print(f"🧾 Transaction IDs:")
            print(trx_ids)

            # =========================
            # DETAIL
            # =========================
            details = TransactionData.get_sales_detail(
                trx_ids,
                date_str
            )

            print(f"📦 Detail ditemukan: {len(details)}")

            self.dump_source_sample(date_str, headers, details)

            if details and isinstance(details[0], tuple):
                raise Exception(
                    "Database return tuple, harus dict (fix execute_query)"
                )

            # =========================
            # DEBUG DETAIL
            # =========================
            detail_trx_ids = list(set(
                d["TransactionID"] for d in details
            ))

            print("📌 Detail transaction IDs:")
            print(detail_trx_ids)

            missing_detail = set(trx_ids) - set(detail_trx_ids)

            if missing_detail:
                print("❌ TRANSACTION TIDAK PUNYA DETAIL:")
                print(missing_detail)

            # =========================
            # BUILD PAYLOAD
            # =========================
            payload = self.build_payload(headers, details)

            if not payload.get("sales"):
                self.log_warning("Payload kosong setelah build")
                return False

            self.log_info(
                f"📦 Total transaksi payload: {len(payload['sales'])}"
            )

            # =========================
            # DEBUG PAYLOAD
            # =========================
            payload_trx_ids = [
                s["transaction_id"]
                for s in payload["sales"]
            ]

            print("🚀 Payload transaction IDs:")
            print(payload_trx_ids)

            missing_payload = set(trx_ids) - set(payload_trx_ids)

            if missing_payload:
                print("❌ HILANG SAAT BUILD PAYLOAD:")
                print(missing_payload)

            print("PAYLOAD PREVIEW:")
            print(json.dumps(payload["sales"][:1], indent=2))

            # =========================
            # ENQUEUE
            # =========================
            response = self.api_client.enqueue_sales(
                date_str,
                payload
            )

            if not response.get("success"):
                self.log_error(
                    f"Gagal memasukkan ke queue: {response.get('error')}"
                )
                return False

            new_last_id = max(
                h["ReceiptID"]
                for h in headers
            )

            # last_sync sengaja TIDAK dinaikkan di sini. Data baru masuk queue
            # lokal, belum sampai server — worker yang menaikkannya setelah
            # server membalas 2xx.
            self.log_info(
                f"📥 {len(payload['sales'])} transaksi masuk queue "
                f"(s/d ReceiptID {new_last_id}), menunggu worker mengirim..."
            )

            return True

        except Exception as e:

            import traceback
            traceback.print_exc()

            self.log_error(f"❌ Error enqueue: {str(e)}")

            return False
    
    def save_api_log(self, date_str, result):
        """Simpan log pengiriman API"""
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'date': date_str,
            'success': result['success'],
            'endpoint': result.get('endpoint', 'N/A'), 
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

    def dump_source_sample(self, date_str, headers, details):
        """
        Simpan struktur baris mentah dari view ke logs/.

        Dipakai untuk memastikan kolom yang dibaca payload memang ada dan
        berisi — kalau close_time / receipt_total_amount kosong di payload,
        file ini menunjukkan apakah sumbernya yang NULL atau nama kolomnya
        yang berbeda.
        """
        try:
            log_dir = os.path.join(get_base_path(), "logs")
            os.makedirs(log_dir, exist_ok=True)

            path = os.path.join(log_dir, f"source_sample_{date_str}.json")

            def profil(rows):
                if not rows:
                    return {"jumlah_baris": 0}

                kolom = list(rows[0].keys())

                return {
                    "jumlah_baris": len(rows),
                    "kolom": kolom,
                    "null_di_semua_baris": [
                        k for k in kolom
                        if all(r.get(k) is None for r in rows)
                    ],
                    "contoh_baris": rows[0],
                }

            data = {
                "tanggal": date_str,
                "header": profil(headers),
                "detail": profil(details),
            }

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.log_info(f"🔬 Struktur sumber disimpan: {path}")

        except Exception as e:
            self.log_warning(f"Gagal menyimpan struktur sumber: {e}")

    def warn_incomplete_sales(self, sales):
        """
        Peringatkan pola yang membuat server tidak mem-publish.

        Dibanding outlet yang publish-nya berhasil (close_time terisi di
        105/105 transaksi), outlet yang gagal punya close_time kosong di
        272/272. Dua kolom di bawah ini yang membedakan keduanya.
        """
        if not sales:
            return

        if not any(s.get("close_time") for s in sales):
            self.log_warning(
                f"close_time KOSONG di seluruh {len(sales)} transaksi. "
                "Kemungkinan besar hari itu belum di-close di POS — server "
                "hanya mem-publish transaksi yang sudah close."
            )

        if not any(s.get("receipt_total_amount") for s in sales):
            self.log_warning(
                f"receipt_total_amount 0 di seluruh {len(sales)} transaksi — "
                "cek kolom ReceiptTotalAmount di vw_ordertransaction."
            )

    def warn_missing_columns(self, rows, expected, label):
        """Peringatkan kalau view tidak punya kolom yang dibaca payload."""
        if not rows:
            return

        missing = [c for c in expected if c not in rows[0]]

        if missing:
            self.log_warning(
                f"Kolom {label} tidak ada di view, nilainya dikirim sebagai "
                f"default: {', '.join(missing)}"
            )

    def build_payload(self, headers, details):

        detail_map = {}
        null_id_rows = []
        grup_disamakan = {}
        self.log_info("🔹 Membangun payload untuk API...")

        self.warn_missing_columns(headers, HEADER_FIELDS, "header")
        self.warn_missing_columns(details, DETAIL_FIELDS, "detail")

        # 🔹 mapping detail ke item (SUDAH SESUAI FORMAT BARU)
        for d in details:
            trx_id = _to_int(d.get("TransactionID"))

            if not trx_id or d.get("OrderDetailID") is None or d.get("ProductID") is None:
                null_id_rows.append(
                    f"detail trx={d.get('TransactionID')} "
                    f"detail_id={d.get('OrderDetailID')} "
                    f"product_id={d.get('ProductID')}"
                )

            if trx_id not in detail_map:
                detail_map[trx_id] = []

            price = _to_float(d.get("Price"))

            grup_asli = _text(d.get("ProductGroupName"))
            grup = _group(d.get("ProductGroupName"))

            if grup != grup_asli:
                grup_disamakan[grup_asli] = grup_disamakan.get(grup_asli, 0) + 1

            detail_map[trx_id].append({
                "order_detail_id": _to_int(d.get("OrderDetailID")),  # ✅ rename
                "transaction_id": trx_id,
                "sale_date": _date_only(d.get("SaleDate")),

                "product_id": _to_int(d.get("ProductID")),
                "product_name": _text(d.get("ProductName")),
                "product_group": grup,
                "product_dept": _text(d.get("ProductDeptName")),

                "product_set_type": _to_int(d.get("ProductSetType")),
                "order_status_id": _to_int(d.get("OrderStatusID"), 2),
                "sale_mode": _to_int(d.get("SaleMode"), 1),

                "qty": _to_float(d.get("Amount")),
                "price": price,
                "retail_price": _to_float(d.get("RetailPrice"), price),
                "minimum_price": _to_float(d.get("MinimumPrice")),

                "comment": _text(d.get("Comment")),
                "order_staff_id": _to_int(d.get("OrderStaffID")),
                "order_table_id": _to_int(d.get("OrderTableID")),
                "void_staff_id": _to_int(d.get("VoidStaffID")),
            })

        result = []

        # 🔹 mapping header ke sales (SUDAH FULL SESUAI SPEC)
        for h in headers:
            trx_id = _to_int(h.get("TransactionID"))

            if not trx_id:
                null_id_rows.append(
                    f"header ref={h.get('ReferenceNo')} "
                    f"trx={h.get('TransactionID')}"
                )

            paid_time = _to_iso(h.get("PaidTime"))

            result.append({
                "transaction_id": trx_id,  # ✅ rename
                "invoice_number": h.get("ReferenceNo"),  # ✅ rename

                "sale_date": _date_only(h.get("SaleDate")),
                "paid_time": paid_time,
                "close_time": _to_iso(h.get("CloseTime")),
                "trx_date": paid_time,  # ✅ tambahan WAJIB

                "shop_id": _to_int(h.get("ShopID")),
                "transaction_status_id": _to_int(h.get("TransactionStatusID"), 1),
                "sale_mode": _to_int(h.get("SaleMode"), 1),
                "no_customer": _to_int(h.get("NoCustomer"), 1),
                "deleted": _to_int(h.get("Deleted")),

                "receipt_id": _to_int(h.get("ReceiptID")),
                "receipt_month": _to_int(h.get("ReceiptMonth")),
                "receipt_year": _to_int(h.get("ReceiptYear")),

                "receipt_product_retail_price": _to_float(h.get("ReceiptProductRetailPrice")),
                "receipt_sale_price": _to_float(h.get("ReceiptSalePrice")),
                "receipt_pay_price": _to_float(h.get("ReceiptPayPrice")),
                "receipt_discount": _to_float(h.get("ReceiptDiscount")),
                "receipt_total_amount": _to_float(h.get("ReceiptTotalAmount")),

                "other_percent_discount": _to_float(h.get("OtherPercentDiscount")),
                "other_amount_discount": _to_float(h.get("OtherAmountDiscount")),

                "vat_percent": _to_float(h.get("VATPercent")),
                "transaction_vat": _to_float(h.get("TransactionVAT")),
                "transaction_exclude_vat": _to_float(h.get("TransactionExcludeVAT")),
                "transaction_vatable": _to_float(h.get("TransactionVATable")),

                "service_charge_percent": _to_float(h.get("ServiceChargePercent")),
                "service_charge": _to_float(h.get("ServiceCharge")),
                "service_charge_vat": _to_float(h.get("ServiceChargeVAT")),

                "other_income": _to_float(h.get("OtherIncome")),
                "other_income_vat": _to_float(h.get("OtherIncomeVAT")),

                # Ada di SalesSchema tapi sebelumnya tidak pernah dikirim,
                # sehingga selalu tersimpan sebagai 0 di server.
                "open_staff_id": _to_int(h.get("OpenStaffID")),
                "paid_staff_id": _to_int(h.get("PaidStaffID")),
                "comm_staff_id": _to_int(h.get("CommStaffID")),

                "void_staff_id": _to_int(h.get("VoidStaffID")),
                "void_reason": _text(h.get("VoidReason")),
                "void_time": _to_iso(h.get("VoidTime")),

                "transaction_note": _text(h.get("TransactionNote")),
                "queue_name": _text(h.get("QueueName")),
                "reference_no": h.get("ReferenceNo"),

                "is_split_transaction": _to_int(h.get("IsSplitTransaction")),
                "is_from_other_transaction": _to_int(h.get("IsFromOtherTransaction")),

                # 🔥 RELATION
                "items": detail_map.get(trx_id, [])
            })

        if grup_disamakan:
            rincian = ", ".join(
                f"{asli!r} → 'COLORPLATE' ({n} item)"
                for asli, n in grup_disamakan.items()
            )
            self.log_info(f"🎨 Nama product group disamakan: {rincian}")

        self.warn_incomplete_sales(result)

        if null_id_rows:
            self.log_warning(
                f"{len(null_id_rows)} baris punya ID NULL (dikirim sebagai 0): "
                + "; ".join(null_id_rows[:5])
            )

        return {
            "sales": result
        }