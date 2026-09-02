# Architecture

## 1. Dua proses

Aplikasi berjalan sebagai dua proses OS yang terpisah dan hanya berkomunikasi
lewat file SQLite `queue.db`.

```
┌────────────────────────────────────────────────────────┐
│ PROSES 1 — GUI  (main.py / main.exe)                   │
│                                                        │
│  PromisePOSApp (tk.Tk)                                 │
│   └─ DashboardView (tk.Frame)                          │
│        └─ DashboardController                          │
│             ├─ TransactionData ──► MySQL POS           │
│             ├─ ReportGenerator ──► reports/*.txt       │
│             ├─ EmailSender     ──► SMTP SSL            │
│             └─ APIClient.enqueue_sales ──┐             │
└──────────────────────────────────────────┼─────────────┘
                                           ▼
                                    ┌─────────────┐
                                    │  queue.db   │  SQLite
                                    │  · queue    │
                                    │  · sync_state│
                                    └─────────────┘
                                           ▲
┌──────────────────────────────────────────┼─────────────┐
│ PROSES 2 — WORKER  (worker.py / worker.exe)            │
│                                                        │
│  loop tiap 10 detik:                                   │
│    APIClient.process_queue()                           │
│      ├─ ambil 10 row status='pending'                  │
│      ├─ POST {BASE_URL}/sync/sales                     │
│      ├─ 200  → DELETE row                              │
│      └─ else → retry_count += 1, backoff (1+retry) dtk │
└────────────────────────────────────────────────────────┘
```

GUI men-spawn worker lewat `PromisePOSApp.start_worker()`
([main.py:83](../main.py#L83)) dan me-`terminate()`-nya di `on_closing()`.
Saat frozen, urutan pencarian worker: `sys._MEIPASS/worker.exe` →
`<folder exe>/worker.exe` → `<folder exe>/worker.py`.

`worker.lock` mencegah dua worker berjalan bersamaan. File lock yatim (sisa
crash) dihapus oleh `main.py` saat startup.

## 2. Lapisan kode

| Lapisan | File | Tanggung jawab |
|---|---|---|
| Entry | `main.py`, `worker.py` | Bootstrap, window, subprocess, signal handling |
| View | `views/dashboard_view.py` | Widget, threading, tampilan log, dialog |
| Controller | `controllers/dashboard_controller.py` | Orkestrasi alur bisnis, build payload |
| Core | `core/*.py` | Akses DB, HTTP, SMTP, penulisan file report |
| Config | `config/settings.py` | Singleton `settings`: config.ini, path, tema |
| Storage | `queue_db.py` | Semua akses SQLite |

`models/`, `utils/`, `resources/` masih kosong (hanya `__init__.py`) — disiapkan
untuk pengembangan berikutnya.

## 3. Alur "Generate & Kirim"

[dashboard_controller.py:37](../controllers/dashboard_controller.py#L37)

```
DashboardView.on_generate()
  ├─ set is_processing = True, disable tombol
  └─ Thread → run_process()
       └─ DashboardController.process_closing(date_str)
            ├─ TransactionData.get_transactions(date)   → bsum_trans
            ├─ TransactionData.get_dine_in(date)        → bsum_menu salemode=1
            ├─ TransactionData.get_takeaway(date)       → bsum_menu salemode=2
            ├─ ReportGenerator.generate(...)            → reports/{OUTLET}_{date}.txt
            ├─ view.ask_yes_no("Kirim laporan via email?")
            └─ EmailSender.send_report(subject, body, filename)
       └─ finally: master.after(0, reset_buttons)
```

## 4. Alur "Closing Colorplate"

[dashboard_controller.py:89](../controllers/dashboard_controller.py#L89)

```
DashboardView.on_close_colorplate()
  └─ Thread → run_send_colorplate()
       └─ DashboardController.close_colorplate(date_str)
            ├─ send_to_api(date_str)
            │    ├─ last_id = get_last_sync() or 0
            │    ├─ get_sales_header(last_id, date)  → vw_ordertransaction
            │    ├─ get_sales_detail(trx_ids, date)  → vw_orderdetail
            │    ├─ build_payload(headers, details)  → {"sales":[{...,"items":[...]}]}
            │    ├─ APIClient.enqueue_sales()        → INSERT queue.db
            │    └─ update_last_sync(max ReceiptID)
            └─ loop 30×, jeda 2 detik:
                 POST /sales/publish
                 berhenti kalau response.message mengandung "published"
```

Data **tidak** dikirim langsung dari GUI — GUI hanya menaruh di antrian, worker
yang mengirim. Karena itu `close_colorplate` melakukan polling: menunggu sampai
worker selesai mengirim dan server siap mem-publish.

## 5. Siklus hidup aplikasi

**Startup** ([main.py:12](../main.py#L12))
1. `recreate_db()` — hapus `queue.db` lama, buat baru **(antrian tersisa hilang)**
2. Hapus `worker.lock` yatim
3. Paksa locale ke `en_US.UTF-8` (fallback `English_United States`)
4. Import `settings` → baca `config.ini`, buat folder `reports/` & `logs/`
5. Bangun window (60% ukuran layar, minimum 900×700), menu bar, shortcut
6. Spawn worker

**Shutdown** ([main.py:330](../main.py#L330))
1. `worker_process.terminate()` + `wait(timeout=3)`
2. Konfirmasi kalau `dashboard.is_processing` masih `True`
3. `destroy()`

## 6. Threading

Semua operasi I/O panjang jalan di `threading.Thread(daemon=True)`. Aturan yang
harus dijaga:

- Widget hanya boleh disentuh dari main thread → pakai `self.master.after(0, fn)`.
- `DashboardView.log()` memanggil `self.update()` — dipanggil dari worker thread
  dan sejauh ini aman di praktik, tapi **jangan tambah pemanggilan Tk lain**
  dari dalam thread.
- `ask_yes_no()` (messagebox) dipanggil dari dalam thread di `process_closing()`.
  Ini secara teknis tidak thread-safe; jangan perbanyak pola ini.
- `is_processing` adalah satu-satunya kunci antar aksi. `on_close_colorplate()`
  mengecek flag ini tapi **tidak** menyetelnya, jadi masih mungkin men-trigger
  Generate bersamaan.

## 7. Keputusan desain

| Keputusan | Alasan |
|---|---|
| Antrian SQLite, bukan kirim langsung | Outlet sering koneksi buruk; data tidak hilang saat request gagal, worker retry sendiri |
| Worker proses terpisah, bukan thread | Kirim data tetap jalan walau UI hang / dialog modal terbuka |
| `queue.db` dibuat ulang tiap startup | Menghindari data basi & konflik skema; konsekuensinya `last_sync` reset |
| PyMySQL, bukan `mysql-connector-python` | Pure-Python, lebih ramah PyInstaller 32-bit |
| Date picker custom | Menghindari dependency `babel`/`tkcalendar` yang menyulitkan build |
| Report fixed-width `.txt` | Kompatibel dengan format lama yang sudah dipakai kantor pusat |
