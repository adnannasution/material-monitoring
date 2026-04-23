# 📦 PRISMA · TA-ex System — Python Streamlit Version

Sistem manajemen reservasi material SAP berbasis Python Streamlit.  
Mendukung data ratusan ribu baris dengan PostgreSQL + pandas.

---

## 🚀 Cara Menjalankan

### 1. Prasyarat

- Python 3.10+
- PostgreSQL 14+ (lokal atau cloud: Railway, Supabase, Neon, dll.)

---

### 2. Install Dependensi

```bash
cd prisma_taex
pip install -r requirements.txt
```

---

### 3. Konfigurasi Database

Salin file `.env.example` menjadi `.env` lalu isi:

```bash
cp .env.example .env
```

Isi `.env`:

```env
DATABASE_URL=postgresql://user:password@localhost:5432/prisma_taex
DB_SSL=false
```

**Contoh untuk Railway:**
```env
DATABASE_URL=postgresql://postgres:AbCdEf@containers-us-west-1.railway.app:7890/railway
DB_SSL=true
```

**Contoh untuk Supabase:**
```env
DATABASE_URL=postgresql://postgres:password@db.xxxx.supabase.co:5432/postgres
DB_SSL=true
```

---

### 4. Jalankan Aplikasi

```bash
streamlit run app.py
```

Buka browser di: **http://localhost:8501**

Saat pertama kali dijalankan, tabel database otomatis dibuat (auto-migrate).

---

## 📁 Struktur File

```
prisma_taex/
├── app.py              ← Aplikasi Streamlit utama (UI + logika tab)
├── database.py         ← Koneksi PostgreSQL, migrasi, helper query
├── bulk_ops.py         ← Operasi bulk INSERT/UPSERT (cepat, ratusan ribu baris)
├── header_maps.py      ← Normalisasi nama kolom Excel ke field internal
├── styles.py           ← CSS kustom agar tampilan rapi
├── requirements.txt    ← Daftar dependensi Python
├── .env.example        ← Template konfigurasi environment
├── .env                ← (buat sendiri, jangan di-commit ke git)
└── .streamlit/
    └── config.toml     ← Konfigurasi Streamlit (tema, upload limit)
```

---

## 🗂 Fitur Utama

| Tab | Deskripsi |
|-----|-----------|
| 📦 TA-ex Reservasi | Tabel utama reservasi material SAP. Upload Excel, search, export. |
| 📋 PRISMA Reservasi | Sinkron dari TA-ex, filter ICt=L & Del/FIs bukan X. |
| 📝 Kertas Kerja | Buat Kertas Kerja per Planner Group dan Work Order. |
| 📊 Summary | Ringkasan per material dari Kertas Kerja. |
| 🗂 Kumpulan Summary | Histori semua Kertas Kerja. Sinkron nomor PR dari SAP PR. |
| 🧾 SAP PR | Upload dan kelola data Purchase Request dari SAP. |
| 📋 Order | Upload dan kelola data Work Order dari SAP. |
| 🛒 PO | Upload dan kelola data Purchase Order dari SAP. |
| 🔍 Tracking | End-to-end tracking: TA-ex → PR → PO → Delivery. |
| 🔎 Audit | Bandingkan kolom TA-ex vs PRISMA, tampilkan perbedaan. |
| ⚙ Reset | Reset semua data (butuh konfirmasi teks). |

---

## 📥 Format Upload Excel

### TA-ex Reservasi
Header yang didukung (case-insensitive, format baru SAP maupun lama):

`PlPl, Equipment, Order, Reserv.No., Revision, Material, Itm, Material Description, Reqmt Qty, Qty_Stock, PR, Item, Qty_PR, Cost Ctrs, SLoc, Del, FIs, ICt, PG, Recipient, Unloading Point, Reqmt Date, Qty. f. avail.check, Qty Withdrawn, BUn, G/L Acct, Price, per, Crcy`

### SAP PR
`Plnt, Purch.Req., Item, Material, Material Description, D, Rel, PGr, S, TrackingNo, Qty Requested, Un, Req.Date, Valn Price, Crcy, Per, Release Dt`

### SAP PO
`Plnt, Purchreq, Item, Material, Short_Text, PO, PO_Item, D, DCI, PGr, Doc_Date, PO_Quantity, Qty_Delivered, Deliv_Date, OUn, Net_Price, Crcy, Per`

### Order
`Plant, Order, Superior order, Notification, Created on, Description, Revision, Equipment, System status, User status, Functional Loc., Location, WBS ord. header, Cost Center, TotalPlnndCosts, Total act.costs, Planner group, Main WorkCtr, Entered by, Changed by, Bas. start date, Basic fin. date, Actual release`

---

## ⚡ Performa

- **Pandas** digunakan untuk baca file Excel di memory — jauh lebih cepat dari parsing di browser.
- **`execute_values`** dari psycopg2 untuk bulk INSERT (ribuan baris per query batch).
- **`@st.cache_data`** meng-cache hasil query DB untuk response cepat saat filter/paging.
- Upload file Excel 100k baris biasanya selesai dalam 10–30 detik tergantung koneksi DB.

---

## 🐳 Deploy ke Railway / Server

1. Push folder `prisma_taex/` ke GitHub repo
2. Di Railway: **New Project → Deploy from GitHub Repo**
3. Set environment variable: `DATABASE_URL` dan (opsional) `DB_SSL=true`
4. Railway otomatis detect `requirements.txt` dan jalankan dengan:
   ```
   streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```
5. Atau tambahkan `Procfile`:
   ```
   web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```

---

## 🔒 Keamanan (Opsional)

Tambahkan autentikasi sederhana di `app.py` dengan `st.secrets` atau library `streamlit-authenticator`.

---

## 📞 Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `psycopg2` error install | `pip install psycopg2-binary` (bukan `psycopg2`) |
| Tidak bisa konek DB | Periksa `DATABASE_URL` di `.env`, pastikan PostgreSQL berjalan |
| Upload file gagal | Cek `maxUploadSize` di `.streamlit/config.toml` (default 500MB) |
| Data tidak muncul setelah upload | Klik tombol 🔄 Refresh atau reload halaman |
| SSL error Railway/Supabase | Set `DB_SSL=true` di `.env` |
