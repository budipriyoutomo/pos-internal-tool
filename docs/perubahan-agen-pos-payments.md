# Perubahan agen POS untuk `payments`

Untuk: pengembang agen POS (`POSClosing/v3/internal_tool`) dan sync-api
Tanggal: 17 November 2026 (revisi 2)

Kontrak kirim rekap closing revisi 3 meminta `payments` di setiap elemen
`sales`. Sekarang kita mengirim `payments: []`, karena data pembayaran tidak
pernah ditarik dari POS. Dokumen ini menjelaskan apa yang harus berubah supaya
data itu tersedia.

> **Revisi 2.** Agen dipakai di dua sistem POS dengan skema tabel berbeda
> (Promise dan Vtec), dan Promise **tidak punya** tabel `orderpaydetail`.
> Karena itu sumber data pembayaran diambil lewat view baru
> `vw_orderpaydetail` yang dibuat per sistem (bagian 4), bukan langsung dari
> tabel.

---

## 1. Yang dikirim ke ERP

Satu baris per metode bayar, di dalam elemen `sales` (satu tujuan kunjungan):

```json
{
  "paymentMethod": "Cash",
  "paymentAmount": 224250,
  "fullPaymentAmount": 224250,
  "notes": ""
}
```

`coaNo` dan `merchantDiscountRate` **tidak kami kirim**. Asumsinya, keduanya
diatur di ERP Gateway berdasarkan `paymentMethod` (belum dikonfirmasi, lihat
pertanyaan #6 dan #7). Dari POS hanya dikirim detail transaksi, termasuk
pembayarannya.

Pembagian tugasnya begini:

| Data | Sumber | Dikerjakan di |
|---|---|---|
| Baris pembayaran per transaksi (jenis bayar + nominal) | MySQL POS lewat view `vw_orderpaydetail` (bagian 4) | **Agen POS** |
| Nama jenis bayar (`paymentMethod`) | Master jenis bayar di POS, ikut di view yang sama | **Agen POS** |
| Penjumlahan per tujuan kunjungan + metode, di dalam satu sistem POS | Data yang sudah tersimpan | **sync-api** |
| Akun (COA) dan MDR per metode, per sistem POS | Pengaturan di ERP | **ERP Gateway** |

Agen hanya mengirim data mentah pembayaran.

> **Aturan: jenis bayar tidak pernah digabung antar sistem POS.** Promise
> dan Vtec adalah software yang berbeda, jadi jenis bayarnya dipisah per
> brand / per sistem POS, **walaupun namanya sama** (mis. "Cash" atau
> "QRIS BNI" di keduanya). Aturan ini berlaku di semua tahap: view, payload,
> tabel di sync-api, penjumlahan, dan pemetaan akun di ERP Gateway. Sistem
> POS selalu menjadi bagian dari kunci jenis bayar:
> (sistem POS, `PayTypeID`) atau (sistem POS, nama), tidak pernah nama
> saja.

---

## 2. Dua sistem POS

Agen membaca MySQL POS hanya lewat view `vw_*`. View inilah yang menyamakan
**nama kolom** antar sistem, sehingga kode agen cukup satu. Yang disamakan
hanya bentuk datanya. **Isinya**, termasuk daftar jenis bayar, tetap milik
masing-masing sistem dan tidak digabung (aturan di bagian 1). Definisi view yang
terpasang sekarang disimpan di `POSClosing/v3/queryPOS/`:

| | Promise | Vtec |
|---|---|---|
| Database (contoh) | `promise6` | `tomsushi` |
| Definisi view | `queryPOS/promise/` | `queryPOS/vtec/` |
| Tabel header / detail | `ordertransaction` / `orderdetail` | `ordertransaction` / `orderdetail` |
| Tabel pembayaran | **`paydetail`** (tidak ada `orderpaydetail`) | `orderpaydetail` |
| Master jenis bayar | `paytype` (ada juga `paytypegroup`) | `paytype` |
| Tabel pembayaran lain yang perlu dicek | `paybyvoucher`, `creditcardtype` | voucher tercatat di `orderpaydetail` (`Voucher*`) |
| Hasil `SHOW COLUMNS` | `queryPOS/promise/paydetail.csv`, `paytype.csv` | `queryPOS/vtec/orderpaydetail.csv`, `paytype.csv` |

Struktur kolom pembayaran (dari hasil `SHOW COLUMNS`):

| Keperluan | Promise | Vtec |
|---|---|---|
| Kunci baris (PK) | `paydetail` (`PayDetailID`, `TransactionID`, `ComputerID`) | `orderpaydetail` (`PayDetailID`, `TransactionID`, `ComputerID`) |
| Jenis bayar | `PayTypeID` | `PayTypeID` (ada juga `OrgPayTypeID`) |
| Nominal | `Amount` | `PayAmount` |
| Uang diserahkan / kembalian | tidak ada kolomnya | `Paid` (decimal), `CashChange` |
| Tanggal | tidak ada, ambil dari `ordertransaction` | `SaleDate` (datetime) |
| EDC | `IsFromEDC` | `IsFromEDC` |
| Nomor kartu (**jangan dikirim**) | `CreditCardNo`, `CardHolderName` | `CreditCardNo`, `CardNo`, `CreditCardHolderName` |
| Kunci master | `paytype.TypeID` (**bukan** `PayTypeID`) | `paytype.PayTypeID` |
| Nama jenis bayar | `paytype.PayType`, `paytype.DisplayName` | `paytype.PayTypeName`, `paytype.DisplayName` |
| Kode jenis bayar | `paytype.PayTypeCode` | `paytype.PayTypeCode` |
| Penanda di master | `IsSale`, `IsOtherReceipt`, `Deleted` | `IsSale`, `IsOtherReceipt`, `Deleted` |
| Kolom MDR di master | tidak ada (`PrepaidDiscountPercent` adalah diskon prepaid) | tidak ada |

`PayDetailID` hanya unik bersama `TransactionID` + `ComputerID`, jadi
ketiganya dipakai sebagai kunci baris di sync-api.

Contoh perbedaan kolom yang sudah disamakan di `vw_orderdetail`: Promise
`Amount`/`Price`, Vtec `TotalQty AS Amount`/`PricePerUnit AS Price`. Pola
yang sama dipakai untuk pembayaran.

Hal yang perlu diketahui dari view yang ada:

- `vw_ordertransaction` **tidak memfilter dan tidak menampilkan**
  `ComputerID`. Filternya hanya `ReceiptID > 0`.
- `vw_orderdetail` join ke `ordertransaction` dengan `TransactionID` **dan**
  `ComputerID`, dan memfilter `ReceiptID > 0 AND a.Deleted = 0 AND o.Deleted = 0`.
  Jadi transaksi `Deleted = 1` ikut di header, tetapi tanpa item.
- `SaleDate` di Vtec memakai `CAST(SaleDate AS DATE)`, di Promise apa adanya.
- `ReceiptPayPrice` ada di kedua sistem, jadi bisa dipakai untuk pengecekan
  Σ pembayaran.

---

## 3. Langkah 0: cek isi data di POS

Struktur kolom sudah diketahui (bagian 2). Yang belum diketahui adalah
**arti isinya**. Jalankan query di bawah di **satu outlet Promise dan satu
outlet Vtec**. Semuanya hanya membaca. Ganti tanggal dengan hari yang ramai.

Catatan: query lama Vtec (`POSClosing/vtecQuery.sql`, `vtecQuery2.sql`)
memakai `TranKey` untuk join. `TranKey` hanya ada di Vtec, jadi view memakai
`TransactionID` + `ComputerID` yang ada di kedua sistem dan memang menjadi PK.

### 3.1 Nominal: apakah sudah bersih dari kembalian?

**Promise**: `paydetail` tidak punya kolom kembalian. Cek apakah `Amount`
sudah bersih.

```sql
SELECT a.TransactionID, a.ComputerID, a.ReceiptPayPrice,
       SUM(p.Amount) AS total_amount, COUNT(*) AS baris
FROM ordertransaction a
JOIN paydetail p
  ON p.TransactionID = a.TransactionID AND p.ComputerID = a.ComputerID
WHERE a.SaleDate = '2026-11-10' AND a.ReceiptID > 0 AND a.Deleted = 0
GROUP BY a.TransactionID, a.ComputerID, a.ReceiptPayPrice
HAVING ABS(a.ReceiptPayPrice - total_amount) > 0.5;
```

**Vtec**: ada `PayAmount`, `Paid` dan `CashChange`. Dugaan: `PayAmount` =
nominal bersih, `Paid` = uang diserahkan, `CashChange` = `Paid − PayAmount`.

```sql
-- Contoh baris tunai yang ada kembaliannya
SELECT TransactionID, ComputerID, PayTypeID, PayAmount, Paid, CashChange
FROM orderpaydetail
WHERE CAST(SaleDate AS DATE) = '2026-11-10' AND CashChange <> 0
LIMIT 20;

-- Σ PayAmount vs ReceiptPayPrice
SELECT a.TransactionID, a.ComputerID, a.ReceiptPayPrice,
       SUM(p.PayAmount) AS total_payamount, SUM(p.CashChange) AS total_kembalian
FROM ordertransaction a
JOIN orderpaydetail p
  ON p.TransactionID = a.TransactionID AND p.ComputerID = a.ComputerID
WHERE CAST(a.SaleDate AS DATE) = '2026-11-10' AND a.ReceiptID > 0 AND a.Deleted = 0
GROUP BY a.TransactionID, a.ComputerID, a.ReceiptPayPrice
HAVING ABS(a.ReceiptPayPrice - total_payamount) > 0.5;
```

Kalau query Σ tidak menghasilkan baris, nominalnya sudah cocok dengan
`ReceiptPayPrice`. Kalau ada selisih, catat pola selisihnya (kembalian,
pembulatan, voucher) sebelum view dipakai.

### 3.2 Apakah semua jenis bayar ada di master?

```sql
-- Promise
SELECT DISTINCT p.PayTypeID
FROM paydetail p LEFT JOIN paytype t ON t.TypeID = p.PayTypeID
WHERE t.TypeID IS NULL;

-- Vtec
SELECT DISTINCT p.PayTypeID
FROM orderpaydetail p LEFT JOIN paytype t ON t.PayTypeID = p.PayTypeID
WHERE t.PayTypeID IS NULL;
```

View memakai `LEFT JOIN` supaya pembayaran tidak hilang, tetapi hasil query
ini perlu diketahui.

### 3.3 Daftar jenis bayar yang terpakai

Dipakai untuk pertanyaan #2 dan #3 (keseragaman nama antar outlet **dalam
satu sistem**, dan pengecualian 10008/10051/10152). Hasil Promise dan Vtec
disimpan dan diserahkan ke ERP Gateway sebagai **dua daftar terpisah**, tidak
dicocokkan satu sama lain.

