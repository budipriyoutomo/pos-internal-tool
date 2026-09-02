# Development

## 1. Prasyarat

| Item | Versi |
|---|---|
| Python | **3.11, 32-bit** (`Python311-32`) |
| OS | Windows 10+ |
| Akses | MySQL POS (read-only sudah cukup) + endpoint API |

Kenapa 32-bit: build exe yang beredar di outlet memakai interpreter 32-bit.
Kalau mem-build dengan Python 64-bit, hasilnya tidak akan jalan di PC outlet
yang masih 32-bit.

## 2. Setup

Virtualenv berada **satu level di atas** repo, di `POSClosing/v3/venv/`.

```powershell
cd D:\Project\maharasa\POSClosing\v3
.\venv\Scripts\Activate.ps1
cd internal_tool
```

Membuat venv baru dari nol:

```powershell
cd D:\Project\maharasa\POSClosing\v3
& "$env:LOCALAPPDATA\Programs\Python\Python311-32\python.exe" -m venv venv
.\venv\Scripts\Activate.ps1
pip install PyMySQL requests pyinstaller
```

⚠️ `pip install -r requirements.txt` **tidak bisa diandalkan sekarang**: file itu
tersimpan sebagai UTF-16, masih mencantumkan `mysql-connector-python` (tidak
dipakai lagi), dan tidak mencantumkan `PyMySQL` (yang justru dipakai). Paket
yang benar-benar dibutuhkan runtime hanya **PyMySQL** dan **requests**;
**pyinstaller** hanya untuk build. Tkinter dan sqlite3 bawaan Python.

Regenerasi file yang benar (sekali saja, lalu commit):

```powershell
pip freeze | Out-File -Encoding utf8 requirements.txt
```

## 3. Konfigurasi

```powershell
Copy-Item config.ini.example config.ini
notepad config.ini
```

Lalu tambahkan section `[API]` yang belum ada di template — lihat
[configuration.md](configuration.md) untuk template lengkap.

Verifikasi lewat aplikasi: menu **Help → Check Config**.

## 4. Menjalankan

```powershell
python main.py      # GUI; otomatis men-spawn worker sebagai subprocess
```

Debug worker sendiri (log-nya jadi kelihatan, tidak tertelan subprocess):

```powershell
python worker.py
```

Kalau ingin menjalankan worker manual, hapus dulu `worker.lock` bila ada —
kalau lock masih ada, worker langsung `sys.exit(0)`.

### Shortcut GUI

| Tombol | Aksi |
|---|---|
| `Ctrl+G` / `F5` | Generate Report |
| `F11` | Toggle fullscreen |
| `Esc` | Keluar fullscreen |
| `F1` | About |

Menu **Tools** membuka folder `reports/` dan `logs/` di Explorer.

## 5. Debugging

Semua log ke stdout (`print`) dan ke panel log di UI (`view.log()`). Karena spec
PyInstaller memakai `console=False`, **output print tidak terlihat pada build
exe** — untuk mendiagnosis masalah di lapangan, build sementara dengan
`console=True`.

Titik pemeriksaan yang berguna:

| Gejala | Cek |
|---|---|
| Payload salah | Console saat klik Closing Colorplate — `send_to_api()` mencetak trx IDs, jumlah header/detail, dan preview transaksi pertama |
| Transaksi hilang | Console mencetak `❌ TRANSACTION TIDAK PUNYA DETAIL` dan `❌ HILANG SAAT BUILD PAYLOAD` |
| Data tidak terkirim | Isi tabel `queue` (lihat [database.md](database.md#inspeksi-manual)) |
| Config salah | Help → Check Config |

Tidak ada test suite, linter, atau CI. Verifikasi dilakukan manual: jalankan
aplikasi, generate report untuk tanggal yang datanya sudah diketahui, bandingkan
hasilnya dengan file di `reports/`.

## 6. Build

Dua executable terpisah:

```powershell
pyinstaller main.spec --clean --noconfirm
pyinstaller worker.spec --clean --noconfirm
```

Hasil di `dist/`: `main.exe`, `worker.exe`.

Tanpa spec (sekali, untuk regenerasi spec):

```powershell
pyinstaller --clean --noconsole --onefile main.py
```

### Yang perlu diketahui tentang spec saat ini

- `datas=[]` — **`assets/` dan `config.ini` tidak ikut dibundel**. Icon aplikasi
  karena itu tidak muncul pada exe, dan `config.ini` harus disalin manual.
- `console=False` pada keduanya → tidak ada jendela konsol, tapi juga tidak ada
  output print.
- `upx=True` — kalau UPX tidak terpasang, PyInstaller melewatinya dengan warning.

Kalau ingin membundel assets, ubah `datas` di `main.spec`:

```python
datas=[('assets/icons/app.ico', 'assets/icons')],
```

## 7. Deploy ke PC outlet

Isi folder deploy:

```
POSClosing\
├── main.exe
├── worker.exe        ← wajib satu folder dengan main.exe
├── config.ini        ← disesuaikan per outlet (OUTLET, DB, email)
├── reports\          ← dibuat otomatis
└── logs\             ← dibuat otomatis
```

Langkah:

1. Salin `main.exe` + `worker.exe` ke folder tujuan.
2. Salin `config.ini`, sesuaikan `OUTLET`, kredensial DB, dan email outlet itu.
3. Jalankan `main.exe`, cek **Help → Check Config**.
4. Uji generate report untuk tanggal kemarin.
5. Uji Closing Colorplate dan pastikan log berakhir `✅ ... ditutup!`.

Catatan operasional:

- `queue.db` dibuat ulang setiap `main.exe` dibuka — **jangan tutup aplikasi
  sebelum log menunjukkan pengiriman selesai**, antrian yang tersisa akan hilang.
- `worker.lock` yatim otomatis dibersihkan saat startup, tidak perlu tindakan
  manual.
- Folder deploy berisi kredensial plaintext — batasi akses foldernya.

## 8. Alur git

```powershell
git status
git add <file>
git commit -m "pesan singkat"
git push origin main
```

Repo: `github.com/budipriyoutomo/pos-internal-tool`, branch `main`.

Yang **tidak boleh** di-commit (sudah ada di `.gitignore`, jangan di-force-add):
`config.ini`, `*.db`, `dist/`, `build/`, `reports/`, `logs/`, `venv/`.

Perhatikan `.gitignore` mengabaikan **semua `*.txt`** (termasuk
`requirements.txt`). Kalau memperbarui `requirements.txt`, tambahkan pengecualian
di `.gitignore` (`!requirements.txt`) atau pakai `git add -f`.

## 9. Menambah fitur baru — pola yang diikuti

Contoh: menambah tombol aksi baru di dashboard.

1. **Core** — kalau butuh query/HTTP baru, tambahkan method di `core/` yang
   sesuai (`TransactionData`, `APIClient`, dst).
2. **Controller** — tambahkan method di `DashboardController` yang memanggil
   core, menulis progres lewat `self.log_info/success/warning/error`, dan
   mengembalikan `True`/`False`.
3. **View** — tambahkan tombol via helper `create_button(...)` dengan warna dari
   `settings.THEME_COLORS`, handler `on_xxx()` yang mengecek `is_processing`
   lalu menjalankan `threading.Thread(target=self.run_xxx, daemon=True)`.
4. **Reset state** — di `finally`, panggil `self.master.after(0, self.reset_xxx)`.

Jangan panggil DB/HTTP dari view, dan jangan sentuh widget dari dalam thread.
