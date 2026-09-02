import io
import logging
import os
import signal
import sys
import time
import traceback
from logging.handlers import RotatingFileHandler

# Konsol Windows memakai cp1252. Modul lain mencetak emoji saat diimpor
# (config.settings), dan itu melempar UnicodeEncodeError yang mematikan worker
# sebelum logging sempat aktif. Amankan stream sebelum impor apa pun dari proyek.
for _nama_stream in ("stdout", "stderr"):
    _stream = getattr(sys, _nama_stream, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from core.worker_lock import LOCK_FILE, acquire_lock, read_lock_pid, release_lock
from queue_db import get_base_path, init_db

LOG_DIR = os.path.join(get_base_path(), "logs")
LOG_FILE = os.path.join(LOG_DIR, "worker.log")

RUNNING = True


# ==============================
# 📝 LOGGING
# ==============================
class _StreamToLog(io.TextIOBase):
    """Alihkan print()/traceback ke logger, per baris."""

    def __init__(self, emit):
        self._emit = emit
        self._buf = ""

    def write(self, text):
        self._buf += text

        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.strip():
                self._emit(line)

        return len(text)

    def flush(self):
        if self._buf.strip():
            self._emit(self._buf)
        self._buf = ""


def setup_logging():
    """
    Worker dibangun dengan console=False dan dijalankan CREATE_NO_WINDOW, jadi
    tanpa ini semua output-nya hilang dan kegagalan kirim tidak terlihat.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("[%(asctime)s] %(levelname)s %(message)s")
    )

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers = [handler]

    # api_client memakai print(); tangkap supaya ikut masuk log.
    sys.stdout = _StreamToLog(logging.getLogger("worker.out").info)
    sys.stderr = _StreamToLog(logging.getLogger("worker.err").error)


# ==============================
# 🛑 HANDLE EXIT (CTRL+C / kill)
# ==============================
def handle_exit(signum, frame):
    global RUNNING
    logging.info("🛑 Stop signal diterima, shutdown worker...")
    RUNNING = False


signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)


# ==============================
# 🔁 WORKER LOOP
# ==============================
def run_worker():
    # Diimpor di sini, bukan di level modul, supaya pesan yang dicetak
    # config.settings saat diimpor ikut masuk ke worker.log.
    from core.api_client import APIClient

    logging.info("🚀 Worker started (pid %s)", os.getpid())

    client = APIClient()

    while RUNNING:
        try:
            client.process_queue()
        except Exception as e:
            logging.error("❌ Worker error: %s", e)
            logging.error(traceback.format_exc())

        # Tidur bertahap supaya stop signal cepat direspons.
        for _ in range(10):
            if not RUNNING:
                break
            time.sleep(1)


# ==============================
# 🚀 MAIN
# ==============================
if __name__ == "__main__":
    setup_logging()

    locked = False

    try:
        logging.info("🔧 Init DB...")
        init_db()

        logging.info("🔒 Acquire lock: %s", LOCK_FILE)
        locked = acquire_lock()

        if not locked:
            logging.warning(
                "⚠️ Worker lain sudah berjalan (pid %s), keluar...",
                read_lock_pid(),
            )
            sys.exit(0)

        run_worker()

    except SystemExit:
        raise

    except Exception as e:
        logging.error("❌ Worker gagal start: %s", e)
        logging.error(traceback.format_exc())

    finally:
        if locked:
            logging.info("🧹 Cleanup lock...")
            release_lock()

        logging.info("👋 Worker stopped")