```sql
-- Promise
SELECT t.TypeID, t.PayTypeCode, t.PayType, t.DisplayName, t.IsSale,
       t.IsOtherReceipt, t.Deleted, COUNT(*) AS baris, SUM(p.Amount) AS total
FROM paydetail p LEFT JOIN paytype t ON t.TypeID = p.PayTypeID
GROUP BY t.TypeID, t.PayTypeCode, t.PayType, t.DisplayName, t.IsSale,
         t.IsOtherReceipt, t.Deleted;

-- Vtec
SELECT t.PayTypeID, t.PayTypeCode, t.PayTypeName, t.DisplayName, t.IsSale,
       t.IsOtherReceipt, t.Deleted, COUNT(*) AS baris, SUM(p.PayAmount) AS total
FROM orderpaydetail p LEFT JOIN paytype t ON t.PayTypeID = p.PayTypeID
GROUP BY t.PayTypeID, t.PayTypeCode, t.PayTypeName, t.DisplayName, t.IsSale,
         t.IsOtherReceipt, t.Deleted;
```

### 3.4 Lainnya

```sql
-- Kedua sistem: apakah TransactionID unik tanpa ComputerID?
SELECT TransactionID, COUNT(DISTINCT ComputerID) n
FROM ordertransaction
GROUP BY TransactionID HAVING n > 1
LIMIT 20;

-- Promise: apakah voucher juga tercatat di paydetail?
SHOW COLUMNS FROM paybyvoucher;
SELECT * FROM paybyvoucher LIMIT 20;

-- Promise: arti kolom Paid (tinyint) di paydetail
SELECT Paid, COUNT(*) FROM paydetail GROUP BY Paid;

-- Vtec: kapan OrgPayTypeID berbeda dari PayTypeID?
SELECT PayTypeID, OrgPayTypeID, COUNT(*)
FROM orderpaydetail WHERE OrgPayTypeID <> 0 AND OrgPayTypeID <> PayTypeID
GROUP BY PayTypeID, OrgPayTypeID;
```

