# API Integration

Implementasi: [core/api_client.py](../core/api_client.py),
payload disusun di [dashboard_controller.py:285](../controllers/dashboard_controller.py#L285).

Base URL, timeout, dan API key diambil dari section `[API]` di `config.ini`.

---

## 1. Endpoint

### `POST {BASE_URL}/sync/sales`

Mengirim data penjualan. Dipanggil **oleh worker**, bukan oleh GUI.

**Headers**
```
Authorization: Bearer {API_KEY}
User-Agent: PromisePOS-Internal/1.0
Accept: application/json
Content-Type: application/json
```

**Body** — isi field `payload` dari row antrian, yaitu `{"sales": [...]}`
(wrapper `meta` tidak ikut terkirim).

**Respons yang diharapkan:** HTTP `200` = sukses (row dihapus dari antrian).
Status lain apa pun dianggap gagal → `retry_count += 1`, item tetap di antrian.

### `POST {BASE_URL}/sales/publish?t={timestamp}`

Memicu publish ke message broker. Dipanggil **oleh GUI** dalam loop polling.

**Headers**
```
Authorization: Bearer {API_KEY}
User-Agent: PostmanRuntime/7.54.0
Accept: */*
Content-Type: application/json
Cache-Control: no-cache
Connection: close
```

**Body**
```json
{
  "exchange": "posdata_exchange",
  "routing_key": "posdata.created",
  "date": "2026-04-08"
}
```

**Deteksi sukses:** GUI mem-parse JSON respons dan mengecek apakah field
`message` mengandung substring `"published"` (case-insensitive). Timeout
hardcode 30 detik, query param `?t=` untuk cache-busting.

⚠️ Deteksi berbasis substring ini rapuh — kalau backend mengubah teks pesan,
closing akan selalu gagal walau datanya sukses.

---

## 2. Struktur payload

### Wrapper di antrian

Yang disimpan `insert_queue()` ke kolom `payload`:

```json
{
  "meta": {
    "date": "2026-04-08",
    "batch_id": "BATCH-1775635200",
    "source": "pos_closing_system"
  },
  "payload": { "sales": [ ... ] }
}
```

`batch_id` = `BATCH-{int(time.time())}`. `meta` **hanya untuk keperluan lokal** —
worker meng-unwrap dan hanya mengirim isi `payload`.

### Body yang dikirim ke `/sync/sales`

```json
{
  "sales": [
    {
      "transaction_id": 12345,
      "invoice_number": "INV-0001",
      "reference_no": "INV-0001",

      "sale_date": "2026-04-08",
      "paid_time": "2026-04-08T14:23:11",
      "close_time": "2026-04-08T14:25:00",
      "trx_date": "2026-04-08T14:23:11",

      "shop_id": 1,
      "transaction_status_id": 1,
      "sale_mode": 1,
      "no_customer": 2,
      "deleted": 0,

      "receipt_id": 4501,
      "receipt_month": 4,
      "receipt_year": 2026,

      "receipt_product_retail_price": 150000.0,
      "receipt_sale_price": 150000.0,
      "receipt_pay_price": 168000.0,
      "receipt_discount": 0.0,
      "receipt_total_amount": 168000.0,

      "other_percent_discount": 0.0,
      "other_amount_discount": 0.0,

      "vat_percent": 10.0,
      "transaction_vat": 15000.0,
      "transaction_exclude_vat": 0.0,
      "transaction_vatable": 150000.0,

      "service_charge_percent": 5.0,
      "service_charge": 7500.0,
      "service_charge_vat": 750.0,

      "other_income": 0.0,
      "other_income_vat": 0.0,

      "void_staff_id": 0,
      "void_reason": "",
      "void_time": null,

      "transaction_note": "",
      "queue_name": "A01",

      "is_split_transaction": 0,
      "is_from_other_transaction": 0,

      "items": [
        {
          "order_detail_id": 98765,
          "transaction_id": 12345,
          "sale_date": "2026-04-08",

          "product_id": 501,
          "product_name": "Nasi Goreng",
          "product_group": "Main Course",
          "product_dept": "Kitchen",

          "product_set_type": 0,
          "order_status_id": 2,
          "sale_mode": 1,

          "qty": 2.0,
          "price": 45000.0,
          "retail_price": 45000.0,
          "minimum_price": 0.0,

          "comment": "",
          "order_staff_id": 3,
          "order_table_id": 12,
          "void_staff_id": 0
        }
      ]
    }
  ]
}
```

### Pemetaan kolom DB → field JSON

| Kolom DB (header) | Field JSON | Catatan |
|---|---|---|
| `TransactionID` | `transaction_id` | `int`, juga kunci join ke items |
| `ReferenceNo` | `invoice_number` **dan** `reference_no` | dikirim dua kali (kompatibilitas) |
| `PaidTime` | `paid_time` **dan** `trx_date` | ISO 8601 via `to_iso()` |
| `CloseTime` | `close_time` | ISO / `null` |
| `VoidTime` | `void_time` | ISO / `null` |

| Kolom DB (detail) | Field JSON |
|---|---|
| `OrderDetailID` | `order_detail_id` |
| `Amount` | `qty` (float) |
| `ProductGroupName` | `product_group` |
| `ProductDeptName` | `product_dept` |

**Konversi tipe:** semua ID → `int`, semua nominal → `float`, teks nullable →
`""`, waktu → ISO string atau `null`. Field yang tidak wajib diakses lewat
`.get(key, default)`, jadi kolom hilang tidak membuat crash — tapi
`TransactionID`, `OrderDetailID`, `ProductID`, `Amount`, `Price`, dan
`ReceiptID` **wajib ada**.

---

## 3. Mekanisme antrian & retry

```
GUI:  enqueue_sales()  →  INSERT queue (status='pending', retry_count=0)

Worker (loop tiap 10 detik):
  items = get_pending(limit=10)
  untuk tiap item:
      unwrap payload → POST /sync/sales
      200      → mark_sent(id)        # baris DIHAPUS
      selain   → increase_retry(id)
      exception→ increase_retry(id)
      sleep(1 + retry_count)          # backoff per item
```

Karakteristik yang perlu diketahui:

- **Tidak ada batas retry.** Item bermasalah dicoba selamanya. Karena
  `get_pending()` memakai `ORDER BY id ASC`, satu item yang selalu gagal
  ikut memperlambat batch (backoff makin lama) tapi tidak memblokir item lain
  di batch yang sama.
- **Backoff linear**, bukan eksponensial: `1 + retry_count` detik.
- **Batch maksimum 10 item** per siklus.
- **Tidak ada dedup.** Kirim ulang tanggal yang sama menghasilkan payload yang
  sama lagi — server harus idempotent terhadap `transaction_id`.
- **Worker mem-print seluruh payload JSON** ke stdout setiap kirim
  ([api_client.py:126](../core/api_client.py#L126)). Berisik dan lambat untuk
  data besar; kandidat untuk dibersihkan.

## 4. `last_sync`

Disimpan di `sync_state` (`queue.db`) sebagai `ReceiptID` terbesar yang sudah
di-enqueue, dan dipakai `get_sales_header()` sebagai `WHERE ReceiptID > last_sync`.

Yang perlu diingat:

- Di-update di **controller setelah enqueue**, bukan setelah kirim sukses.
- Update di `process_queue()` sengaja dikomentari
  ([api_client.py:140](../core/api_client.py#L140)).
- Karena `recreate_db()` jalan setiap startup, `last_sync` **selalu 0 di awal
  sesi** → transaksi tanggal terpilih dikirim ulang dari awal. Ini yang membuat
  idempotency di sisi server menjadi syarat mutlak.

## 5. Tes manual endpoint

```powershell
# ganti <BASE_URL> dan <API_KEY> sesuai config.ini
curl -X POST "<BASE_URL>/sales/publish" `
     -H "Authorization: Bearer <API_KEY>" `
     -H "Content-Type: application/json" `
     -d '{\"exchange\":\"posdata_exchange\",\"routing_key\":\"posdata.created\",\"date\":\"2026-04-08\"}'
```

Untuk melihat payload tanpa mengirim: jalankan `python main.py`, klik
**Closing Colorplate**, dan baca console — `send_to_api()` mencetak preview
transaksi pertama sebelum enqueue.
