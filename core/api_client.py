import requests
import json
import time 
from config.settings import settings
import os

from queue_db import (
    insert_queue,
    get_pending,
    mark_sent,
    increase_retry,
    get_base_path,
)
from datetime import date
import requests

class APIClient:
    def __init__(self):
        self.base_url = settings.get_api_config()['base_url'] 
        self.timeout = settings.get_api_config()['timeout']
        self.api_key = settings.get_api_config()['api_key']

    # ==============================
    # 📥 ENQUEUE (JSON)
    # ============================== 

    def enqueue_sales(self, date_str, payload):
        try:
            #
            #data = {
            #    "date": date_str,
            #    "batch_id": f"BATCH-{int(time.time())}",
            #    "source": "pos_closing_system",
# 
#                "outlet": getattr(self, "outlet_code", None),
#                "sales": payload
#           }

            data = {
                    "meta": {
                        "date": date_str,
                        "batch_id": f"BATCH-{int(time.time())}",
                        "source": "pos_closing_system"
                    },
                    "payload": payload   # simpan di wrapper
                }

            insert_queue(json.dumps(data))

            print(f"📥 {len(payload)} transaksi masuk queue")

            return {
                "success": True,
                "message": "Data masuk queue"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    # ==============================
    # 📤 INTERNAL SEND (JSON)
    # ==============================
    def _send(self, payload):
        endpoint = f"{self.base_url}/sync/sales"

        headers = {
            "Authorization": f"Bearer {settings.get_api_config()['api_key']}",
            "User-Agent": "PromisePOS-Internal/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        response = requests.post(
            endpoint,
            json=payload,   
            headers=headers,
            timeout=self.timeout,
        )

        return response
    
    def close_colorplate(self, date_str=None):
        endpoint = f"{self.base_url}/sales/publish?t={time.time()}" 

        headers = {
            "Authorization": f"Bearer {settings.get_api_config()['api_key']}",
            "User-Agent": "PostmanRuntime/7.54.0",
            "Accept": "*/*",
            "Content-Type": "application/json",
            "Cache-Control": "no-cache",
            "Connection": "close",
        }


        payload = {
            "exchange": "posdata_exchange",
            "routing_key": "posdata.created",
            "date": date_str or date.today().isoformat(),
        }

        response = requests.post(
            endpoint,
            json=payload,
            headers=headers, 
            timeout=30,
        )
  
        return response
    
    # ==============================
    # 💾 SIMPAN PAYLOAD TERAKHIR (diagnostik)
    # ==============================
    @staticmethod
    def _dump_payload(date_str, payload):
        """Simpan payload apa adanya supaya bisa dibandingkan dengan apa yang
        dilihat backend. Satu file per tanggal, ditimpa tiap pengiriman."""
        try:
            log_dir = os.path.join(get_base_path(), "logs")
            os.makedirs(log_dir, exist_ok=True)

            path = os.path.join(log_dir, f"last_payload_{date_str}.json")

            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)

            return path

        except Exception as e:
            print(f"⚠️ Gagal menyimpan payload: {e}")
            return None

    # ==============================
    # 🔎 RINGKASAN PAYLOAD (diagnostik)
    # ==============================
    @staticmethod
    def _summarize(sales):
        """Ringkas isi payload untuk log — supaya ketahuan kalau tanggal
        yang dikirim tidak sesuai dengan tanggal yang diminta saat publish."""
        if not sales:
            return "payload kosong"

        sale_dates = sorted({str(s.get("sale_date")) for s in sales})
        null_trx_date = sum(1 for s in sales if not s.get("trx_date"))
        no_items = sum(1 for s in sales if not s.get("items"))
        receipt_ids = [s.get("receipt_id") or 0 for s in sales]

        return (
            f"{len(sales)} transaksi | sale_date={sale_dates} | "
            f"receipt_id {min(receipt_ids)}..{max(receipt_ids)} | "
            f"trx_date kosong: {null_trx_date} | tanpa items: {no_items}"
        )

    # ==============================
    # 🔁 PROCESS QUEUE (worker)
    # ==============================
    def process_queue(self):
        items = get_pending(limit=10)

        if not items:
            return

        print(f"📦 Proses {len(items)} queue...")

        for id, payload_str, retry_count in items:
            try:
                payload_wrapper = json.loads(payload_str)

                real_payload = payload_wrapper.get("payload", payload_wrapper)
                sales = real_payload.get("sales", [])

                meta = payload_wrapper.get("meta", {})

                print(
                    f"📤 Kirim ID {id} → {self.base_url}/sync/sales "
                    f"(retry {retry_count}, date={meta.get('date')}, "
                    f"batch={meta.get('batch_id')})"
                )
                print(f"🔎 {self._summarize(sales)}")

                dumped = self._dump_payload(
                    meta.get("date", "unknown"), real_payload
                )
                if dumped:
                    print(f"💾 Payload disimpan: {dumped}")

                response = self._send(real_payload)

                body = response.text or ""

                # Banyak backend membalas HTTP 200 tapi isinya success:false.
                # Tanpa cek body, data dianggap terkirim padahal ditolak.
                rejected = False
                try:
                    parsed = response.json()
                    if isinstance(parsed, dict) and parsed.get("success") is False:
                        rejected = True
                except ValueError:
                    parsed = None

                # Terima seluruh 2xx, bukan hanya 200 — backend bisa balas 201/202.
                if 200 <= response.status_code < 300 and not rejected:
                    mark_sent(id)

                    print(f"✅ ID {id} terkirim (status {response.status_code})")
                    print(f"📨 Response: {body[:1000]}")

                else:
                    increase_retry(id)

                    alasan = (
                        "body success:false"
                        if rejected
                        else f"status {response.status_code}"
                    )

                    print(f"⚠️ ID {id} ditolak server ({alasan})")
                    print(f"📨 Response: {body[:1000]}")

            except requests.exceptions.RequestException as e:
                increase_retry(id)
                print(f"❌ ID {id} gagal koneksi: {e}")

            except Exception as e:
                increase_retry(id)
                print(f"❌ Error ID {id}: {e}")

            # 🔥 backoff
            time.sleep(1 + retry_count)
