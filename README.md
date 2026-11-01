# Contoh Dashboard Nilai Mahasiswa (Flask + Chart.js)

Kode studi kasus visualisasi data untuk mata kuliah Aplikasi Web.
Data di `data/nilai.csv` adalah data contoh (bukan data asli).

## Menjalankan

```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
pip install -r requirements.txt
python app.py
```

Buka http://127.0.0.1:5000 di browser. Chart.js dimuat dari CDN, jadi perlu koneksi internet.

## Endpoint

| URL | Isi |
|---|---|
| `/` | Halaman dashboard |
| `/api/ringkasan` | Jumlah mahasiswa, rata-rata, % lulus |
| `/api/rata-prodi` | Rata-rata nilai per prodi |
| `/api/distribusi-grade` | Jumlah nilai huruf A sampai E |
| `/api/tren-semester` | Rata-rata per semester tiap prodi |

Semua endpoint `/api/...` menerima filter `?angkatan=2022` atau `?angkatan=2023`.
