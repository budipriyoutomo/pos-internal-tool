# Database

Ada dua database: **MySQL POS** (sumber data, read-only) dan **SQLite lokal**
(`queue.db`, antrian pengiriman).

---

## 1. MySQL POS

Koneksi: [core/database.py](../core/database.py), driver **PyMySQL**.

```python
pymysql.connect(
    host=..., user=..., password=..., database=..., port=...,
    charset="utf8",
    autocommit=True,
    cursorclass=pymysql.cursors.DictCursor,   # ← hasil query = list of dict
)
```

`DictCursor` itu penting: `DashboardController` mengakses hasil query dengan
`h["TransactionID"]`. Kalau cursor diganti ke tuple, `send_to_api()` sengaja
melempar `Exception("Database return tuple, harus dict")`.

`execute_query()` memanggil `connection.ping(reconnect=True)` sebelum eksekusi
supaya koneksi yang idle tidak putus.

### Objek yang dibaca

Aplikasi **hanya melakukan SELECT** ke 4 objek berikut:

| Objek | Jenis | Dipakai untuk |
|---|---|---|
| `bsum_trans` | tabel ringkasan | Report: total transaksi, diskon, service, pajak |
| `bsum_menu` | tabel ringkasan | Report: rincian per grup menu, dipisah `salemode` |
| `vw_ordertransaction` | view | Sync API: header transaksi |
| `vw_orderdetail` | view | Sync API: item per transaksi |

### Query

Semuanya ada di class `TransactionData`:

```sql
-- get_transactions(saledate)
SELECT * FROM bsum_trans WHERE saledate = %s;

-- get_dine_in(saledate)
SELECT * FROM bsum_menu WHERE saledate = %s AND salemode = 1;

-- get_takeaway(saledate)
SELECT * FROM bsum_menu WHERE saledate = %s AND salemode = 2;

-- get_sales_header(last_id, saledate)
SELECT * FROM vw_ordertransaction
WHERE ReceiptID > %s AND saledate = %s;

-- get_sales_detail(transaction_ids, date_str)
SELECT * FROM vw_orderdetail
WHERE TransactionID IN (%s, %s, ...)     -- jumlah placeholder = len(ids)
  AND CAST(SaleDate AS DATE) = %s;
```

`salemode`: **1 = Dine In**, **2 = Take Away**.

### Kolom yang dipakai

Query memakai `SELECT *`, tapi kode hanya membaca kolom-kolom di bawah. Kalau
struktur tabel berubah, ini yang harus tetap ada.

**`bsum_trans`** (dibaca `ReportGenerator`, **hanya baris terakhir**):
`AmountSummary`, `Disc`, `AmountTransaksi`, `AmountService`, `Tax`,
`OutletCode`, `OutletName`

**`bsum_menu`**: `Group`, `TotalQty`, `AmountMenu`

**`vw_ordertransaction`** (header):
`TransactionID`, `ReferenceNo`, `SaleDate`, `PaidTime`, `CloseTime`, `ShopID`,
`TransactionStatusID`, `SaleMode`, `NoCustomer`, `Deleted`, `ReceiptID`,
`ReceiptMonth`, `ReceiptYear`, `ReceiptProductRetailPrice`, `ReceiptSalePrice`,
`ReceiptPayPrice`, `ReceiptDiscount`, `ReceiptTotalAmount`,
`OtherPercentDiscount`, `OtherAmountDiscount`, `VATPercent`, `TransactionVAT`,
`TransactionExcludeVAT`, `TransactionVATable`, `ServiceChargePercent`,
`ServiceCharge`, `ServiceChargeVAT`, `OtherIncome`, `OtherIncomeVAT`,
`VoidStaffID`, `VoidReason`, `VoidTime`, `TransactionNote`, `QueueName`,
`IsSplitTransaction`, `IsFromOtherTransaction`

**`vw_orderdetail`** (item):
`OrderDetailID`, `TransactionID`, `SaleDate`, `ProductID`, `ProductName`,
`ProductGroupName`, `ProductDeptName`, `ProductSetType`, `OrderStatusID`,
`SaleMode`, `Amount` (=qty), `Price`, `RetailPrice`, `MinimumPrice`, `Comment`,
`OrderStaffID`, `OrderTableID`, `VoidStaffID`

Hanya `TransactionID`, `OrderDetailID`, `ProductID`, `Amount`, `Price` yang
diakses tanpa default — sisanya pakai `.get(..., default)` sehingga aman kalau
kolom hilang. `ReceiptID` di header juga wajib ada (dipakai hitung `last_sync`).

### Aturan saat menambah query

- Parameterized (`%s`) selalu. Satu-satunya f-string yang boleh adalah
  penyusunan placeholder `IN (...)` — nilainya tetap lewat params.
- Bungkus dengan `with DatabaseConnection() as db:` supaya koneksi ditutup.
- Aplikasi ini read-only. Jangan tambah `INSERT`/`UPDATE`/`DELETE` ke MySQL POS.

---

## 2. SQLite `queue.db`

Dikelola [queue_db.py](../queue_db.py). Lokasi: folder yang sama dengan
`main.py` (atau `main.exe` saat frozen).

### Skema

```sql
CREATE TABLE IF NOT EXISTS queue (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    payload     TEXT NOT NULL,      -- JSON: {"meta": {...}, "payload": {"sales":[...]}}
    status      TEXT DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    created_at  TEXT                -- ISO 8601
);

CREATE TABLE IF NOT EXISTS sync_state (
    key   TEXT PRIMARY KEY,         -- saat ini hanya 'last_sync'
    value TEXT
);
```

### Fungsi

| Fungsi | Aksi |
|---|---|
| `init_db()` | `CREATE TABLE IF NOT EXISTS` untuk kedua tabel |
| `recreate_db()` | **Hapus file `queue.db`** lalu `init_db()` |
| `insert_queue(payload)` | Insert satu row `status='pending'` |
| `get_pending(limit=10)` | `SELECT id, payload, retry_count ... WHERE status='pending' ORDER BY id ASC` |
| `mark_sent(id)` | **`DELETE FROM queue WHERE id=?`** — bukan update status |
| `increase_retry(id)` | `retry_count += 1` |
| `get_last_sync()` | Baca `sync_state.value` untuk key `last_sync` |
| `update_last_sync(v)` | Upsert `last_sync` |

Catatan penting:

- **`mark_sent()` menghapus baris**, jadi tabel `queue` hanya berisi item yang
  belum sukses terkirim. Tidak ada riwayat pengiriman.
- **Kolom `status` tidak pernah di-update** — nilainya selalu `'pending'`.
  Kalau nanti ingin status `sent`/`failed`, `mark_sent()` harus diubah.
- **Tidak ada batas `retry_count`.** Item yang selalu gagal akan dicoba terus
  selamanya (dengan backoff `1 + retry_count` detik), sampai app ditutup.
- **`recreate_db()` dipanggil setiap `main.py` start** — antrian yang belum
  terkirim hilang, dan `last_sync` reset ke 0. Konsekuensinya `get_sales_header()`
  memakai `ReceiptID > 0`, artinya seluruh transaksi tanggal terpilih dikirim
  ulang. Server diasumsikan idempotent.
- Setiap fungsi membuka & menutup koneksi sendiri (tidak ada connection pool).
  Ini disengaja karena file diakses dua proses.

### Inspeksi manual

```powershell
cd internal_tool
python -c "import sqlite3;c=sqlite3.connect('queue.db');print(c.execute('SELECT id,status,retry_count,created_at FROM queue').fetchall());print(c.execute('SELECT * FROM sync_state').fetchall())"
```
