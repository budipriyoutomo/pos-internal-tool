# Dokumentasi — Promise POS Internal Tool v3

Aplikasi desktop untuk proses *closing* harian outlet restoran Maharasa:
generate laporan penjualan, kirim email, dan sinkronisasi data transaksi ke
API pusat (Colorplate).

| Item | Nilai |
|---|---|
| Bahasa | Python 3.11 (32-bit) |
| GUI | Tkinter (stdlib) |
| Database POS | MySQL / MariaDB via **PyMySQL** |
| Antrian lokal | SQLite (`queue.db`) |
| Packaging | PyInstaller (`main.exe` + `worker.exe`) |
| Platform | Windows 10+ |
| Repo | `github.com/budipriyoutomo/pos-internal-tool` |

## Daftar isi

1. **[Architecture](architecture.md)** — komponen, alur data, siklus hidup dua proses
2. **[Configuration](configuration.md)** — seluruh key `config.ini` dan artinya
3. **[Database](database.md)** — tabel/view MySQL yang dipakai + skema SQLite
4. **[API Integration](api-integration.md)** — endpoint, struktur payload, queue & retry
5. **[Report Format](report-format.md)** — spesifikasi layout file `.txt`
6. **[Development](development.md)** — setup, menjalankan, build exe, deploy
7. **[Troubleshooting](troubleshooting.md)** — error umum dan cara mengatasinya
8. **[Roadmap](roadmap.md)** — utang teknis & rencana pengembangan

Untuk AI coding agent: [`../AGENTS.md`](../AGENTS.md).

## Alur kerja pengguna (ringkas)

```
Buka aplikasi
   ↓
Pilih tanggal (default: hari ini · tombol "Hari Ini" / "Kemarin")
   ↓
┌─────────────────────────────┬──────────────────────────────────┐
│ 🚀 GENERATE & KIRIM         │ 🌐 CLOSING COLORPLATE            │
│                             │                                  │
│ 1. Query bsum_trans         │ 1. Query vw_ordertransaction     │
│    + bsum_menu              │    + vw_orderdetail              │
│ 2. Tulis reports/           │ 2. Build payload JSON            │
│    {OUTLET}_{tanggal}.txt   │ 3. Masuk queue.db                │
│ 3. Tanya: kirim email?      │ 4. Worker POST /sync/sales       │
│ 4. SMTP SSL + attachment    │ 5. Polling POST /sales/publish   │
│                             │    max 30× tiap 2 detik          │
└─────────────────────────────┴──────────────────────────────────┘
   ↓
Log tampil real-time di panel hitam bagian bawah
```
