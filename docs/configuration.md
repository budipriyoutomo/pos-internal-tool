# Configuration

Semua konfigurasi ada di satu file INI dan dibaca oleh singleton
`settings` ([config/settings.py](../config/settings.py)).

## Lokasi file

| Mode | Lokasi `config.ini` |
|---|---|
| Jalan dari source (`python main.py`) | `internal_tool/config.ini` |
| Jalan dari exe (frozen) | folder yang sama dengan `main.exe` |

Kalau file tidak ditemukan, `settings` **menulis file default baru** di lokasi
tersebut dan tetap lanjut jalan dengan nilai default (localhost / root / dsb).
Jadi "tidak error saat start" bukan jaminan config sudah benar — cek lewat menu
**Help → Check Config**.

`config.ini` di-gitignore dan tidak pernah boleh di-commit.

## Template lengkap

`config.ini.example` yang ada di repo **belum memuat section `[API]`**. Template
lengkap yang benar:

```ini
[DEFAULT]
SERVERNAME = 192.168.1.10        ; host MySQL POS
USERNAME   = root
PASSWORD   = ********
PORT       = 3306
DATABASE   = pos_db
OUTLET     = BIPVJ               ; kode outlet, dipakai di nama file & subjek email
CHARSET    = utf8

[MAIL]
SENDER     = outlet@gmail.com
PASSWORD   = ****************    ; Gmail App Password (16 karakter, BUKAN password akun)
RECEIVER   = finance@example.com
CC         = manager@example.com ; boleh dikosongkan
SMTPSERVER = smtp.gmail.com
SMTPPORT   = 465                 ; SSL

[APP]
AUTO_LOGIN    = False
LOG_LEVEL     = INFO
REPORT_FORMAT = txt

[API]
BASE_URL = http://<host>:<port>/api
TIMEOUT  = 30
API_KEY  = <bearer token>
```

## Referensi key

### `[DEFAULT]`

⚠️ INI `[DEFAULT]` bersifat khusus: **semua key di sini otomatis diwarisi oleh
section lain**. Jadi `PASSWORD` di `[DEFAULT]` akan terbaca sebagai fallback
`[API].PASSWORD` dan seterusnya. Jangan tambah key generik baru ke `[DEFAULT]` —
taruh di section sendiri.

| Key | Tipe | Dipakai di | Keterangan |
|---|---|---|---|
| `SERVERNAME` | str | `get_db_config()['host']` | Host/IP MySQL |
| `USERNAME` | str | `...['user']` | User MySQL |
| `PASSWORD` | str | `...['password']` | Plaintext |
| `PORT` | int | `...['port']` | Default 3306 |
| `DATABASE` | str | `...['database']` | Nama database POS |
| `OUTLET` | str | `settings.get_outlet()` | Nama file report, subjek email, label UI |
| `CHARSET` | str | — | **Tidak dibaca kode**; `get_db_config()` hardcode `utf8` |

### `[MAIL]`

| Key | Tipe | Keterangan |
|---|---|---|
| `SENDER` | str | Alamat pengirim, juga dipakai sebagai username SMTP |
| `PASSWORD` | str | Gmail App Password. Password akun biasa akan ditolak Gmail |
| `RECEIVER` | str | Penerima utama (satu alamat) |
| `CC` | str | Satu alamat CC; kosongkan kalau tidak perlu |
| `SMTPSERVER` | str | Default `smtp.gmail.com` |
| `SMTPPORT` | int | **Harus port SSL (465)** — kode memakai `smtplib.SMTP_SSL`, port 587/STARTTLS tidak akan jalan |

### `[APP]`

| Key | Status |
|---|---|
| `AUTO_LOGIN` | Belum diimplementasi |
| `LOG_LEVEL` | Belum diimplementasi (logging masih `print`) |
| `REPORT_FORMAT` | Belum diimplementasi (selalu `.txt`) |

Ketiganya hanya punya default di `settings.load_config()` dan tidak dibaca
di mana pun. Aman untuk dipakai kalau nanti fitur terkait dikerjakan.

### `[API]`

| Key | Tipe | Keterangan |
|---|---|---|
| `BASE_URL` | str | Tanpa trailing slash. Endpoint disusun jadi `{BASE_URL}/sync/sales` dan `{BASE_URL}/sales/publish` |
| `TIMEOUT` | int | Detik, dipakai `_send()`. `close_colorplate()` mengabaikannya dan hardcode 30 |
| `API_KEY` | str | Dikirim sebagai `Authorization: Bearer <API_KEY>` |

## API `settings`

```python
from config.settings import settings

settings.APP_NAME          # "Promise POS Internal Tool"
settings.APP_VERSION       # "1.0.0"
settings.BASE_DIR          # Path root app (frozen-aware)
settings.REPORTS_DIR       # BASE_DIR/reports  (dibuat otomatis)
settings.LOGS_DIR          # BASE_DIR/logs     (dibuat otomatis)
settings.config_path       # Path ke config.ini
settings.THEME_COLORS      # dict warna UI

settings.get_db_config()   # {host, user, password, port, database, charset}
settings.get_mail_config() # {sender, password, receiver, cc, smtp_server, smtp_port}
settings.get_api_config()  # {base_url, timeout, api_key}
settings.get_outlet()      # str kode outlet
```

Config dibaca **sekali** saat import. Mengubah `config.ini` saat aplikasi jalan
tidak berpengaruh sampai aplikasi di-restart.

## Palet warna UI

`settings.THEME_COLORS` — pakai ini, jangan hardcode hex baru.

| Key | Hex | Pemakaian |
|---|---|---|
| `primary` | `#4338ca` | Header bar, judul section |
| `secondary` | `#1e1b4b` | Status bar bawah |
| `accent` | `#4f46e5` | Tombol sekunder (Hari Ini, Kemarin, Colorplate) |
| `success` | `#059669` | Tombol aksi utama (Generate & Kirim) |
| `warning` | `#d97706` | — |
| `danger` | `#dc2626` | Tombol Batal (outline) |
| `light` | `#f3f4f6` | Background halaman |
| `white` | `#ffffff` | Background kartu |
| `text` | `#1f2937` | Teks utama |
| `border` | `#e5e7eb` | Garis kartu, warna tombol disabled |

Panel log memakai warna hardcode terpisah: background `#1e1e1e`, teks `#4af626`,
font Consolas 11.

## Catatan keamanan

Password DB dan App Password Gmail tersimpan **plaintext**. Konsekuensinya:

- Folder deploy di PC outlet harus dibatasi aksesnya.
- Pakai user MySQL **read-only** khusus untuk aplikasi ini — aplikasi hanya
  melakukan `SELECT`.
- Pakai Gmail App Password khusus per outlet supaya bisa dicabut satu-satu.
- Jangan pernah menempel isi `config.ini` ke issue, chat, atau dokumentasi.
