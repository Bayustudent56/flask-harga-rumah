"""Studi kasus: Dashboard Harga Rumah Yogyakarta dengan Flask + Chart.js.

Jalankan:
    pip install flask pandas
    python app.py
lalu buka http://127.0.0.1:5000
"""
import re
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

# 1. Muat dataset
df_raw = pd.read_csv("data/rumah123_yogya_unfiltered.csv")


def konversi_harga(teks):
    """Konversi teks 'Rp 1,79 Miliar' atau 'Rp 695 Juta' ke satuan Juta Rupiah (float)."""
    if pd.isnull(teks):
        return np.nan
    s = str(teks).replace("Rp", "").strip().replace(",", ".")
    bagian = s.split()
    if len(bagian) < 2:
        return np.nan
    try:
        angka = float(bagian[0])
    except ValueError:
        return np.nan
    satuan = bagian[1].lower()
    if "miliar" in satuan:
        return angka * 1000.0
    if "juta" in satuan:
        return angka
    if "triliun" in satuan:
        return angka * 1000000.0
    return angka


def konversi_luas(teks):
    """Ambil angka luas dari teks seperti '120 m²'."""
    if pd.isnull(teks):
        return np.nan
    cocok = re.search(r"[-+]?\d*\.\d+|\d+", str(teks).replace(",", "."))
    if cocok:
        nilai = float(cocok.group(0))
        return nilai if nilai > 0 else np.nan
    return np.nan


def kategori_harga(h):
    """Kelompokkan harga (dalam Juta Rupiah) ke dalam 5 kelas."""
    if h < 500:
        return "< 500 Juta"
    if h <= 1000:
        return "500 Jt - 1 M"
    if h <= 2000:
        return "1 M - 2 M"
    if h <= 5000:
        return "2 M - 5 M"
    return "> 5 Miliar"


def kategori_kamar(b):
    """Kelompokkan jumlah kamar tidur (1 KT s.d. 6+ KT)."""
    k = int(b) if pd.notnull(b) and b > 0 else 1
    return f"{k} KT" if k <= 5 else "6+ KT"


# 2. Pembersihan dan transformasi kolom
df_raw["harga_juta"] = df_raw["price"].apply(konversi_harga)
df_raw["luas_tanah"] = df_raw["surface_area"].apply(konversi_luas)
df_raw["luas_bangunan"] = df_raw["building_area"].apply(konversi_luas)
df_raw["kecamatan"] = df_raw["listing-location"].apply(
    lambda x: str(x).split(",")[0].strip() if pd.notnull(x) else "Lainnya"
)
df_raw["kabupaten"] = df_raw["listing-location"].apply(
    lambda x: str(x).split(",")[-1].strip() if pd.notnull(x) else "Lainnya"
)

# Hapus baris kosong dan outlier ekstrem (misal salah input luas bangunan > 2000 m²)
df = df_raw.dropna(subset=["harga_juta", "luas_tanah", "luas_bangunan"]).copy()
df = df[(df["luas_bangunan"] <= 2000) & (df["luas_tanah"] <= 5000)]

df["kelas_harga"] = df["harga_juta"].apply(kategori_harga)
df["kelas_kamar"] = df["bed"].apply(kategori_kamar)

URUTAN_HARGA = ["< 500 Juta", "500 Jt - 1 M", "1 M - 2 M", "2 M - 5 M", "> 5 Miliar"]
URUTAN_KAMAR = ["1 KT", "2 KT", "3 KT", "4 KT", "5 KT", "6+ KT"]


def filter_data():
    """Ambil filter ?kabupaten=Sleman dari URL (opsional)."""
    data = df
    kabupaten = request.args.get("kabupaten", type=str)
    if kabupaten:
        data = data[data["kabupaten"] == kabupaten]
    return data


@app.route("/")
def dashboard():
    daftar_kabupaten = sorted(df["kabupaten"].unique().tolist())
    return render_template("dashboard.html", daftar_kabupaten=daftar_kabupaten)


@app.route("/api/ringkasan")
def ringkasan():
    data = filter_data()
    if data.empty:
        return jsonify(total_unit=0, rata_harga=0, median_luas=0, persen_terjangkau=0)
    return jsonify(
        total_unit=int(len(data)),
        rata_harga=round(float(data["harga_juta"].mean()), 1),
        median_luas=int(round(float(data["luas_bangunan"].median()), 0)),
        persen_terjangkau=round(float((data["harga_juta"] <= 1000).mean() * 100), 1),
    )


@app.route("/api/rata-lokasi")
def rata_lokasi():
    data = filter_data()
    kabupaten = request.args.get("kabupaten", type=str)
    # Jika semua wilayah dipilih, tampilkan rata-rata per Kabupaten/Kota
    # Jika 1 Kabupaten dipilih, tampilkan Top 10 Kecamatan termahal di kabupaten tersebut
    kolom_grup = "kecamatan" if kabupaten else "kabupaten"
    hasil = (
        data.groupby(kolom_grup)["harga_juta"]
        .mean()
        .sort_values(ascending=False)
        .head(10)
        .round(1)
    )
    return jsonify(
        judul=f"Rata-rata harga per {kolom_grup.capitalize()} (Juta Rp)",
        labels=hasil.index.tolist(),
        data=hasil.tolist(),
    )


@app.route("/api/distribusi-harga")
def distribusi_harga():
    hasil = (
        filter_data()["kelas_harga"]
        .value_counts()
        .reindex(URUTAN_HARGA, fill_value=0)
    )
    return jsonify(labels=hasil.index.tolist(), data=hasil.tolist())


@app.route("/api/tren-kamar")
def tren_kamar():
    data = filter_data()
    kabupaten = request.args.get("kabupaten", type=str)

    if kabupaten:
        hasil = (
            data.groupby("kelas_kamar")["harga_juta"]
            .mean()
            .reindex(URUTAN_KAMAR)
            .fillna(0)
            .round(1)
        )
        datasets = [{"label": kabupaten, "data": hasil.tolist()}]
    else:
        # Tampilkan perbandingan 3 wilayah dengan listing terbanyak agar grafik rapi
        top_kab = ["Sleman", "Yogyakarta", "Bantul"]
        sub = data[data["kabupaten"].isin(top_kab)]
        hasil = (
            sub.groupby(["kelas_kamar", "kabupaten"])["harga_juta"]
            .mean()
            .unstack()
            .reindex(URUTAN_KAMAR)
            .fillna(0)
            .round(1)
        )
        datasets = [
            {"label": k, "data": hasil[k].tolist()}
            for k in top_kab
            if k in hasil.columns
        ]

    return jsonify(labels=URUTAN_KAMAR, datasets=datasets)


if __name__ == "__main__":
    app.run(debug=True)