# Promise POS Internal Tool

Aplikasi desktop untuk proses *closing* harian outlet restoran Maharasa:
generate laporan penjualan, kirim via email, dan sinkronisasi transaksi ke API
pusat (Colorplate).

Python 3.11 (32-bit) · Tkinter · MySQL (PyMySQL) · SQLite · PyInstaller · Windows

## Quick start

```powershell
# venv ada satu level di atas folder ini
..\venv\Scripts\Activate.ps1

Copy-Item config.ini.example config.ini    # lalu edit, dan tambahkan section [API]
python main.py
```

> `pip install -r requirements.txt` belum bisa diandalkan (file tersimpan UTF-16
> dan isinya belum sinkron). Install manual: `pip install PyMySQL requests pyinstaller`.
> Lihat [docs/development.md](docs/development.md).

## Fitur

- **Generate & Kirim** — baca ringkasan penjualan dari MySQL, tulis
  `reports/{OUTLET}_{tanggal}.txt`, kirim sebagai attachment email.
- **Closing Colorplate** — susun payload transaksi, masukkan ke antrian lokal,
  worker mengirimnya ke API, lalu polling sampai server mem-publish.
- Antrian SQLite + retry otomatis supaya data tidak hilang saat koneksi outlet
  bermasalah.

## Struktur

```
main.py                 entry GUI (spawn worker sebagai subprocess)
worker.py               entry worker (loop kirim antrian tiap 10 detik)
queue_db.py             SQLite antrian
config/                 settings singleton (config.ini, path, tema)
core/                   database, report_generator, email_sender, api_client
controllers/            logika bisnis
views/                  UI Tkinter
docs/                   dokumentasi lengkap
```

## Dokumentasi

| Dokumen | Isi |
|---|---|
| [docs/README.md](docs/README.md) | Indeks & alur kerja pengguna |
| [docs/architecture.md](docs/architecture.md) | Komponen, alur data, siklus hidup |
| [docs/configuration.md](docs/configuration.md) | Semua key `config.ini` |
| [docs/database.md](docs/database.md) | Tabel/view MySQL + skema SQLite |
| [docs/api-integration.md](docs/api-integration.md) | Endpoint, payload JSON, queue & retry |
| [docs/report-format.md](docs/report-format.md) | Layout file `.txt` |
| [docs/development.md](docs/development.md) | Setup, run, build, deploy |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Error umum & solusinya |
| [docs/roadmap.md](docs/roadmap.md) | Utang teknis & rencana |

Untuk AI coding agent: [AGENTS.md](AGENTS.md).

## Build

```powershell
pyinstaller main.spec --clean --noconfirm
pyinstaller worker.spec --clean --noconfirm
```

Deploy: salin `main.exe`, `worker.exe`, dan `config.ini` ke satu folder di PC
outlet. Detail di [docs/development.md](docs/development.md).

## Catatan

- `config.ini` berisi kredensial plaintext dan **tidak boleh di-commit**
  (sudah di-gitignore).
- `queue.db` dibuat ulang setiap aplikasi dibuka — jangan tutup aplikasi sebelum
  log menunjukkan pengiriman selesai.
