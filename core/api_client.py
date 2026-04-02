import requests
import json
import time
from config.settings import settings
from queue_db import insert_queue, get_pending, mark_sent, increase_retry


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
            data = {
                "date": date_str,
                "batch_id": f"BATCH-{int(time.time())}",
                "source": "pos_closing_system",
 
                "outlet": getattr(self, "outlet_code", None),
                "sales": payload
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
                payload = json.loads(payload_str)

                print(f"📤 Kirim ID {id} (retry: {retry_count})")

                response = self._send(payload)
                #print("PAYLOAD:", json.dumps(payload, indent=2))
                print("STATUS:", response.status_code)

                if response.status_code == 200:
                    mark_sent(id)
                    print(f"✅ ID {id} sukses dikirim & dihapus")
                else:
                    increase_retry(id)
                    print(f"⚠️ ID {id} gagal (status {response.status_code})")

            except requests.exceptions.RequestException:
                print(f"❌ ID {id} gagal koneksi")
                increase_retry(id)

            except Exception as e:
                print(f"❌ Error ID {id}: {e}")
                increase_retry(id)

            # 🔥 backoff
            time.sleep(1 + retry_count)