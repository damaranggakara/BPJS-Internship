"""
Menghitung sekali seluruh angka untuk tab Analisis, lalu menyimpannya ke
Dashboard/models/<wilayah>/analysis.json, satu per wilayah.

Dijalankan SEKALI, seperti train_export.py. Dashboard yang berjalan hanya membaca
analysis.json (sekitar 240 KB; ukuran tepatnya dicetak skrip ini setiap kali
dijalankan) dan tidak pernah menyentuh CSV 42 MB, sehingga folder
Dashboard/ tetap hanya bergantung pada models/ miliknya sendiri.

SUMBER
------
Data      : Data Setiap Target Revised/dataset_master.csv  (satu-satunya berkas)
            Hanya master yang masih menyimpan target sebagai teks termasuk
            "Tidak Dapat Pertanyaan", yang justru dibutuhkan eligible() untuk
            memilih subpopulasi yang memang ditanyai per penyakit.

Notebook  : Analisis Hubungan Antar Variabel.ipynb
              sel 4  -> eligible(), cramers_v(), correlation_ratio(), tafsir()
              sel 18 -> rancangan histogram + garis prevalensi per desil
              sel 38 -> peta panas segmen x penyakit
              sel 41 -> matriks asosiasi
            Analisis Data Bersih.ipynb
              sel 13,14 -> kelompok usia, piramida, komposisi segmen
              sel 22    -> prevalensi menurut jenis kelamin & kelompok usia

Fungsi ukuran asosiasi disalin APA ADANYA dari notebook supaya dashboard tidak
mungkin menyimpang dari laporan.

GERBANG VERIFIKASI
------------------
Setelah dihitung, matriks asosiasi dan angka perancu dibandingkan dengan nilai
yang sudah dipublikasikan di catatan analisis 3.10/3.11. Bila ada satu saja yang
menyimpang lebih dari 0,0015 skrip berhenti dengan error.

Cara pakai:
    python Dashboard/build_analysis.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import gaussian_kde

DASHBOARD_DIR = Path(__file__).resolve().parent
# Akar proyek = folder terdekat di atas yang memuat Bersama/ (pola yang sama
# dipakai seluruh notebook), jadi letak folder Dashboard bebas.
AKAR = DASHBOARD_DIR
while not (AKAR / "Bersama").exists():
    AKAR = AKAR.parent
if str(AKAR / "Bersama") not in sys.path:
    sys.path.insert(0, str(AKAR / "Bersama"))
import bmi_standards as bs  # noqa: E402
import konfigurasi as cfg  # noqa: E402

ROOT = AKAR                                 # nama lama, masih dipakai modul lain

# Nama folder model per wilayah. WILAYAH/DATA_DIR/MODEL_DIR di-set per wilayah
# oleh siapkan_acuan() di bawah.
SLUG_WILAYAH = {"Bantul": "bantul", "Sleman": "sleman", "Gabungan": "gabungan"}

NUM = ["Usia", "Tinggibadan", "Berat Badan", "IMT_recalculated"]
CAT = ["Jeniskelamin", "segmen"]

# Nama penyakit mengikuti metadata.json agar seragam dengan seluruh dashboard.
TARGETS = {
    "Diabetes Melitus": ("Berisiko Diabetes Melitus", "15+"),
    "Hipertensi":       ("Berisiko Hipertensi", "15+"),
    "Kanker Paru":      ("Berisiko Kanker Paru", "45+"),
    "TBC":              ("Berisiko TBC", "semua usia"),
}

# Kelompok usia -- persis seperti Analisis Data Bersih sel 13.
AGE_BINS = [0, 5, 15, 25, 35, 45, 55, 65, 120]
AGE_LABELS = ["0-4", "5-14", "15-24", "25-34", "35-44", "45-54", "55-64", "65+"]

N_BIN = 45      # tepi histogram (44 batang), sama dengan notebook
N_KDE = 200     # titik evaluasi kurva KDE
N_DESIL = 10
TOLERANSI = 0.0015

# Toleransi terpisah untuk struktur baru. Keduanya JAUH lebih ketat daripada
# TOLERANSI karena yang diperiksa bukan angka publikasi yang dibulatkan,
# melainkan identitas aritmetika yang harus tepat.
TOL_IDENTITAS = 1e-6    # identitas aritmetika (jumlah, rata-rata berbobot)
TOL_PREV = 0.001        # prevalensi yang memang disimpan 3 desimal

# --------------------------------------------------------------------------
# Acuan verifikasi per wilayah
# --------------------------------------------------------------------------
# Gerbangnya punya DUA lapis, dan hanya lapis pertama yang bergantung wilayah:
#
#   1. Acuan EKSTERNAL -- angka yang sudah dipublikasikan di luar skrip ini.
#      Untuk Bantul, sumbernya catatan analisis; nilainya diketik di bawah dan tidak
#      boleh berubah, karena justru itulah yang membuat perubahan tak sengaja
#      pada data atau pipeline ketahuan. Untuk wilayah lain belum ada angka
#      terbit, jadi acuannya DIBUAT pada build pertama lalu disimpan ke
#      models/<wilayah>/acuan_analisis.json dan dipakai menggerbangi build
#      berikutnya.
#
#   2. Identitas INTERNAL -- jumlah yang harus kembali ke n, prevalensi yang
#      harus bisa dihitung ulang dari dua arah, penanda yang dihitung dua cara
#      harus sama. Semua ini berlaku di wilayah mana pun tanpa acuan apa pun,
#      jadi lapis kedua berjalan penuh sejak build pertama.
ACUAN_TERBIT = {
    "Bantul": {
        "asosiasi": {
            "Diabetes Melitus": [0.207, -0.074, 0.515, 0.616, 0.075, 0.105],
            "Hipertensi":       [0.054, 0.042, 0.297, 0.312, 0.035, 0.053],
            "Kanker Paru":      [-0.031, 0.203, 0.080, -0.032, 0.317, 0.040],
            "TBC":              [0.134, 0.049, 0.070, 0.066, 0.002, 0.094],
        },
        "perancu": {
            "tinggi_berat_pooled": 0.797, "tinggi_berat_dewasa": 0.463,
            "usia_imt_pooled": 0.356, "usia_imt_dewasa": -0.083,
            "tinggi_kp_pooled": 0.203, "tinggi_kp_L": 0.055,
            "tinggi_kp_P": -0.011,
        },
        # Jumlah baris per dataset -- catatan analisis 5. Dipakai supaya piramida
        # risiko diuji terhadap LAPORAN, bukan terhadap dirinya sendiri.
        "piramida_n": {
            "Diabetes Melitus": 277137, "Hipertensi": 272964,
            "Kanker Paru": 146540, "TBC": 353182,
        },
        # Sensus pola pertanyaan -- catatan analisis 3.13.
        "kookurensi": {
            "1111": {"n": 131768, "jumlah": [42941, 22983, 53844, 10627, 1373],
                     "keluar_n": 14772, "keluar_tbc": 32.934},
            "1101": {"n": 139793, "jumlah": [53216, 44453, 40127, 1997],
                     "keluar_n": 793, "keluar_tbc": 34.174},
        },
        "pola_total": 353182,
        "sumber": "catatan analisis 3.10/3.11/3.13/5",
    },
}

# Diisi ulang tiap wilayah oleh siapkan_acuan().
WILAYAH = None
DATA_DIR = None
MODEL_DIR = None
ACUAN_ASOSIASI = {}
ACUAN_PERANCU = {}
ACUAN_PIRAMIDA_N = {}
ACUAN_KOOKURENSI = {}
ACUAN_POLA_TOTAL = None
SUMBER_ACUAN = None


def siapkan_acuan(wilayah: str) -> None:
    """Menyiapkan jalur dan acuan verifikasi untuk satu wilayah."""
    global WILAYAH, DATA_DIR, MODEL_DIR, SUMBER_ACUAN
    global ACUAN_ASOSIASI, ACUAN_PERANCU, ACUAN_PIRAMIDA_N
    global ACUAN_KOOKURENSI, ACUAN_POLA_TOTAL

    WILAYAH = wilayah
    DATA_DIR = cfg.folder_data(wilayah)
    MODEL_DIR = DASHBOARD_DIR / "models" / SLUG_WILAYAH[wilayah]

    acuan = ACUAN_TERBIT.get(wilayah)
    if acuan is None:
        tersimpan = MODEL_DIR / "acuan_analisis.json"
        if tersimpan.exists():
            acuan = json.loads(tersimpan.read_text(encoding="utf-8"))
            acuan["sumber"] = f"{tersimpan.name} (build sebelumnya)"

    if acuan is None:
        SUMBER_ACUAN = None
        ACUAN_ASOSIASI, ACUAN_PERANCU = {}, {}
        ACUAN_PIRAMIDA_N, ACUAN_KOOKURENSI = {}, {}
        ACUAN_POLA_TOTAL = None
        return

    SUMBER_ACUAN = acuan["sumber"]
    ACUAN_ASOSIASI = acuan["asosiasi"]
    ACUAN_PERANCU = acuan["perancu"]
    ACUAN_PIRAMIDA_N = acuan["piramida_n"]
    ACUAN_KOOKURENSI = acuan["kookurensi"]
    ACUAN_POLA_TOTAL = acuan["pola_total"]

# Indeks AGE_LABELS yang seharusnya berisi baris untuk tiap penyakit, mengikuti
# gerbang usia catatan analisis 3.1. "5-14" adalah [5,15) sehingga usia 15+ mulai di
# indeks 2, dan usia 45+ mulai di indeks 5.
GERBANG_PITA = {
    "Diabetes Melitus": set(range(2, 8)),
    "Hipertensi":       set(range(2, 8)),
    "Kanker Paru":      set(range(5, 8)),
    "TBC":              set(range(0, 8)),
}


# --------------------------------------------------------------------------
# Fungsi ukuran asosiasi -- disalin dari notebook sel 4
# --------------------------------------------------------------------------
def cramers_v(x, y) -> float:
    ct = pd.crosstab(x, y)
    if min(ct.shape) < 2:
        return float("nan")
    n = ct.to_numpy().sum()
    exp = np.outer(ct.sum(axis=1), ct.sum(axis=0)) / n
    chi2 = ((ct.to_numpy() - exp) ** 2 / exp).sum()
    return float(np.sqrt((chi2 / n) / (min(ct.shape) - 1)))


def correlation_ratio(kategori, nilai) -> float:
    grand = nilai.mean()
    g = nilai.groupby(kategori, observed=True)
    antar = (g.count() * (g.mean() - grand) ** 2).sum()
    total = ((nilai - grand) ** 2).sum()
    return float(np.sqrt(antar / total)) if total > 0 else float("nan")


def tafsir(v: float) -> str:
    a = abs(v)
    if np.isnan(a):
        return "-"
    if a < 0.10:
        return "diabaikan"
    if a < 0.30:
        return "lemah"
    if a < 0.50:
        return "sedang"
    return "kuat"


def r2(x, n=4):
    """Bulatkan untuk JSON; NaN jadi None."""
    if isinstance(x, (list, tuple)):
        return [r2(v, n) for v in x]
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), n)


def bangun_wilayah(wilayah: str) -> int:
    siapkan_acuan(wilayah)
    print("-" * 78)
    print(f"WILAYAH {wilayah.upper()}")
    print("-" * 78)

    src = DATA_DIR / "dataset_master.csv"
    if not src.exists():
        print(f"\nGAGAL: {src} tidak ditemukan.")
        return 1

    df = pd.read_csv(src)
    df["Kelompok_Usia"] = pd.cut(df["Usia"], bins=AGE_BINS,
                                 labels=AGE_LABELS, right=False)
    print(f"\nData: {len(df):,} catatan skrining, usia "
          f"{int(df.Usia.min())}-{int(df.Usia.max())} tahun")

    def eligible(nama):
        col, _ = TARGETS[nama]
        sub = df[df[col].isin(["Berisiko", "Tidak Berisiko"])].copy()
        return sub, (sub[col] == "Berisiko").astype(int)

    out: dict = {
        "dibuat": datetime.now().isoformat(timespec="seconds"),
        "wilayah": wilayah,
        "sumber": "dataset_master.csv",
        "n_total": int(len(df)),
        "usia_min": int(df.Usia.min()),
        "usia_max": int(df.Usia.max()),
        "num_cols": NUM,
        "age_labels": AGE_LABELS,
        # Tepi pita usia ikut disimpan supaya app_streamlit.py dapat memetakan
        # usia pengguna ke kelompoknya tanpa menyalin ulang konstanta ini.
        # Dua salinan konstanta adalah cara paling umum keduanya jadi berbeda.
        "age_bins": AGE_BINS,
    }

    # ---------------- 1a. profil populasi (Bersih B1) ----------------
    pyr = (df.groupby(["Kelompok_Usia", "Jeniskelamin"], observed=True)
             .size().unstack(fill_value=0))
    out["piramida"] = {
        "kelompok": AGE_LABELS,
        "L": [int(pyr.get("L", pd.Series(dtype=int)).get(k, 0)) for k in AGE_LABELS],
        "P": [int(pyr.get("P", pd.Series(dtype=int)).get(k, 0)) for k in AGE_LABELS],
    }
    seg_count = df["segmen"].value_counts()
    out["segmen_jumlah"] = {k: int(v) for k, v in seg_count.items()}
    out["segmen_urut"] = list(seg_count.index)

    # ---------------- 1c. klasifikasi IMT (Bersih Lengkap II.2) ----------------
    # Dewasa dan anak DIPISAH karena ambangnya berbeda secara mendasar: dewasa
    # memakai ambang WHO yang tetap, anak memakai persentil CDC yang bergeser
    # tiap tahun usia. Menggabung keduanya dalam satu grafik akan membuat
    # "Overweight" berarti dua hal berbeda di sumbu yang sama.
    # Balita (< 2 th) tidak diklasifikasi sama sekali -- BMI-for-age tidak
    # berlaku secara medis di bawah 2 tahun -- jadi hanya jumlahnya yang dibawa.
    d_dewasa = df[df["Usia"] > bs.CHILD_MAX_AGE]
    d_anak = df[df["Usia"].between(bs.CHILD_MIN_AGE, bs.CHILD_MAX_AGE)]
    d_balita = df[df["Usia"] < bs.CHILD_MIN_AGE]

    urut_who8 = [l for _, l in bs.WHO_ADULT_BINS]
    hit_dewasa = d_dewasa["Kategori_BMI_WHO8"].value_counts()
    hit_anak = d_anak["Kategori_BMI_WHO8"].value_counts()

    out["klasifikasi_bmi"] = {
        "dewasa": {
            "n": int(len(d_dewasa)),
            "batas": f"> {bs.CHILD_MAX_AGE} th",
            # Urutan mengikuti WHO_ADULT_BINS, bukan urutan jumlah: kategori IMT
            # bersifat ordinal, jadi mengurutkannya menurut frekuensi akan
            # merusak maknanya.
            "kategori": {k: int(hit_dewasa.get(k, 0)) for k in urut_who8},
        },
        "anak": {
            "n": int(len(d_anak)),
            "batas": f"{bs.CHILD_MIN_AGE}-{bs.CHILD_MAX_AGE} th",
            # Urutan ordinal (kurus -> gemuk) diambil dari CDC_CHILD_LABELS,
            # sama alasannya dengan panel dewasa: mengurutkan menurut frekuensi
            # akan membuat kedua panel terbaca dengan aturan yang berbeda.
            "kategori": {k: int(hit_anak.get(k, 0))
                         for k in bs.CDC_CHILD_LABELS.values()},
        },
        "balita": {"n": int(len(d_balita)), "batas": f"< {bs.CHILD_MIN_AGE} th"},
    }

    # Gerbang identitas: ketiga kelompok harus menutup seluruh baris, dan tiap
    # kelompok harus habis terbagi ke kategorinya sendiri (kecuali balita yang
    # memang tidak diklasifikasi).
    kb = out["klasifikasi_bmi"]
    assert kb["dewasa"]["n"] + kb["anak"]["n"] + kb["balita"]["n"] == len(df), \
        "kelompok usia klasifikasi IMT tidak menutup seluruh baris"
    for kel in ("dewasa", "anak"):
        assert sum(kb[kel]["kategori"].values()) == kb[kel]["n"], \
            f"jumlah kategori IMT {kel} tidak sama dengan jumlah barisnya"

    # ---------------- 1b. korelasi antar variabel bebas ----------------
    korr = df[NUM].corr()
    out["korelasi_numerik"] = {a: {b: r2(korr.loc[a, b]) for b in NUM} for a in NUM}

    dewasa = df[df.Usia > 20]
    kp_sub, kp_y = eligible("Kanker Paru")
    perancu = {
        "tinggi_berat_pooled": df["Tinggibadan"].corr(df["Berat Badan"]),
        "tinggi_berat_dewasa": dewasa["Tinggibadan"].corr(dewasa["Berat Badan"]),
        "usia_imt_pooled": df["Usia"].corr(df["IMT_recalculated"]),
        "usia_imt_dewasa": dewasa["Usia"].corr(dewasa["IMT_recalculated"]),
        "tinggi_kp_pooled": kp_sub["Tinggibadan"].corr(kp_y),
        "tinggi_kp_L": (lambda g: g["Tinggibadan"].corr((g[TARGETS["Kanker Paru"][0]] == "Berisiko").astype(int)))(kp_sub[kp_sub.Jeniskelamin == "L"]),
        "tinggi_kp_P": (lambda g: g["Tinggibadan"].corr((g[TARGETS["Kanker Paru"][0]] == "Berisiko").astype(int)))(kp_sub[kp_sub.Jeniskelamin == "P"]),
    }
    out["perancu"] = {k: r2(v) for k, v in perancu.items()}
    out["kp_prev_sex"] = {
        s: r2(kp_y[kp_sub.Jeniskelamin == s].mean() * 100, 2) for s in ("L", "P")
    }

    # ---------------- per penyakit ----------------
    out["penyakit"] = {}
    out["piramida_risiko"] = {"kelompok": AGE_LABELS, "penyakit": {}}
    asosiasi_hitung = {}
    prev_sg, rr_sg, v_sg = {}, {}, {}

    for nama, (col, usia_lbl) in TARGETS.items():
        sub, y = eligible(nama)
        base = float(y.mean())
        d: dict = {
            "usia_label": usia_lbl,
            "n": int(len(sub)),
            "prevalensi": r2(base, 6),
            "variabel": {},
        }

        for var in NUM:
            lo, hi = sub[var].quantile([0.005, 0.995])
            bins = np.linspace(lo, hi, N_BIN)
            hist = {}
            for kelas, lbl in ((0, "Tidak Berisiko"), (1, "Berisiko")):
                h, _ = np.histogram(sub.loc[y == kelas, var], bins=bins, density=True)
                hist[lbl] = r2(h.tolist(), 6)

            # Desil. duplicates="drop" berarti jumlahnya BELUM TENTU 10:
            # Tinggibadan dicatat kelipatan 5 cm sehingga beberapa batas desil
            # bernilai sama dan runtuh -- tiga dari empat penyakit hanya
            # menghasilkan 9 desil untuk variabel itu. Semua array di bawah
            # diindeks terhadap kat, jadi panjangnya selalu konsisten.
            q = pd.qcut(sub[var], N_DESIL, duplicates="drop")
            kat = q.cat.categories
            n_d = y.groupby(q, observed=True).size().reindex(kat, fill_value=0)
            prev = (y.groupby(q, observed=True).mean() * 100).reindex(kat)
            xpos = sub.groupby(q, observed=True)[var].median().reindex(kat)
            r = float(sub[var].corr(y))

            # Tepi desil disimpan supaya nilai pengguna bisa dipetakan ke
            # desilnya dengan searchsorted, bukan ditebak. Tepi kiri pertama
            # memakai nilai minimum sebenarnya, bukan batas qcut yang sengaja
            # digeser sedikit ke bawah.
            tepi = [float(sub[var].min())] + [float(c.right) for c in kat]

            # Kurva desil per jenis kelamin memakai TEPI YANG SAMA dengan
            # kurva gabungan -- bukan desil yang dihitung ulang per jenis
            # kelamin. Hanya dengan tepi yang sama ketiga garis boleh
            # dibandingkan dalam satu grafik (peragaan perancu 3.10).
            jk_desil = {}
            for s in ("L", "P"):
                msk = sub["Jeniskelamin"].eq(s)
                g = y[msk].groupby(q[msk], observed=True)
                jk_desil[s] = {
                    "n": [int(v) for v in g.size().reindex(kat, fill_value=0)],
                    "prev": r2((g.mean() * 100).reindex(kat).tolist(), 3),
                }

            # Kurva KDE per kelas, di atas rentang x yang sama dengan histogram
            # sehingga keduanya bisa ditumpuk persis. Dihitung pada SELURUH baris
            # yang memenuhi syarat (0,18 detik untuk kelas terbesar) -- tidak
            # disubsampel, karena subsampel 50 ribu menggeser kurva sampai 4,15%
            # dari tinggi puncaknya.
            grid = np.linspace(lo, hi, N_KDE)
            kde = {"grid": r2(grid.tolist(), 3)}
            for kelas, lbl in ((0, "Tidak Berisiko"), (1, "Berisiko")):
                nilai = sub.loc[y == kelas, var].to_numpy(dtype=float)
                if len(nilai) > 2 and float(np.std(nilai)) > 0:
                    kde[lbl] = r2(gaussian_kde(nilai)(grid).tolist(), 6)
                else:
                    kde[lbl] = None      # tidak cukup ragam untuk KDE

            d["variabel"][var] = {
                "bins": r2(bins.tolist(), 3),
                "hist": hist,
                "kde": kde,
                "desil_x": r2(xpos.tolist(), 3),
                "desil_prev": r2(prev.tolist(), 3),
                "desil_n": [int(v) for v in n_d],
                "desil_tepi": r2(tepi, 3),
                "desil_jk": jk_desil,
                "r": r2(r),
                "tafsir": tafsir(r),
                "xlim": [r2(lo, 3), r2(hi, 3)],
            }

        # jenis kelamin
        ps = (y.groupby(sub["Jeniskelamin"], observed=True).mean() * 100)
        d["jenis_kelamin"] = {"prev": {k: r2(v, 3) for k, v in ps.items()},
                              "v": r2(cramers_v(sub["Jeniskelamin"], y))}
        # segmen
        pg = (y.groupby(sub["segmen"], observed=True).mean() * 100)
        d["segmen"] = {"prev": {k: r2(v, 3) for k, v in pg.items()},
                       "v": r2(cramers_v(sub["segmen"], y))}
        # kelompok usia (Bersih B3)
        pu = (y.groupby(sub["Kelompok_Usia"], observed=True).mean() * 100).dropna()
        d["kelompok_usia"] = {"label": [str(k) for k in pu.index],
                              "prev": r2(pu.tolist(), 3)}

        # Piramida terpisah risiko: tiap sel (kelompok usia x jenis kelamin)
        # dipecah menjadi Berisiko / Tidak Berisiko.
        #
        # observed=False WAJIB, kalau tidak pita usia yang kosong hilang; lalu
        # reindex terhadap AGE_LABELS kanonik menjamin urutan dan kedua jenis
        # kelamin selalu ada. Pita yang tidak ditanyai tetap hadir sebagai baris
        # nol, sehingga sumbu y identik untuk keempat penyakit dan tidak
        # melompat saat penyakit diganti di dashboard.
        #
        # Prevalensi per sel SENGAJA tidak disimpan -- figur menghitungnya
        # sendiri dari total dan berisiko, jadi hanya ada satu sumber kebenaran
        # dan tidak ada jalur pembulatan yang bisa berbeda dari kelompok_usia.
        tot = (sub.groupby(["Kelompok_Usia", "Jeniskelamin"], observed=False)
                  .size().unstack(fill_value=0)
                  .reindex(index=AGE_LABELS, columns=["L", "P"], fill_value=0)
                  .fillna(0).astype(int))
        ber = (y.groupby([sub["Kelompok_Usia"], sub["Jeniskelamin"]], observed=False)
                .sum().unstack(fill_value=0)
                .reindex(index=AGE_LABELS, columns=["L", "P"], fill_value=0)
                .fillna(0).astype(int))
        out["piramida_risiko"]["penyakit"][nama] = {
            "usia_label": usia_lbl,
            "ditanya": [bool(v) for v in (tot["L"] + tot["P"] > 0)],
            "L": {"total": tot["L"].tolist(), "berisiko": ber["L"].tolist()},
            "P": {"total": tot["P"].tolist(), "berisiko": ber["P"].tolist()},
        }

        out["penyakit"][nama] = d

        asosiasi_hitung[nama] = ([float(sub[c].corr(y)) for c in NUM]
                                 + [cramers_v(sub[c], y) for c in CAT])
        prev_sg[nama] = pg
        rr_sg[nama] = pg / (base * 100)
        v_sg[nama] = cramers_v(sub["segmen"], y)

    # Disimpan 6 desimal, bukan 4. Dengan 4 desimal terjadi pembulatan ganda:
    # nilai asli 0,093504 -> tersimpan 0,0935 -> ditampilkan 0,093, padahal
    # catatan analisis 3.11 (dibulatkan sekali dari nilai asli) menyebut 0,094.
    out["asosiasi"] = {
        "kolom": NUM + CAT,
        "nilai": {n: r2(v, 6) for n, v in asosiasi_hitung.items()},
    }

    # ---------------- kookurensi penanda ----------------
    # Tiap penyakit ditanyakan pada subpopulasi usia yang berbeda, dan
    # "Tidak Dapat Pertanyaan" berarti PERTANYAANNYA TIDAK DIAJUKAN -- bukan
    # jawaban "tidak". Karena itu tidak ada satu pun denominator yang berlaku
    # untuk keempat penyakit sekaligus.
    #
    # Penyelesaiannya: strata didefinisikan oleh POLA PERTANYAAN YANG DIAJUKAN,
    # bukan oleh pita usia, dan tiap strata menyimpan sendiri berapa pertanyaan
    # yang diterimanya (n_ditanya). Dengan begitu label sumbu pada figur dibaca
    # dari data dan tidak mungkin menulis "dari 4 penyakit" untuk kelompok yang
    # hanya ditanyai 3. Lihat catatan analisis 3.13.
    nama_target = list(TARGETS)
    ditanya = pd.DataFrame({n: df[c].isin(["Berisiko", "Tidak Berisiko"])
                            for n, (c, _) in TARGETS.items()})
    tanda = pd.DataFrame({n: df[c].eq("Berisiko") for n, (c, _) in TARGETS.items()})
    pola = ditanya[nama_target].astype(int).astype(str).agg("".join, axis=1)

    def strata(kode: str) -> dict:
        m = pola.eq(kode)
        nama_l = [n for n, bit in zip(nama_target, kode) if bit == "1"]
        s = tanda.loc[m, nama_l]
        n = int(m.sum())
        k = s.sum(axis=1)
        prev = s.mean()

        # Harapan bila keempat penanda saling bebas (Poisson-binomial).
        # Dipakai sebagai PEMBANDING untuk menunjukkan penanda TIDAK bebas,
        # bukan sebagai model. Digambar sebagai lingkaran berongga.
        dist = np.array([1.0])
        for p_ in prev.to_numpy():
            dist = np.convolve(dist, [1.0 - p_, p_])

        # Siapa yang TIDAK masuk strata ini padahal usianya sama. Angka ini
        # wajib tampil di layar: tanpa itu pembaca mengira strata ini mewakili
        # seluruh pita usianya. Rentang usia diambil DARI DATA, tidak
        # disimpulkan dari gerbang usia -- pola 0001 terlihat seperti "anak"
        # padahal membentang 0-44 tahun.
        umin, umax = int(df.loc[m, "Usia"].min()), int(df.loc[m, "Usia"].max())
        pita = df["Usia"].between(umin, umax)
        keluar = pita & ~m
        return {
            "kode": kode,
            "penyakit": nama_l,
            "n_ditanya": len(nama_l),
            "n": n,
            "usia_min": umin,
            "usia_max": umax,
            "n_pita_usia": int(pita.sum()),
            "cakupan": r2(100.0 * n / int(pita.sum()), 3),
            "prev_strata": {p: r2(prev[p] * 100, 3) for p in nama_l},
            "prev_publikasi": {p: r2(out["penyakit"][p]["prevalensi"] * 100, 3)
                               for p in nama_l},
            "jumlah": [int((k == i).sum()) for i in range(len(nama_l) + 1)],
            "persen": [r2(100.0 * (k == i).sum() / n, 3)
                       for i in range(len(nama_l) + 1)],
            "harapan_bebas": r2((dist * 100).tolist(), 3),
            "pasangan": [[int((s[a] & s[b]).sum()) for b in nama_l] for a in nama_l],
            "keluar": {
                "n": int(keluar.sum()),
                "prev": {p: r2(tanda.loc[keluar & ditanya[p], p].mean() * 100, 3)
                         for p in nama_target},
                "usia_rata": r2(df.loc[keluar, "Usia"].mean(), 1),
            },
        }

    # Hanya 1111 dan 1101 yang digambar. 0001 (TBC saja) degeneratif --
    # "kookurensi" satu pertanyaan hanyalah prevalensi TBC itu sendiri -- jadi
    # ia disebut di kartu kejujuran, bukan di pemilih strata.
    out["kookurensi"] = {
        "urutan_penyakit": nama_target,
        "pola_ditanya": {k: int(v) for k, v in pola.value_counts().items()},
        "strata": [strata("1111"), strata("1101")],
        "n_pola_lain": int((~pola.isin(["1111", "1101", "0001"])).sum()),
    }

    # ---------------- peta panas segmen x penyakit ----------------
    prev_df = pd.DataFrame(prev_sg).reindex(out["segmen_urut"])
    rr_df = pd.DataFrame(rr_sg).reindex(out["segmen_urut"])
    out["heatmap"] = {
        "segmen": out["segmen_urut"],
        "penyakit": list(TARGETS),
        "prevalensi": {s: r2(prev_df.loc[s].tolist(), 3) for s in out["segmen_urut"]},
        "risiko_relatif": {s: r2(rr_df.loc[s].tolist(), 3) for s in out["segmen_urut"]},
        "cramers_v": {n: r2(v) for n, v in v_sg.items()},
    }

    # ---------------- gerbang verifikasi ----------------
    print("\n" + "-" * 78)
    if SUMBER_ACUAN:
        print(f"VERIFIKASI terhadap acuan eksternal -- sumber: {SUMBER_ACUAN}")
    else:
        print("ACUAN EKSTERNAL BELUM ADA untuk wilayah ini.")
        print("Pemeriksaan lapis 1 (terhadap angka terbit) DILEWATI; acuannya")
        print("dibuat dari build ini lalu dipakai menggerbangi build berikutnya.")
        print("Pemeriksaan lapis 2 (identitas internal) tetap berjalan penuh.")
    print("-" * 78)
    gagal = []

    print(f"  {'target':<18} {'kolom':<18} {'hitung':>8} {'acuan':>8}  status")
    for nama, acuan in ACUAN_ASOSIASI.items():
        for kol, hit, ac in zip(NUM + CAT, asosiasi_hitung[nama], acuan):
            ok = abs(round(hit, 3) - ac) <= TOLERANSI
            if not ok:
                gagal.append(f"{nama}/{kol}: {hit:.4f} vs {ac}")
            print(f"  {nama:<18} {kol:<18} {hit:>8.3f} {ac:>8.3f}  {'sama' if ok else 'BEDA'}")

    print()
    for k, ac in ACUAN_PERANCU.items():
        hit = perancu[k]
        ok = abs(round(hit, 3) - ac) <= TOLERANSI
        if not ok:
            gagal.append(f"perancu/{k}: {hit:.4f} vs {ac}")
        print(f"  {k:<24} {hit:>8.3f} {ac:>8.3f}  {'sama' if ok else 'BEDA'}")

    # ---------------- gerbang konsistensi internal (struktur baru) ----------
    # Struktur baru tidak punya angka terbitan untuk hampir semua selnya, jadi
    # yang diuji adalah IDENTITAS: jumlah yang harus kembali ke n yang sudah
    # dilaporkan, prevalensi yang harus dapat dihitung ulang dari dua arah, dan
    # label yang harus cocok dengan struktur yang sudah ada. Semua kegagalan
    # masuk ke daftar `gagal` yang sama, sehingga satu selisih pun tetap
    # membatalkan penulisan analysis.json.
    print("\n" + "-" * 78)
    print("VERIFIKASI KONSISTENSI INTERNAL (struktur baru)")
    print("-" * 78)

    def grup(label: str, hasil: list) -> None:
        buruk = [f"{k} ({d})" for k, ok, d in hasil if not ok]
        for b in buruk:
            gagal.append(f"{label}/{b}")
        status = "sama" if not buruk else "BEDA -> " + "; ".join(buruk)
        print(f"  {label:<44} {len(hasil) - len(buruk):>2}/{len(hasil):<3} {status}")

    def tol_bulat(n: int) -> float:
        """
        Anggaran galat untuk membandingkan jumlah berbobot dengan bilangan
        bulat. 0,5 dari pembulatan bilangan bulatnya sendiri, ditambah
        5e-6*n karena persentase disimpan 3 desimal sehingga tiap baris
        menyumbang galat sampai 0,000005.
        """
        return 0.5 + 5e-6 * n

    # --- piramida risiko ---
    pr = out["piramida_risiko"]
    for nama in TARGETS:
        p = pr["penyakit"][nama]
        d = out["penyakit"][nama]
        tl, tp = p["L"]["total"], p["P"]["total"]
        bl, bp = p["L"]["berisiko"], p["P"]["berisiko"]
        n_pyr = sum(tl) + sum(tp)
        n_ber = sum(bl) + sum(bp)
        idx = {l: i for i, l in enumerate(AGE_LABELS)}

        # P5 -- prevalensi tiap pita dihitung ULANG dari piramida lalu
        # dibandingkan dengan kelompok_usia yang sudah dipakai grafik lain.
        # Ini yang membuat kolom jenis kelamin tertukar atau pita bergeser
        # satu langkah tidak mungkin lolos.
        beda_pita = []
        for lbl, pv in zip(d["kelompok_usia"]["label"], d["kelompok_usia"]["prev"]):
            i = idx[lbl]
            tot_i = tl[i] + tp[i]
            if tot_i == 0:
                beda_pita.append(lbl)
                continue
            if abs((bl[i] + bp[i]) / tot_i * 100 - pv) > TOL_PREV:
                beda_pita.append(lbl)

        hasil = [
            ("P1 jumlah=n", n_pyr == d["n"] and ACUAN_PIRAMIDA_N.get(nama, n_pyr) == n_pyr, str(n_pyr)),
            ("P2 prevalensi", abs(n_ber / n_pyr - d["prevalensi"]) <= TOL_IDENTITAS,
             f"{n_ber / n_pyr:.6f}"),
            ("P3 berisiko<=total",
             all(b <= t for b, t in zip(bl + bp, tl + tp)), ""),
            ("P4 gerbang usia",
             {i for i, v in enumerate(p["ditanya"]) if v} == GERBANG_PITA[nama],
             ""),
            ("P5 prev per pita", not beda_pita, ",".join(beda_pita)),
        ]
        if nama == "TBC":
            # TBC ditanyakan ke semua orang, jadi piramidanya WAJIB sama persis
            # dengan piramida populasi -- identitas lintas struktur yang gratis.
            hasil.append(("P6 = piramida populasi",
                          tl == out["piramida"]["L"] and tp == out["piramida"]["P"],
                          ""))
        grup(f"piramida_risiko/{nama}", hasil)

    # --- desil ---
    for nama in TARGETS:
        d = out["penyakit"][nama]
        for var in NUM:
            v = d["variabel"][var]
            xs, pv, nn, tp_ = (v["desil_x"], v["desil_prev"],
                               v["desil_n"], v["desil_tepi"])
            nd = len(xs)
            bobot = sum(n_i * p_i / 100 for n_i, p_i in zip(nn, pv))
            target = round(d["n"] * d["prevalensi"])

            # D6 -- L + P harus menyusun ulang baris DAN prevalensi gabungan.
            # Toleransinya 2x TOL_PREV: prev L, prev P dan prev gabungan
            # masing-masing sudah dibulatkan 3 desimal.
            beda_jk = []
            for i in range(nd):
                nl = v["desil_jk"]["L"]["n"][i]
                np_ = v["desil_jk"]["P"]["n"][i]
                if nl + np_ != nn[i]:
                    beda_jk.append(f"n{i}")
                    continue
                pl = v["desil_jk"]["L"]["prev"][i] or 0.0
                pp = v["desil_jk"]["P"]["prev"][i] or 0.0
                if nn[i] and abs((nl * pl + np_ * pp) / nn[i] - pv[i]) > 2 * TOL_PREV:
                    beda_jk.append(f"p{i}")

            grup(f"desil/{nama[:12]}/{var[:16]}", [
                ("D1 panjang array",
                 len(pv) == len(nn) == nd and len(tp_) == nd + 1, str(nd)),
                ("D2 jumlah=n", sum(nn) == d["n"], str(sum(nn))),
                ("D3 prev berbobot", abs(bobot - target) <= tol_bulat(d["n"]),
                 f"{bobot:.1f}vs{target}"),
                ("D4 tepi menaik",
                 all(a <= b for a, b in zip(tp_, tp_[1:]))
                 and tp_[0] <= min(xs) and tp_[-1] >= max(xs), ""),
                ("D5 desil tak kosong", min(nn) > 0, str(min(nn))),
                ("D6 L+P=gabungan", not beda_jk, ",".join(beda_jk[:4])),
            ])

    # --- kookurensi ---
    ko = out["kookurensi"]
    grup("kookurensi/global", [
        ("K1 pola=n_total",
         sum(ko["pola_ditanya"].values()) == out["n_total"] and ACUAN_POLA_TOTAL in (None, out["n_total"]),
         str(sum(ko["pola_ditanya"].values()))),
        ("K10 strata+0001+lain=n_total",
         sum(s["n"] for s in ko["strata"]) + ko["pola_ditanya"].get("0001", 0)
         + ko["n_pola_lain"] == out["n_total"], ""),
    ])

    for s in ko["strata"]:
        kode, m = s["kode"], s["n_ditanya"]
        ac = ACUAN_KOOKURENSI.get(kode)
        diag = [s["pasangan"][i][i] for i in range(m)]
        total_penanda = sum(i * j for i, j in enumerate(s["jumlah"]))
        grup(f"kookurensi/{kode}", [
            ("K2 jumlah=n=acuan",
             sum(s["jumlah"]) == s["n"] == ko["pola_ditanya"][kode]
             and (ac is None
                  or (s["n"] == ac["n"] and s["jumlah"] == ac["jumlah"])),
             str(s["n"])),
            # K3 -- total penanda dihitung dua arah: dijumlah per orang, dan
            # dijumlah per penyakit. Keduanya harus sama persis.
            ("K3 penanda dua arah", total_penanda == sum(diag), str(total_penanda)),
            ("K4 pasangan simetris",
             all(s["pasangan"][i][j] == s["pasangan"][j][i]
                 for i in range(m) for j in range(m))
             and all(abs(diag[i] - s["prev_strata"][s["penyakit"][i]] / 100 * s["n"])
                     <= tol_bulat(s["n"]) for i in range(m)), ""),
            ("K5 irisan<=diagonal",
             all(s["pasangan"][i][j] <= min(diag[i], diag[j])
                 for i in range(m) for j in range(m)), ""),
            ("K6 k maksimum", s["jumlah"][m] <= min(diag), str(s["jumlah"][m])),
            ("K7 harapan bebas",
             abs(sum(s["harapan_bebas"]) - 100) <= 0.01
             and abs(sum(i * h for i, h in enumerate(s["harapan_bebas"])) / 100
                     - sum(s["prev_strata"].values()) / 100) <= 1e-3, ""),
            # K8 -- penjaga struktural: strata tidak mungkin membawa penyakit
            # yang tidak pernah ditanyakan kepadanya, dan n_ditanya tidak
            # mungkin dilabel ulang menjadi "dari 4".
            ("K8 n_ditanya=bit aktif",
             m == len(s["penyakit"]) == kode.count("1")
             and all(kode[nama_target.index(p)] == "1" for p in s["penyakit"]), str(m)),
            ("K9 keluar=pita-n",
             s["n"] <= s["n_pita_usia"]
             and s["keluar"]["n"] == s["n_pita_usia"] - s["n"]
             and (ac is None
                  or (s["keluar"]["n"] == ac["keluar_n"]
                      and abs(s["keluar"]["prev"]["TBC"] - ac["keluar_tbc"])
                      <= TOL_PREV)),
             str(s["keluar"]["n"])),
        ])

    # --- lintas struktur ---
    urut_ok = True
    for nama in TARGETS:
        lbl = out["penyakit"][nama]["kelompok_usia"]["label"]
        pos = [AGE_LABELS.index(l) for l in lbl if l in AGE_LABELS]
        if len(pos) != len(lbl) or pos != sorted(pos):
            urut_ok = False
    grup("lintas-struktur", [
        # X1 -- sisi data dari perbaikan sumbu usia. Figur memetakan label ke
        # posisi kanonik; pemeriksaan ini memastikan labelnya memang ada di
        # sana dan sudah urut, sehingga celahnya tertutup dari dua sisi.
        ("X1 label usia kanonik & urut", urut_ok, ""),
        ("X2 kelompok=age_labels", pr["kelompok"] == AGE_LABELS, ""),
        ("X3 age_bins=age_labels+1",
         len(out["age_bins"]) == len(AGE_LABELS) + 1, ""),
    ])

    # Informasi, BUKAN gerbang: desil sengaja tidak dipaksa sama besar.
    # Tinggibadan dibulatkan 5 cm sehingga sebarannya memang timpang, dan itu
    # sifat data, bukan cacat.
    rentang = []
    for nama in TARGETS:
        for var in NUM:
            nn = out["penyakit"][nama]["variabel"][var]["desil_n"]
            rentang.append(100.0 * min(nn) / sum(nn))
    print(f"\n  (info) bagian desil terkecil: {min(rentang):.1f}% - "
          f"{max(rentang):.1f}% dari rata rata merata")

    print("\n" + "=" * 78)
    if gagal:
        print("VERIFIKASI GAGAL:")
        for g in gagal:
            print("  " + g)
        print("analysis.json TIDAK ditulis.")
        print("=" * 78)
        return 1

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    dest = MODEL_DIR / "analysis.json"
    dest.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")

    # Build pertama sebuah wilayah: acuan eksternalnya belum ada, jadi dibuat
    # sekarang dari hasil yang barusan lolos seluruh pemeriksaan identitas.
    # Build berikutnya akan digerbangi terhadap berkas ini, sehingga perubahan
    # tak sengaja pada data atau pipeline tetap ketahuan.
    if SUMBER_ACUAN is None:
        acuan_baru = {
            "asosiasi": {n: [round(v, 3) for v in asosiasi_hitung[n]]
                         for n in TARGETS},
            "perancu": {k: round(v, 3) for k, v in perancu.items()},
            "piramida_n": {n: out["penyakit"][n]["n"] for n in TARGETS},
            "kookurensi": {
                st["kode"]: {
                    "n": st["n"], "jumlah": st["jumlah"],
                    "keluar_n": st["keluar"]["n"],
                    "keluar_tbc": st["keluar"]["prev"]["TBC"],
                }
                for st in out["kookurensi"]["strata"]
            },
            "pola_total": out["n_total"],
            "sumber": f"dibuat otomatis {datetime.now():%Y-%m-%d} dari build pertama",
        }
        (MODEL_DIR / "acuan_analisis.json").write_text(
            json.dumps(acuan_baru, indent=1, ensure_ascii=False), encoding="utf-8")
        print(f"Acuan verifikasi {wilayah} DIBUAT: acuan_analisis.json")
        print("Build berikutnya akan diuji terhadap berkas itu.")

    print(f"BERHASIL -- semua angka {wilayah} lolos pemeriksaan")
    print(f"Tersimpan: {dest}  ({dest.stat().st_size/1024:.0f} KB)")
    print("=" * 78)
    return 0


def main() -> int:
    """Membangun analysis.json untuk setiap wilayah yang datanya sudah ada."""
    print("=" * 78)
    print("BANGUN DATA ANALISIS UNTUK DASHBOARD -- SEMUA WILAYAH")
    print("=" * 78)

    berhasil, dilewati, gagal_w = [], [], []
    for wilayah in cfg.SEMUA_WILAYAH:
        if not (cfg.folder_data(wilayah) / "dataset_master.csv").exists():
            dilewati.append(wilayah)
            print(f"(dilewati) {wilayah}: dataset_master.csv belum ada")
            continue
        if bangun_wilayah(wilayah) == 0:
            berhasil.append(wilayah)
        else:
            gagal_w.append(wilayah)

    print("=" * 78)
    print(f"RINGKASAN: {len(berhasil)} wilayah dibangun "
          f"({', '.join(berhasil) or '-'})")
    if dilewati:
        print(f"           {len(dilewati)} dilewati ({', '.join(dilewati)})")
    if gagal_w:
        print(f"           {len(gagal_w)} GAGAL ({', '.join(gagal_w)})")
    print("=" * 78)
    return 1 if (gagal_w or not berhasil) else 0


if __name__ == "__main__":
    sys.exit(main())