Yang ditetapkan dari langkah 0:

1. **Nominal bersih** per sistem (3.1).
2. **Jenis bayar tanpa master** (3.2).
3. **Daftar jenis bayar** untuk dikirim ke ERP Gateway (3.3).
4. **Keunikan `TransactionID`.** Kalau ada `TransactionID` yang sama di
   beberapa `ComputerID`, agen yang sekarang mengelompokkan detail hanya per
   `TransactionID` sudah berisiko mencampur data. Ini berlaku juga untuk
   detail, bukan hanya pembayaran.
5. **Voucher Promise.** Kalau voucher hanya ada di `paybyvoucher` (tidak di
   `paydetail`), view Promise harus menggabungkan keduanya.
6. **Arti `Paid` di Promise** dan **`OrgPayTypeID` di Vtec.** Kalau `Paid = 0`
   artinya belum dibayar, view Promise harus memfilternya.

### 3.5 Hasil: Promise (17 November 2026)

Dijalankan dari agen, hanya membaca, ke dua server Promise (`promise6`):

- **Server A**: `ComputerID` 1583, 1585, 1586. Koneksinya putus-sambung, jadi
  hanya uji awal yang jalan.
- **Server B**: `ComputerID` 790, 793, 838. Uji lengkap 30 hari
  (19 Oktober–17 November 2026, 3.342 transaksi).

