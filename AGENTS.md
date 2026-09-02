# AGENTS.md — Promise POS Internal Tool (POS Closing v3)

Panduan untuk AI coding agent (Claude Code, Cursor, dll) yang bekerja di repo ini.
Dokumentasi lengkap untuk manusia ada di [`docs/`](docs/README.md).

---

## 1. Apa aplikasi ini

Aplikasi desktop **Tkinter** (Windows, Python 3.11 **32-bit**) untuk proses *closing*
harian outlet restoran Maharasa. Tiga fungsi utama:

1. **Generate report** — baca ringkasan penjualan dari MySQL POS (`bsum_trans`,
   `bsum_menu`), tulis file `.txt` fixed-width, kirim via email (SMTP SSL).
2. **Sync sales ke API** — ambil transaksi detail (`vw_ordertransaction`,
   `vw_orderdetail`), susun payload JSON, masukkan ke antrian SQLite lokal.
3. **Closing Colorplate** — trigger publish di server (RabbitMQ exchange) lalu
   polling sampai server menjawab "published".

Aplikasi berjalan sebagai **dua proses**: GUI (`main.py`) + background worker
(`worker.py`) yang dispawn otomatis oleh GUI sebagai subprocess.

---

## 2. Peta kode

```
internal_tool/
├── main.py                     # entry GUI: window, menubar, spawn worker, shutdown
├── worker.py                   # entry worker: loop 10 detik → APIClient.process_queue()
├── queue_db.py                 # SQLite antrian (queue.db): queue + sync_state
├── locale_fix.py               # helper locale (TIDAK diimport siapa-siapa saat ini)
├── config/settings.py          # singleton `settings`: config.ini + path + THEME_COLORS
├── core/
│   ├── database.py             # PyMySQL: DatabaseConnection + TransactionData (query)
│   ├── database copy.py        # ⚠️ DEAD CODE (versi lama pakai mysql-connector)
│   ├── report_generator.py     # tulis report .txt fixed-width
│   ├── email_sender.py         # SMTP_SSL + attachment
│   └── api_client.py           # enqueue, _send, close_colorplate, process_queue
├── controllers/dashboard_controller.py  # orkestrasi semua alur bisnis
├── views/
│   ├── dashboard_view.py       # UI utama + threading + logging ke Text widget
│   └── components/simple_datepicker.py  # date picker tanpa dependency babel
├── models/  utils/  resources/ # KOSONG (hanya __init__.py)
├── config.ini                  # 🔒 rahasia, gitignored
├── config.ini.example          # template (⚠️ belum ada section [API])
├── main.spec / worker.spec     # PyInstaller
└── docs/                       # dokumentasi lengkap
```

**Alur data:** `DashboardView` (thread) → `DashboardController` → `TransactionData`
(MySQL) → `build_payload()` → `APIClient.enqueue_sales()` → `queue.db` → *(proses
lain)* `worker.py` → `APIClient.process_queue()` → `POST /sync/sales`.

---

## 3. Aturan wajib saat mengubah kode

### Arsitektur
- **Pertahankan pemisahan MVC.** View tidak boleh query DB atau panggil `requests`
  langsung. Semua logika bisnis di `controllers/dashboard_controller.py`.
- **Semua akses config lewat `settings`** (`from config.settings import settings`).
  Jangan `configparser.read()` di tempat lain, jangan hardcode host/URL/kredensial.
- **Setiap operasi lama (DB/HTTP/SMTP) harus jalan di thread**, pola:
  `threading.Thread(target=..., daemon=True).start()`, dan update widget balik ke
  main thread lewat `self.master.after(0, ...)`. Tkinter tidak thread-safe.

### Path & packaging
- Kode harus jalan sebagai script **dan** sebagai `.exe` PyInstaller. Selalu pakai
  pola frozen-aware yang sudah ada:
  ```python
  base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) \
         else os.path.dirname(os.path.abspath(__file__))
  ```
  Jangan pakai path relatif polos (`open("queue.db")`) — CWD tidak dijamin.

### Database
- Query MySQL **wajib parameterized** (`%s`), jangan f-string. Satu-satunya
  interpolasi yang diizinkan adalah placeholder `IN (...)` di
  `TransactionData.get_sales_detail()`; jumlahnya dihitung dari `len()`, nilainya
  tetap lewat params.
- `execute_query()` mengembalikan **list of dict** (`DictCursor`). Controller
  bergantung penuh pada ini — jangan ganti ke tuple cursor.
- Driver aktif = **PyMySQL**. Jangan tambahkan `mysql.connector` lagi.

### Style
- Ikuti gaya sekitarnya: komentar & pesan log **Bahasa Indonesia**, emoji di
  awal pesan log (`📤 ✅ ⚠️ ❌ 🔒`), `print()` untuk console + `self.view.log()`
  untuk UI. Jangan konversi ke modul `logging` kecuali diminta eksplisit.
