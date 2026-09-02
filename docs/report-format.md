# Report Format

Implementasi: [core/report_generator.py](../core/report_generator.py).

Format ini **fixed-width** dan sudah dicocokkan dengan sistem penerima di kantor
pusat. Jangan ubah lebar kolom tanpa permintaan eksplisit.

## Output

| Item | Nilai |
|---|---|
| Path | `reports/{OUTLET}_{YYYY-MM-DD}.txt` |
| Contoh | `reports/BIPVJ_2026-04-08.txt` |
| Encoding | UTF-8 |
| Lebar baris | 35 karakter untuk bagian header/total |
| Mode tulis | `'w'` — file dengan nama sama **ditimpa** |

## Contoh isi

```
          Consolidate Sale         
            8 April 2026           
         End Time 16:55:28         
             Shop:BIPVJ            
BIPVJ:BIPVJ
Dine In
Main Course        12          540000 
Beverage            8          160000 
Sub Total                    700000
Discount                          0
Total Dine In :   20          700000

Take Away 
Beverage            3           60000 
Total Take Away :  3          60000

Sub Total                    760000
Discount                          0
Sub Total :       23          760000

BIPVJ:BIPVJ             836000
Discount                          0
Sub Total                    760000
SVC                           38000
Pb1                           38000

Total Sales                  836000
```

## Struktur per bagian

### Header (rata tengah, lebar 35)

```python
"Consolidate Sale".center(35)
"8 April 2026".center(35)          # nama bulan hardcode bahasa Inggris
"End Time 16:55:28".center(35)     # jam saat generate, bukan jam closing
("Shop:" + outletname).center(35)
outletcode + ":" + outletname      # tanpa center
```

Nama bulan diambil dari list `MONTHS` di dalam kode, **bukan** dari `strftime`.
Ini disengaja supaya output tidak berubah mengikuti locale mesin.

### Baris item (Dine In / Take Away)

```python
str(Group)[0:14].ljust(15) + str(int(TotalQty)).center(10) + str(int(AmountMenu)).rjust(10) + " \n"
```

| Segmen | Lebar | Isi |
|---|---|---|
| Nama grup | 15 (dipotong di 14) | `bsum_menu.Group` |
| Qty | 10, rata tengah | `TotalQty` dibulatkan ke int |
| Nominal | 10, rata kanan | `AmountMenu` dibulatkan ke int |
| Spasi + newline | 2 | literal `" \n"` |

### Blok total

```python
"Sub Total " + str(int(totaldine)).rjust(25)
"\nDiscount" + str(disc).rjust(27)
"\nTotal Dine In :" + str(int(countdine)).center(10) + str(int(totaldine - disc)).rjust(10)
...
"Total Take Away : " + str(int(counttake)).center(3) + str(int(totaltake)).rjust(14)
```

Perhatikan lebar yang **tidak konsisten** antara blok Dine In dan Take Away
(`center(10)`/`rjust(10)` vs `center(3)`/`rjust(14)`). Ini mereplikasi program
lama dan memang begitu adanya — bukan bug yang perlu "dirapikan".

### Footer

```python
outletcode + ":" + outletname[0:18] + summary.rjust(13)
"\nDiscount".ljust(25)  + str(disc).rjust(11)
"\nSub Total".ljust(25) + str(trans).rjust(11)
"\nSVC".ljust(25)       + str(service).rjust(11)
"\nPb1".ljust(25)       + str(tax).rjust(11)
"\n\nTotal Sales" + str(int(trans + service + tax)).rjust(24)
```

`.ljust(25)` di sini diterapkan pada string yang sudah mengandung `\n` di
depannya, jadi lebar efektifnya 24 karakter setelah newline.

## Sumber data

| Variabel | Asal | Catatan |
|---|---|---|
| `summary` | `bsum_trans.AmountSummary` | string apa adanya |
| `disc` | `bsum_trans.Disc` | `int` |
| `trans` | `bsum_trans.AmountTransaksi` | `float` — dicetak apa adanya, bisa muncul `.0` |
| `service` | `bsum_trans.AmountService` | `int` |
| `tax` | `bsum_trans.Tax` | `int` (Pb1) |
| `outletcode` / `outletname` | `bsum_trans.OutletCode` / `.OutletName` | fallback ke `OUTLET` di config |
| Baris Dine In | `bsum_menu` `salemode=1` | |
| Baris Take Away | `bsum_menu` `salemode=2` | |

⚠️ **Hanya baris terakhir `bsum_trans` yang dipakai** (`transactions[-1]`).
Kalau query mengembalikan lebih dari satu baris untuk satu tanggal, baris lain
diabaikan. Kalau kosong, semua nilai jadi 0 dan `outletcode`/`outletname` jatuh
ke kode outlet dari config — inilah kenapa report tanggal tanpa transaksi
terlihat seperti contoh `BIPVJ_2026-04-08.txt` (semua nol).

## Perhitungan

```
totaldine  = Σ AmountMenu   (salemode=1)
countdine  = Σ TotalQty     (salemode=1)
totaltake  = Σ AmountMenu   (salemode=2)
counttake  = Σ TotalQty     (salemode=2)

Total Dine In  = totaldine - disc
Sub Total      = totaldine + totaltake
Sub Total akhir= (totaldine + totaltake) - disc
Total Sales    = trans + service + tax
```

Catatan: `disc` dikurangkan **dua kali** dalam alur laporan (sekali di blok Dine
In, sekali di Sub Total akhir). Ini juga mengikuti perilaku program lama.

## Email

Dikirim oleh [core/email_sender.py](../core/email_sender.py):

- **Subject:** `Consolidate Report {OUTLET} {YYYY-MM-DD}`
- **Body:** teks plain berisi outlet, tanggal, waktu generate
- **Attachment:** file `.txt` di atas, `maintype='text'`, `subtype='plain'`,
  nama file asli dipertahankan
- **Transport:** `smtplib.SMTP_SSL` (port 465), login pakai `SENDER` + `PASSWORD`
- **Penerima:** `RECEIVER` + `CC` (kalau diisi)

## Kalau perlu mengubah format

1. Simpan dulu contoh output lama sebagai pembanding.
2. Ubah, generate ulang tanggal yang sama, lalu `diff` byte-per-byte.
3. Konfirmasi ke penerima laporan sebelum dirilis — format ini dibaca sistem
   lain, bukan hanya manusia.
