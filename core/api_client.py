import requests
import json
import time 
from config.settings import settings
from queue_db import insert_queue, get_pending, mark_sent, increase_retry, update_last_sync
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
    
    def close_colorplate(self, payload=None):
        endpoint = f"{self.base_url}/sales/publish"

        headers = {
            "Authorization": f"Bearer {settings.get_api_config()['api_key']}",
            "User-Agent": "PromisePOS-Internal/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        # ✅ Default payload kalau tidak dikirim dari luar
        if payload is None:
            payload = {
                "exchange": "posdata_exchange",
                "routing_key": "posdata.created",
                "date": date.today().isoformat(),  # otomatis hari ini
            }

        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=self.timeout,
        )

        return response
    
    # ==============================
    # 🔁 PROCESS QUEUE (worker)
    # ==============================
    def process_queue(self):
        items = get_pending(limit=10)

        if not items:
            print("📭 Queue kosong")
            return

        print(f"📦 Proses {len(items)} queue...")

        for id, payload_str, retry_count in items:
            try:
                payload_wrapper = json.loads(payload_str)

                # ✅ FIX DISINI
                real_payload = payload_wrapper.get("payload", payload_wrapper)

                #print("FINAL PAYLOAD:")
                #print(json.dumps(real_payload, indent=2))

                response = self._send(real_payload)

                print(json.dumps(real_payload, indent=2))

                if response.status_code == 200:
                    mark_sent(id)

                    sales = real_payload.get("sales", [])

                    if sales:
                        try:
                            last_receipt_id = max(
                                int(s.get("receipt_id", 0)) for s in sales
                            )

                            if last_receipt_id > 0:
                                #update_last_sync(str(last_receipt_id))
                                print(f"🧠 last_sync updated → {last_receipt_id}")
                            else:
                                print("⚠️ last_receipt_id invalid")

                        except Exception as e:
                            print(f"❌ gagal hitung last_receipt_id: {e}")

                    print(f"✅ ID {id} sukses dikirim & dihapus")
                else:
                    increase_retry(id)
                    print(f"⚠️ ID {id} gagal (status {response.status_code})")
                    print(f"Response: {response.text}")

            except requests.exceptions.RequestException:
                print(f"❌ ID {id} gagal koneksi")
                increase_retry(id)

            except Exception as e:
                print(f"❌ Error ID {id}: {e}")
                increase_retry(id)

            # 🔥 backoff
            time.sleep(1 + retry_count)