| Cek | Hasil | Arti |
|---|---|---|
| Draf view (SELECT-nya) | Jalan, kolom keluaran sesuai 4.1 | Join `paydetail.PayTypeID = paytype.TypeID` benar |
| Σ `Amount` vs `ReceiptPayPrice` (B, 30 hari) | **Cocok di 30 dari 30 hari**, 0 transaksi selisih | `Amount` adalah **nominal bersih**, tanpa kembalian. View Promise sudah memakai kolom yang benar. |
| Transaksi tanpa pembayaran (B, 30 hari) | 0 | – |
| Transaksi multi-pembayaran (B, 30 hari) | 3.118 trx 1 baris, 24 trx 2 baris, 1 trx 4 baris | `payments` memang bisa berisi lebih dari satu baris per transaksi |
| Pembayaran nominal ≤ 0 (B, 30 hari) | 4 baris "Voucher Adjustment" (`TypeID` 168), total −4 | Lihat catatan `Vadj` di bawah |
| Jenis bayar tanpa master (A) | 0 (seluruh tabel) | `LEFT JOIN` tetap dipakai untuk jaga-jaga |
| `paydetail.Paid` (A) | Selalu 0 (98.322 baris) | Bukan penanda lunas. **Tidak perlu filter `Paid`.** |
| `TransactionID` di >1 `ComputerID` | Ada. B: 11.930 `TransactionID` (108366–120335) dipakai lebih dari satu komputer. **Tidak ada** yang bentrok di tanggal yang sama (B, 30 hari). | Agen aman, karena selalu memfilter per tanggal. Risikonya ada di kunci penyimpanan sync-api (bagian 8 #5). |
| Voucher `paybyvoucher` (B, 30 hari) | 21 transaksi, `UsedAmount` total 3.175.000, semuanya `IsSale = 0`. Σ `paydetail` tetap = `ReceiptPayPrice`, dan nominal voucher **tidak** ada di `paydetail`. | Voucher ini potongan (diskon), bukan pembayaran, dan sudah mengurangi `ReceiptPayPrice`. **View tidak perlu menggabungkan `paybyvoucher`.** |
| Jenis bayar 30 hari (A) | 24 jenis, mis. QRIS BCA, Credit Card, BCA DEBIT, Cash, GOBIZ, GRABFOOD | Lihat catatan di bawah |

Catatan dari daftar jenis bayar Promise:

- **QRIS BNI di Promise = `TypeID` 864**, bukan 10152. ID yang dikecualikan
  query lama (10008/10051/10152) adalah ID Vtec. Ini contoh kenapa jenis
  bayar tidak boleh digabung antar sistem: "QRIS BNI" Promise dan "QRIS BNI"
  Vtec adalah dua jenis bayar yang berbeda. Aturan pengecualian, kalau memang
  dipakai, ditetapkan **terpisah per sistem** (pertanyaan #3).
- **`IsOtherReceipt = 1`** terpasang di BCA DEBIT, Niaga Master, dan Visa
  BNI, yang jelas pembayaran penjualan. Jangan memakai flag ini untuk
  membuang pembayaran. Flag ini tetap dikirim sebagai informasi saja.
- **"Voucher Adjustment" (`Vadj`, `TypeID` 168) bernilai −1** per baris.
  Penyesuaian kecil atau pembulatan tercatat sebagai baris pembayaran
  negatif, dan ikut dalam Σ = `ReceiptPayPrice`. Jangan dibuang di view.
  sync-api dan ERP perlu tahu cara memperlakukannya (pertanyaan #8).
- **`PayTypeCode` tidak seragam** (`cc`, `1`, `JKT0066`, `STBDG082`,
  `STBALI0017`). Prefiks lokasinya menandakan kode dibuat per outlet, jadi
  kode ini **tidak** cocok dijadikan kunci pemetaan di ERP. Nama
  (`PayTypeName`) lebih stabil, tetapi tetap perlu dibandingkan antar outlet
  **Promise** (pertanyaan #2).

Langkah 0 untuk **Promise selesai**. Yang belum: seluruh pengecekan **Vtec**
(3.1–3.4), terutama arti `PayAmount`, `Paid` dan `CashChange`.

---

## 4. View baru `vw_orderpaydetail` (dibuat di MySQL POS)

Wajib. Dibuat di setiap outlet, oleh orang yang dulu membuat view `vw_*`,
dengan definisi berbeda per sistem tetapi **nama kolom keluaran yang sama**.
Nama kolom yang sama hanya supaya kode agen cukup satu. `PayTypeID` dan
`PayTypeName` tetap berasal dari master sistem masing-masing dan tidak
dipetakan ke daftar bersama.

Draf definisinya ada di:

- `queryPOS/promise/vw_orderpaydetail.sql`
- `queryPOS/vtec/vw_orderpaydetail.sql`

Nama database di `DROP VIEW` (`promise6`, `tomsushi`) mengikuti file view yang
sudah ada. Sesuaikan per outlet.

### 4.1 Kolom keluaran (kontrak untuk agen)

| Kolom | Promise | Vtec |
|---|---|---|
| `PayDetailID` | `p.PayDetailID` | `p.PayDetailID` |
| `TransactionID` | `p.TransactionID` | `p.TransactionID` |
| `ComputerID` | `p.ComputerID` | `p.ComputerID` |
| `SaleDate` | `a.SaleDate` | `CAST(a.SaleDate AS DATE)` |
| `PayTypeID` | `p.PayTypeID` | `p.PayTypeID` |
| `PayTypeCode` | `t.PayTypeCode` | `t.PayTypeCode` |
| `PayTypeName` | `t.PayType` | `t.PayTypeName` |
| `PayTypeDisplayName` | `t.DisplayName` | `t.DisplayName` |
| `PayAmount` | `p.Amount` | `p.PayAmount` |
| `CashChange` | `0` (tidak ada kolomnya) | `p.CashChange` |
| `IsFromEDC` | `p.IsFromEDC` | `p.IsFromEDC` |
| `IsSale` | `t.IsSale` | `t.IsSale` |
| `IsOtherReceipt` | `t.IsOtherReceipt` | `t.IsOtherReceipt` |

`SaleDate` diambil dari `ordertransaction` di kedua sistem, walaupun Vtec
punya `orderpaydetail.SaleDate` sendiri, supaya filter tanggalnya sama persis
dengan header dan detail.

Nomor kartu, nama pemegang kartu, nomor cek, dan kode approval **tidak**
dimasukkan ke view.

### 4.2 Filter

Ikuti `vw_orderdetail`: join ke `ordertransaction a` dengan `TransactionID`
dan `ComputerID`, lalu `WHERE a.ReceiptID > 0 AND a.Deleted = 0`. Tabel
pembayaran di kedua sistem tidak punya kolom `Deleted`.

- Master jenis bayar di-join dengan **`LEFT JOIN`** supaya pembayaran dengan
  jenis bayar yang tidak ada di master tidak hilang. `PayTypeName` akan NULL,
  dan agen memberi peringatan.
- **Jangan** filter `paytype.Deleted`. Jenis bayar yang sudah dihapus dari
  master tetap dipakai oleh transaksi lama.
- **Jangan** buang `PayTypeID` 10008/10051/10152 di view, walaupun query lama
  Vtec membuangnya (pertanyaan #3). Agen mengirim semua pembayaran beserta
  `IsSale`/`IsOtherReceipt`, dan keputusan filter diambil di sync-api atau ERP.
- **Tidak ada** filter `Paid` di Promise: nilainya selalu 0 (lihat 3.5).
- **Jangan** filter berdasarkan `IsOtherReceipt`. Flag ini terpasang juga di
  pembayaran penjualan biasa (lihat 3.5).

---

## 5. Perubahan di agen POS

> **Status (17 November 2026): 5.1–5.4 dan dokumentasi agen di 5.5 sudah
> dikerjakan** (`core/database.py`, `controllers/dashboard_controller.py`,
> `core/api_client.py`). Sudah diuji offline dengan data tiruan, dan diuji
> read-only ke MySQL Promise (server B, 16 November 2026: 65 transaksi,
> 539 item). Karena view belum dibuat, `payments` tidak dikirim, sesuai
> harapan. Alur dengan view terpasang dan uji di Vtec belum dilakukan.
> Build exe dan rilis ke outlet juga belum.

Semua perubahan mengikuti aturan `AGENTS.md` agen: query parameterized,
hasilnya list of dict, dan agen tetap hanya membaca MySQL.

### 5.1 Query baru: `core/database.py`

Tambahkan `TransactionData.get_sales_payment(transaction_ids, date_str)`
yang membaca `vw_orderpaydetail`. Bentuknya sama dengan `get_sales_detail`:
placeholder `IN (...)` dihitung dari `len()`, nilainya lewat params, dan
tanggal difilter dengan `CAST(SaleDate AS DATE) = %s`. Pengecualian
placeholder di `AGENTS.md` perlu diperluas untuk fungsi ini.

### 5.2 Ambil pembayaran: `controllers/dashboard_controller.py` → `send_to_api()`

Setelah `get_sales_detail(...)`, panggil `get_sales_payment(...)` dengan
`trx_ids` dan tanggal yang sama, lalu teruskan hasilnya ke
`build_payload(headers, details, payments)`.

**Outlet yang belum punya view.** Selama `vw_orderpaydetail` belum dibuat di
suatu outlet, query ini gagal (MySQL error 1146, tabel tidak ada). Kegagalan
itu **tidak boleh** menggagalkan pengiriman. Tangkap error itu, beri
peringatan, lalu kirim payload **tanpa key `payments`** (bukan `[]`), supaya
sync-api mencatatnya sebagai *tidak diketahui* (bagian 6 poin 3).

### 5.3 Susun payload: `build_payload()`

- Buat `payment_map` dengan cara yang sama seperti `detail_map`.
- Tambahkan ke setiap elemen `sales`:

  ```python
  "payments": payment_map.get(trx_id, []),
  ```

  dengan isi tiap baris:

  ```python
  {
      "pay_detail_id": _to_int(p.get("PayDetailID")),
      "computer_id": _to_int(p.get("ComputerID")),
      "pay_type_id": _to_int(p.get("PayTypeID")),
      "pay_type_code": _text(p.get("PayTypeCode")),
      "pay_type_name": _text(p.get("PayTypeName")),
      "pay_type_display_name": _text(p.get("PayTypeDisplayName")),
      "amount": _to_float(p.get("PayAmount")),
      "cash_change": _to_float(p.get("CashChange")),
      "is_from_edc": _to_int(p.get("IsFromEDC")),
      "is_sale": _to_int(p.get("IsSale")),
      "is_other_receipt": _to_int(p.get("IsOtherReceipt")),
  }
  ```

  `payment_map` dikelompokkan per `TransactionID`, sama seperti `detail_map`.
  `computer_id` ikut dikirim supaya sync-api tetap bisa membedakan baris kalau
  `TransactionID` yang sama muncul di dua `ComputerID` (langkah 0 poin 4).

- Tambahkan `PAYMENT_FIELDS` dan panggil
  `warn_missing_columns(payments, PAYMENT_FIELDS, "payment")`, seperti header
  dan detail.

### 5.4 Diagnostik

- `dump_source_sample()`: ikutkan data pembayaran, supaya struktur kolom
  `vw_orderpaydetail` di outlet bisa dicek dari file `logs/`.
- `warn_incomplete_sales()`: beri peringatan untuk transaksi lunas
  (`transaction_status_id = 2`, `receipt_id > 0`, `deleted = 0`) yang tidak
  punya pembayaran, dan untuk transaksi yang Σ `amount` ≠ `receipt_pay_price`.
- `APIClient._summarize()`: tambahkan jumlah baris pembayaran dan jumlah
  transaksi tanpa pembayaran.

### 5.5 Dokumentasi dan rilis

- Perbarui `docs/database.md` (view `vw_orderpaydetail`) dan
  `docs/api-integration.md` (field `payments`).
- Build ulang `main.exe` dan `worker.exe`, lalu pasang di setiap outlet.

---

## 6. Urutan rilis

1. **View dulu atau agen dulu, dua-duanya aman**, asalkan 5.2 (outlet tanpa
   view) sudah diterapkan. Agen baru tanpa view tetap mengirim seperti
   sekarang. View tanpa agen baru tidak dibaca siapa pun.
2. **Agen boleh dirilis sebelum sync-api.** Skema Pydantic di sync-api
   mengabaikan field yang tidak dikenal, jadi `payments` dari agen baru tidak
   menimbulkan error, hanya belum disimpan. Agen lama tetap jalan karena tidak
   mengirim field itu.
3. **sync-api harus bisa membedakan "belum ada data" dari "tidak ada
   pembayaran".** Payload tanpa key `payments` (agen lama, atau outlet tanpa
   view) disimpan sebagai *tidak diketahui*. `payments: []` artinya memang
   tidak ada pembayaran.
4. **Data lama tidak ikut terkirim otomatis.** Agen hanya mengirim tanggal
   yang dipilih saat closing. Supaya tanggal yang sudah lewat punya
   pembayaran, closing tanggal itu harus diulang di outlet setelah agen baru
   dan view terpasang. Pengiriman ulang aman karena sync-api memakai upsert.

---

## 7. Perubahan di sync-api (setelah agen siap)

Ringkasan saja, karena perlu dirancang tersendiri:

- **Skema**: `SalesSchema.payments: Optional[list[SalesPaymentSchema]] = None`.
- **Identitas outlet dan sistem POS** sudah diketahui sync-api dari
  `API_KEY` yang dikirim agen. `API_KEY` itu berisi identitas outlet, dan
  sync-api sudah mengolahnya. Agen dan payload **tidak** perlu field
  tambahan. Jangan menebak sistem POS dari nama jenis bayar.
- **Tabel baru** untuk baris pembayaran, dengan kunci
  `(outlet_code, TransactionID, computer_id, pay_detail_id)`, sesuai PK
  tabel pembayaran di kedua sistem POS. Sistem POS mengikuti outlet. Ini butuh
  **migrasi**, jadi perlu persetujuan sebelum dibuat.
- **Master jenis bayar di sync-api** (kalau dibuat) berkunci
  (sistem POS, `pay_type_id`), **tidak pernah** nama saja. "Cash" Promise
  dan "Cash" Vtec adalah dua baris berbeda.
- **Upsert per transaksi.** Baris pembayaran bisa berubah, misalnya saat
  metode bayar diganti sebelum closing. Caranya perlu diputuskan: menghapus
  baris lama transaksi itu sebelum insert, atau menandainya tidak aktif.
- **Kirim closing**:
  - `payments` dijumlahkan per tujuan kunjungan + metode **di dalam satu
    sistem POS**. Jenis bayar dari Promise dan Vtec tidak pernah dijumlahkan
    bersama, walaupun namanya sama;
  - `paymentMethod` diisi nama jenis bayar dari POS apa adanya. ERP Gateway
    yang memetakannya ke akun, dan pemetaan itu dibuat **per sistem POS**
    (pertanyaan #2);
  - rekap **diblokir** kalau Σ `payments` ≠ `grandTotal` per tujuan
    kunjungan.

---

## 8. Temuan lain di view yang ada (di luar `payments`)

Ditemukan saat membaca `queryPOS/`. Bukan bagian dari perubahan ini, tetapi
perlu diputuskan:

| # | Sistem | Temuan | Dampak |
|---|---|---|---|
| 1 | Vtec | `vw_ordertransaction`: `ReceiptTotalQty AS ReceiptTotalAmount` | `receipt_total_amount` di outlet Vtec berisi **jumlah qty**, bukan nominal. `warn_incomplete_sales()` hanya memeriksa nilai 0, jadi tidak tertangkap. |
| 2 | Vtec | `vw_ordertransaction`: `PaidTime AS CloseTime` | `close_time` sama dengan waktu bayar. |
| 3 | Vtec | `vw_orderdetail` tidak punya `MinimumPrice` | Agen memberi peringatan kolom hilang dan mengirim 0. |
| 4 | Keduanya | `vw_ordertransaction` tidak memfilter `Deleted` | Transaksi yang dihapus tetap terkirim, tanpa item, dan nanti tanpa pembayaran. |
| 5 | Keduanya (terbukti di Promise) | `vw_ordertransaction` tidak menampilkan `ComputerID`, padahal `TransactionID` **tidak unik** antar `ComputerID`. Di server B ada 11.930 `TransactionID` yang dipakai lebih dari satu komputer (3.5). | **Agen:** aman untuk sekarang. Dalam 30 hari tidak ada bentrok di tanggal yang sama, dan agen selalu memfilter per tanggal. **sync-api:** berisiko. Kalau header/item disimpan dengan kunci (outlet, `TransactionID`) saja, transaksi komputer lain dengan `TransactionID` yang sama di tanggal lain bisa **menimpa** data lama saat upsert. Perlu dicek di sync-api. Perbaikan jangka panjang: tambahkan `ComputerID` ke `vw_ordertransaction` dan ke kunci penyimpanan. |
| 6 | Vtec | Query lama `bsum_tran` (`vtecQuery2.sql`) menjumlah `ReceiptPayPrice` setelah join ke `orderpaydetail` | Transaksi dengan dua metode bayar terhitung dua kali. Jangan jadikan acuan angka. |

---

## 9. Pertanyaan yang masih terbuka

| # | Pertanyaan | Ditanyakan ke |
|---|---|---|
| 1 | **Promise selesai** (3.5): `Amount` bersih dan Σ = `ReceiptPayPrice` selama 30 hari, `Paid` tidak dipakai, voucher adalah diskon, dan tidak ada bentrok `TransactionID` di tanggal yang sama. Yang tersisa: **Vtec**, yaitu apakah Σ `PayAmount` = `ReceiptPayPrice` dan arti `Paid`/`CashChange` | Cek langsung di POS Vtec (langkah 0) |
| 2 | Di dalam **satu sistem POS**, apakah `PayTypeID` dan namanya sama di semua outlet? Promise dan Vtec **tidak** dibandingkan, karena jenis bayarnya memang dipisah (aturan di bagian 1). ERP Gateway perlu tahu bahwa pemetaan akunnya per (sistem POS, jenis bayar). | Cek langsung di POS, lalu ERP Gateway |
| 3 | Kenapa query lama Vtec membuang `PayTypeID` 10008/10051/10152 (debit BNI, debit BRI, QRIS BNI)? Apakah aturan ini juga berlaku untuk rekap ERP? Untuk Promise, aturannya (kalau ada) ditetapkan sendiri dengan ID Promise. Aturan Vtec tidak disalin ke Promise berdasarkan kemiripan nama (mis. QRIS BNI Vtec = 10152, Promise = 864). | Tim keuangan / pemilik query lama |
| 4 | Apakah transaksi `Deleted = 1` perlu dikirim ke sync-api? | Tim keuangan |
| 5 | Apa beda `paymentAmount` dan `fullPaymentAmount`? (mis. sebelum/sesudah MDR, atau termasuk kembalian) | ERP Gateway |
| 6 | Apakah COA diisi sepenuhnya oleh ERP Gateway? | ERP Gateway |
| 7 | Apakah MDR diisi sepenuhnya oleh ERP Gateway? Kalau ERP mewajibkan kita yang mengirim, dari mana sumbernya? Tanyakan bersama #5, karena jawabannya saling terkait. | ERP Gateway |
| 8 | Kalau Σ pembayaran ≠ `grandTotal` (mis. pembulatan di kasir), dikirim sebagai `roundingTotal` atau rekap diblokir? | ERP Gateway |
