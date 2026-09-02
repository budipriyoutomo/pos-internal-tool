"""
Lock file worker.

Dipakai bersama oleh worker.py dan GUI supaya keduanya menunjuk ke file yang
sama. Sebelumnya worker.py memakai path relatif ("worker.lock") yang resolve ke
current working directory, sementara main.py membersihkannya di folder exe —
kalau CWD berbeda, lock basi tidak pernah terhapus dan worker keluar diam-diam.
"""

import os

from queue_db import get_base_path

LOCK_FILE = os.path.join(get_base_path(), "worker.lock")

# GetExitCodeProcess mengembalikan nilai ini selama proses masih hidup.
_STILL_ACTIVE = 259
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def read_lock_pid():
    """PID yang tercatat di lock file, atau None kalau tidak ada/rusak."""
    try:
        with open(LOCK_FILE, "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def pid_alive(pid):
    """True kalau proses dengan PID tersebut benar-benar masih berjalan."""
    if not pid or pid <= 0:
        return False

    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )

        if not handle:
            return False

        try:
            code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return code.value == _STILL_ACTIVE
            return True
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def worker_running():
    """True kalau ada worker hidup yang memegang lock."""
    return pid_alive(read_lock_pid())


def clear_stale_lock():
    """Hapus lock yang ditinggal proses mati. True kalau ada yang dihapus."""
    if not os.path.exists(LOCK_FILE):
        return False

    if worker_running():
        return False

    try:
        os.remove(LOCK_FILE)
        return True
    except OSError:
        return False


def acquire_lock():
    """Ambil lock. False kalau worker lain memang sedang berjalan."""
    if worker_running():
        return False

    clear_stale_lock()

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))

    return True


def release_lock():
    """Lepas lock, hanya kalau memang milik proses ini."""
    pid = read_lock_pid()

    if pid is not None and pid != os.getpid():
        return

    try:
        os.remove(LOCK_FILE)
    except OSError:
        pass
