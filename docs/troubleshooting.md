# Troubleshooting

## Database

### `Database connection failed: (2003, "Can't connect to MySQL server...")`

1. Cek `SERVERNAME` dan `PORT` di `config.ini` (Help → Check Config).
2. Uji koneksi dari mesin yang sama:
   ```powershell
   Test-NetConnection -ComputerName <SERVERNAME> -Port 3306
   ```
3. Pastikan MySQL menerima koneksi remote dan firewall Windows mengizinkannya.

### `Access denied for user ...`

Password salah, atau user tidak punya grant dari host tersebut. Aplikasi hanya
butuh `SELECT` — buat user read-only khusus.

### `Table 'pos_db.bsum_trans' doesn't exist`

`DATABASE` salah, atau database POS di outlet itu memakai skema berbeda.
Objek yang wajib ada: `bsum_trans`, `bsum_menu`, `vw_ordertransaction`,
`vw_orderdetail` — lihat [database.md](database.md).

### `Database return tuple, harus dict (fix execute_query)`

Cursor bukan `DictCursor`. Jangan ubah `cursorclass` di
[core/database.py](../core/database.py); seluruh controller bergantung pada dict.

### Report kosong (semua nilai 0) padahal ada transaksi

`bsum_trans` / `bsum_menu` tidak punya baris untuk tanggal itu. Tabel ini adalah
tabel **ringkasan** — biasanya diisi oleh proses closing di aplikasi POS. Kalau
closing POS belum dijalankan, ringkasannya memang belum ada.

Verifikasi langsung:
```sql
SELECT COUNT(*) FROM bsum_trans WHERE saledate = '2026-04-08';
SELECT COUNT(*) FROM bsum_menu  WHERE saledate = '2026-04-08';
```

Perhatikan juga `ReportGenerator` hanya membaca **baris terakhir** `bsum_trans`.

---

## Email

### `SMTPAuthenticationError`

Gmail menolak password akun biasa. Buat **App Password** 16 karakter di akun
Google (butuh 2FA aktif), lalu isikan ke `[MAIL] PASSWORD`.

### Email tidak terkirim, tidak ada error jelas

- `SMTPPORT` **harus 465**. Kode memakai `smtplib.SMTP_SSL`; port 587 (STARTTLS)
  tidak akan bekerja.
- Cek koneksi keluar port 465 tidak diblokir jaringan outlet.

### Attachment tidak ada

`process_closing()` hanya mengirim email kalau file report berhasil dibuat.
Cek dulu file-nya ada di `reports/` dan aplikasi punya izin baca ke folder itu.

---

## API / Sync

### `Sales belum siap dipublish` setelah 30 percobaan

Total tunggu ~60 detik. Penyebab paling umum: **worker belum selesai mengirim
antrian**, jadi server belum punya datanya.

Urutan pemeriksaan:

1. Worker jalan? Cek Task Manager untuk `worker.exe`, atau jalankan
   `python worker.py` di terminal terpisah untuk melihat log-nya.
2. Ada `worker.lock` yatim yang membuat worker langsung keluar? Hapus file itu
   lalu jalankan ulang.
3. Antrian masih terisi?
   ```powershell
   python -c "import sqlite3;print(sqlite3.connect('queue.db').execute('SELECT id,retry_count FROM queue').fetchall())"
   ```
   `retry_count` yang naik terus = pengiriman ditolak server.
4. Kalau data sebenarnya sudah masuk tapi tetap dianggap gagal: deteksi sukses
   memakai substring `"published"` pada field `message`. Kalau backend mengubah
   teks responsnya, kondisi ini tidak akan pernah terpenuhi — konfirmasi ke tim
   backend.

### Semua request API gagal / `401` / `403`

`API_KEY` salah atau kedaluwarsa. Header yang dikirim:
`Authorization: Bearer {API_KEY}`.

### `requests.exceptions.ConnectTimeout`

`BASE_URL` tidak terjangkau dari jaringan outlet, atau `TIMEOUT` terlalu pendek
untuk koneksi lambat. Naikkan `[API] TIMEOUT`. Catatan: `close_colorplate()`
memakai timeout hardcode 30 detik dan mengabaikan setelan ini.

### Item di antrian terus diulang selamanya

Tidak ada batas retry di kode saat ini. Untuk membersihkan antrian yang macet,
tutup aplikasi (startup berikutnya akan membuat ulang `queue.db`), atau hapus
row-nya manual.

### Transaksi tidak lengkap terkirim

Console mencetak dua penanda saat klik Closing Colorplate:

- `❌ TRANSACTION TIDAK PUNYA DETAIL` — header ada di `vw_ordertransaction` tapi
  tidak ada baris pasangannya di `vw_orderdetail`. Biasanya karena filter
  `CAST(SaleDate AS DATE) = date_str` pada detail: transaksi yang dibuka lewat
  tengah malam punya `SaleDate` detail berbeda dari headernya.
- `❌ HILANG SAAT BUILD PAYLOAD` — header hilang saat mapping, biasanya karena
  `TransactionID` `NULL`.

### Data terkirim dobel

Wajar dan diharapkan: `last_sync` reset ke 0 setiap aplikasi dibuka, jadi seluruh
transaksi tanggal terpilih dikirim ulang. Server harus idempotent terhadap
`transaction_id`. Kalau muncul duplikat di sisi server, itu masalah di backend,
bukan di aplikasi ini.

---

## Aplikasi

### Worker tidak jalan (`❌ Failed to start worker process`)

- Mode exe: pastikan `worker.exe` berada **satu folder** dengan `main.exe`.
- Mode source: pastikan `worker.py` ada di folder yang sama dengan `main.py`.

### `⚠️ Worker sudah berjalan, keluar...`

Ada `worker.lock`. Kalau tidak ada proses worker yang benar-benar jalan, file itu
sisa crash — hapus saja. `main.py` sebenarnya menghapusnya otomatis saat startup;
pesan ini muncul kalau worker dijalankan manual tanpa lewat GUI.

### UI membeku saat proses

Cek bahwa operasi baru dijalankan lewat `threading.Thread(daemon=True)` dan
update widget dilakukan lewat `self.master.after(0, ...)`. Operasi DB/HTTP yang
dipanggil langsung di handler tombol akan membekukan Tkinter.

### Dialog "Check Config" tampil satu baris panjang

Bug diketahui: [main.py:294](../main.py#L294) memakai `"\\n".join(info)` (escaped)
alih-alih `"\n".join(info)`.

### Icon aplikasi tidak muncul di exe

`main.spec` tidak membundel `assets/` (`datas=[]`). Lihat
[development.md](development.md#build).

### `UnicodeDecodeError` / karakter aneh di report

Locale dipaksa ke `en_US.UTF-8` di `main.py` dan `core/database.py`. Kalau mesin
menolak keduanya, `except: pass` membuatnya lolos diam-diam dan locale sistem
yang dipakai. Pastikan koneksi MySQL memakai `charset=utf8` (sudah hardcode) dan
kolom di DB memang UTF-8.

### `pip install -r requirements.txt` gagal / paket salah

File itu tersimpan UTF-16 dan isinya sudah tidak sinkron dengan kode. Install
manual: `pip install PyMySQL requests pyinstaller`. Lihat
[development.md](development.md#2-setup).

---

## Cara melaporkan bug

Sertakan:

1. Langkah persis + tanggal yang dipilih.
2. Output console lengkap (jalankan dari source agar print terlihat).
3. Isi tabel `queue` kalau masalahnya soal pengiriman.
4. Isi `config.ini` **dengan password/API key disensor**.
