# Roadmap & Utang Teknis

Daftar hal yang layak dikerjakan untuk pengembangan berikutnya, diurutkan dari
yang paling murah/berdampak. Ini usulan — bukan keputusan yang sudah diambil.

---

## Prioritas 1 — Kebersihan dasar (cepat, risiko rendah)

| # | Item | Detail |
|---|---|---|
| 1.1 | Perbaiki `requirements.txt` | Tersimpan UTF-16; masih menyebut `mysql-connector-python`; `PyMySQL` tidak tercantum. Regenerasi UTF-8. Perhatikan `.gitignore` mengabaikan `*.txt` — tambahkan `!requirements.txt` |
| 1.2 | Hapus `core/database copy.py` | Dead code versi lama (mysql-connector) yang masih di-track git |
| 1.3 | Lengkapi `config.ini.example` | Tambahkan section `[API]` (`BASE_URL`, `TIMEOUT`, `API_KEY`) |
| 1.4 | Perbaiki dialog Check Config | [main.py:294](../main.py#L294): `"\\n".join(...)` → `"\n".join(...)` |
| 1.5 | Hapus kode mati di view | `on_send_api()` / `reset_api_button()` di `dashboard_view.py` tidak punya tombol pemanggil |
| 1.6 | Rapikan import tak terpakai | `from urllib import response` di `dashboard_view.py` dan `dashboard_controller.py`; `import requests` dobel di `api_client.py` |
| 1.7 | Perbaiki level log | `build_payload()` memakai `self.log_error()` untuk pesan informatif |
| 1.8 | Bundel assets di spec | `datas=[('assets/icons/app.ico', 'assets/icons')]` supaya icon ikut ke exe |
| 1.9 | Nasib `locale_fix.py` | Tidak diimport siapa pun — pakai atau hapus |

## Prioritas 2 — Keandalan

| # | Item | Detail |
|---|---|---|
| 2.1 | **Batas retry** | `process_queue()` mengulang selamanya. Tambahkan `MAX_RETRY` (mis. 10) → tandai `status='failed'` dan tampilkan di UI |
| 2.2 | **Antrian tidak hilang saat restart** | `recreate_db()` di startup menghapus item yang belum terkirim. Ganti ke `init_db()` + migrasi skema kalau perlu |
| 2.3 | Path `worker.lock` frozen-aware | `worker.py` memakai path relatif CWD, beda pola dengan file lain |
| 2.4 | Lock berbasis PID | Lock sekarang hanya cek keberadaan file. Validasi PID di dalamnya masih hidup atau tidak |
| 2.5 | Ganti deteksi `"published"` | Deteksi sukses berbasis substring rapuh. Minta backend menyediakan field status eksplisit |
| 2.6 | Hilangkan `except: pass` telanjang | Ada di `settings`, `main.py`, datepicker — menelan error diam-diam |
| 2.7 | Guard `is_processing` konsisten | `on_close_colorplate()` mengecek flag tapi tidak menyetelnya, sehingga aksi masih bisa tumpang tindih |

## Prioritas 3 — Observability

| # | Item | Detail |
|---|---|---|
| 3.1 | Ganti `print` dengan modul `logging` | Tulis ke `logs/app.log` dengan rotasi. Key `[APP] LOG_LEVEL` sudah tersedia tapi belum dipakai |
| 3.2 | Log terlihat di build exe | Sekarang `console=False`, jadi print hilang total di lapangan. File log menyelesaikan ini |
| 3.3 | Hentikan print payload penuh | [api_client.py:126](../core/api_client.py#L126) mencetak seluruh JSON tiap kirim |
| 3.4 | Riwayat pengiriman | `mark_sent()` menghapus baris, tidak ada jejak. Pindahkan ke tabel `queue_history` |
| 3.5 | Indikator status worker di UI | Saat ini pengguna tidak tahu worker hidup atau mati |

## Prioritas 4 — Keamanan

| # | Item | Detail |
|---|---|---|
| 4.1 | Kredensial plaintext | Password DB & Gmail App Password terbuka di `config.ini`. Opsi: DPAPI Windows, atau ambil dari environment variable |
| 4.2 | User MySQL read-only | Aplikasi hanya `SELECT`; jangan pakai `root` di outlet |
| 4.3 | HTTPS untuk API | `BASE_URL` saat ini HTTP polos — Bearer token melintas tanpa enkripsi |

## Prioritas 5 — Fitur

| # | Item | Detail |
|---|---|---|
| 5.1 | Rentang tanggal | Sekarang hanya satu tanggal per proses |
| 5.2 | Preview report di UI | Tampilkan isi `.txt` sebelum dikirim email |
| 5.3 | Riwayat closing | Daftar tanggal yang sudah diproses + statusnya |
| 5.4 | Implementasi `[APP] REPORT_FORMAT` | Key sudah ada, output masih selalu `.txt` |
| 5.5 | Multi-outlet dalam satu instalasi | Sekarang satu `config.ini` = satu outlet |
| 5.6 | Auto-closing terjadwal | Jalankan closing otomatis pada jam tertentu |
| 5.7 | Isi `models/` dan `utils/` | Folder sudah disiapkan tapi kosong; kandidat: dataclass untuk header/detail agar `build_payload()` tidak lagi manual |

## Prioritas 6 — Kualitas kode

| # | Item | Detail |
|---|---|---|
| 6.1 | Test untuk `build_payload()` | Fungsi paling kompleks & paling berisiko, murni transformasi data — mudah dites tanpa DB |
| 6.2 | Test untuk `ReportGenerator` | Bandingkan output dengan file referensi di `reports/` |
| 6.3 | `SELECT *` → daftar kolom eksplisit | Query saat ini rapuh terhadap perubahan skema |
| 6.4 | Type hints | Terutama di `core/` dan `controllers/` |

---

## Yang sebaiknya **tidak** diubah

- **Format report `.txt`** — lebar kolom fixed-width sudah dicocokkan dengan
  sistem penerima, termasuk ketidakkonsistenan antara blok Dine In dan Take Away.
  Lihat [report-format.md](report-format.md).
- **Arsitektur dua proses** — pemisahan GUI/worker memang disengaja agar
  pengiriman tetap jalan saat UI sibuk atau dialog modal terbuka.
- **`DictCursor`** — seluruh controller bergantung pada hasil query berupa dict.
- **Bahasa Indonesia di log & komentar** — konsisten dengan pengguna di outlet.
