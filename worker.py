import time
import os
import sys
import signal
import traceback
from core.api_client import APIClient
from queue_db import init_db

LOCK_FILE = "worker.lock"
RUNNING = True


# ==============================
# 🔒 LOCK (anti double worker)
# ==============================
def acquire_lock():
    if os.path.exists(LOCK_FILE):
        print("⚠️ Worker sudah berjalan, keluar...")
        sys.exit(0)

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))


def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)


# ==============================
# 🛑 HANDLE EXIT (CTRL+C / kill)
# ==============================
def handle_exit(signum, frame):
    global RUNNING
    print("\n🛑 Stop signal diterima, shutdown worker...")
    RUNNING = False


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


# ==============================
# 🔁 WORKER LOOP
# ==============================
def run_worker():
    print("🚀 Worker started...")

    client = APIClient()

    while RUNNING:
        try:
            client.process_queue()
        except Exception as e:
            print(f"❌ Worker error: {e}")
            traceback.print_exc()

        time.sleep(10)  # interval


# ==============================
# 🚀 MAIN
# ==============================
if __name__ == "__main__":
    try:
        print("🔧 Init DB...")
        init_db()

        print("🔒 Acquire lock...")
        acquire_lock()

        run_worker()

    finally:
        print("🧹 Cleanup lock...")
        release_lock()
        print("👋 Worker stopped")