- Warna UI ambil dari `settings.THEME_COLORS`, jangan hardcode hex baru.

### Jangan
- ❌ Jangan commit `config.ini`, `queue.db`, `*.exe`, isi `reports/` atau `logs/`.
- ❌ Jangan menulis kredensial nyata (DB, app-password Gmail, API key) ke file
  apa pun yang di-track git, termasuk dokumentasi dan contoh kode.
- ❌ Jangan ubah format output `report_generator.py` tanpa diminta — lebar kolom
  fixed-width sudah dicocokkan dengan sistem penerima. Lihat
  [docs/report-format.md](docs/report-format.md).

---

## 4. Perintah yang sering dipakai

```powershell
# venv ada satu level di ATAS repo ini
..\venv\Scripts\Activate.ps1

python main.py          # jalankan GUI (otomatis spawn worker)
python worker.py        # jalankan worker sendiri (untuk debug queue)

pyinstaller main.spec --clean --noconfirm
pyinstaller worker.spec --clean --noconfirm
```

Tidak ada test suite, linter, atau CI di repo ini. Verifikasi = jalankan manual.
Detail lengkap: [docs/development.md](docs/development.md).

---

## 5. Perilaku yang mudah disalahpahami

Baca ini sebelum "memperbaiki" sesuatu yang terlihat seperti bug:

| Perilaku | Penjelasan |
|---|---|
| `main.py` memanggil `recreate_db()` saat startup | **Sengaja**: `queue.db` dihapus & dibuat ulang setiap app dibuka. Efek samping: `last_sync` selalu reset ke 0, jadi sync mengirim ulang seluruh transaksi tanggal itu (server diasumsikan idempotent). Antrian yang belum terkirim saat app ditutup **hilang**. |
| `worker.lock` | Anti double-worker. `main.py` menghapus lock yatim saat startup. Path-nya relatif ke CWD (lihat Known Issues). |
| `close_colorplate()` polling 30× × 2 detik | Server butuh waktu memproses queue sebelum siap publish. Sukses dideteksi dari substring `"published"` di `message` respons. |
| `update_last_sync()` di `process_queue()` dikomentari | Sengaja dinonaktifkan; last_sync di-update dari sisi controller setelah enqueue, bukan setelah kirim. |
| `enqueue_sales` membungkus payload jadi `{meta, payload}` | Worker meng-unwrap lagi (`payload_wrapper.get("payload", ...)`) dan yang dikirim ke API hanya isi `payload` (`{"sales": [...]}`). Wrapper `meta` **tidak** ikut terkirim. |

---

## 6. Known issues (utang teknis yang sudah diketahui)

Jangan anggap ini temuan baru; perbaiki hanya kalau memang jadi scope tugas.

1. `requirements.txt` disimpan **UTF-16** (tidak bisa dibaca `pip install -r`
   di sebagian environment) dan masih menyebut `mysql-connector-python` padahal
   kode pakai **PyMySQL**; `PyMySQL` sendiri tidak tercantum.
2. `core/database copy.py` = dead code, masih di-track git.
3. `config.ini.example` belum punya section `[API]` (`BASE_URL`, `TIMEOUT`,
   `API_KEY`) padahal `settings` dan `APIClient` membutuhkannya.
4. `main.spec` / `worker.spec` tidak membundel `assets/` maupun `config.ini`
   (`datas=[]`), sehingga icon tidak ikut ke dalam exe.
5. `worker.py` memakai `LOCK_FILE = "worker.lock"` (relatif CWD), bukan pola
   frozen-aware seperti file lain.
6. `main.py:294` menulis `"\\n".join(info)` (escaped) di dialog *Check Config*,
   sehingga dialog tampil satu baris panjang.
7. `views/dashboard_view.py` masih punya `on_send_api()` / `reset_api_button()`
   tanpa tombol pemanggil (fitur "Send to API" digabung ke Closing Colorplate).
8. `dashboard_controller.build_payload()` memakai `self.log_error()` untuk pesan
   informatif ("🔹 Membangun payload") — salah level log.
9. Banyak `except: pass` telanjang di `settings`, `main.py`, dan datepicker yang
   menelan error diam-diam.
10. Password DB & app-password Gmail tersimpan plaintext di `config.ini`.

---

## 7. Referensi dokumentasi

| Dokumen | Isi |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Diagram proses, alur data, siklus hidup |
| [docs/configuration.md](docs/configuration.md) | Semua key `config.ini` + arti |
| [docs/database.md](docs/database.md) | Tabel/view MySQL & skema SQLite |
| [docs/api-integration.md](docs/api-integration.md) | Endpoint, payload JSON, queue & retry |
| [docs/report-format.md](docs/report-format.md) | Layout report `.txt` per kolom |
| [docs/development.md](docs/development.md) | Setup, run, build, deploy |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Error umum & solusinya |
