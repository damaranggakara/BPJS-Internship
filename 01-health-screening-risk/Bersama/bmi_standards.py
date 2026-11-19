"""
Standar klasifikasi BMI/IMT dan batas plausibilitas antropometri.

Modul ini dipakai bersama oleh (diverifikasi 8 Agustus 2026):
  - Analisis Data/Analisis Data Mentah.ipynb                     (melaporkan pelanggaran batas)
  - Persiapan Data dan Klasifikasi/Persiapan_Data_Revised.ipynb  (menerapkan klasifikasi)
  - Persiapan Data dan Klasifikasi/Klasifikasi BMI.ipynb         (menganalisis klasifikasi)
  - Analisis Data/Analisis Data Bersih.ipynb                     (memakai kategori hasil klasifikasi)

Urutan di atas mengikuti urutan menjalankan notebook. Script penyakitan/Stacked Revisi.ipynb
TIDAK memakai modul ini -- kolom kategori BMI sengaja dikeluarkan dari pemodelan.

Semua ambang batas didefinisikan di satu tempat supaya tidak terjadi divergensi
antar notebook.

SUMBER
------
Tabel dewasa (WHO) dan tabel anak (CDC) diambil dari:
    https://www.calculator.net/bmi-calculator.html

  - Tabel WHO dinyatakan berlaku untuk "both men and women, age 20 or older".
  - Tabel CDC BMI-for-age percentile dinyatakan berlaku untuk usia 2-20 tahun.

CATATAN BATAS USIA
------------------
Kedua tabel di sumbernya sama-sama mencakup usia 20 (WHO: ">= 20", CDC: "2-20"),
sehingga usia 20 tumpang tindih. Proyek ini memutuskan:

    usia  < 2        -> tidak diklasifikasi (lihat LABEL_BALITA)
    2 <= usia <= 20  -> CDC BMI-for-age percentile
    usia  > 20       -> WHO dewasa

Batas ini dikendalikan oleh satu konstanta, CHILD_MAX_AGE.

Standar Indonesia (Kemenkes/IMT) TIDAK diimplementasikan karena tidak ditemukan
sumber yang dapat disitasi pada saat penyusunan. Struktur modul ini memungkinkan
penambahan classify_kemenkes() di kemudian hari tanpa mengubah pemanggilnya.
"""

from __future__ import annotations

import io

import numpy as np
import pandas as pd

__all__ = [
    "SOURCE_URL",
    "CHILD_MIN_AGE",
    "CHILD_MAX_AGE",
    "LABEL_BALITA",
    "WHO_ADULT_BINS",
    "WHO8_TO_WHO4",
    "CDC_CHILD_LABELS",
    "CDC_BMI_REF",
    "SEX_TO_CDC",
    "CHILD_BOUNDS",
    "GLOBAL_BOUNDS",
    "BMI_MIN",
    "BMI_MAX",
    "classify_who_adult",
    "classify_cdc_child",
    "classify_bmi",
    "classify_bmi_series",
    "collapse_who4",
    "apply_child_bounds",
]

SOURCE_URL = "https://www.calculator.net/bmi-calculator.html"

# --------------------------------------------------------------------------
# Batas usia
# --------------------------------------------------------------------------

CHILD_MIN_AGE = 2       # di bawah ini, BMI-for-age tidak berlaku secara medis
CHILD_MAX_AGE = 20      # 2..20 inklusif memakai CDC; > 20 memakai WHO dewasa

LABEL_BALITA = "Balita (0-2th)"


# --------------------------------------------------------------------------
# WHO - dewasa (> CHILD_MAX_AGE)
# --------------------------------------------------------------------------
# Format: (batas_atas_eksklusif, label). np.inf menutup kategori terakhir.
# Sesuai tabel WHO pada SOURCE_URL.

WHO_ADULT_BINS = [
    (16.0, "Severe Thinness"),
    (17.0, "Moderate Thinness"),
    (18.5, "Mild Thinness"),
    (25.0, "Normal"),
    (30.0, "Overweight"),
    (35.0, "Obese Class I"),
    (40.0, "Obese Class II"),
    (np.inf, "Obese Class III"),
]

# Peta 8 kategori WHO -> 4 kategori ringkas, untuk varian model bergranularitas kasar.
WHO8_TO_WHO4 = {
    "Severe Thinness": "Underweight",
    "Moderate Thinness": "Underweight",
    "Mild Thinness": "Underweight",
    "Normal": "Normal",
    "Overweight": "Overweight",
    "Obese Class I": "Obese",
    "Obese Class II": "Obese",
    "Obese Class III": "Obese",
}


# --------------------------------------------------------------------------
# CDC - anak & remaja (CHILD_MIN_AGE..CHILD_MAX_AGE)
# --------------------------------------------------------------------------
# Label diberi awalan "Anak_" supaya tidak bertabrakan dengan label dewasa.
# Tanpa awalan ini, "Overweight" akan berarti dua hal berbeda (BMI 25-30 untuk
# dewasa vs persentil >95 untuk anak) di dalam satu kolom yang sama.

CDC_CHILD_LABELS = {
    "underweight": "Anak_Underweight",
    "healthy": "Anak_Healthy weight",
    "at_risk": "Anak_At risk of overweight",
    "overweight": "Anak_Overweight",
}

# Tabel referensi persentil CDC BMI-for-age (P5 / P85 / P95).
# Sex: 1 = laki-laki (L), 2 = perempuan (P). Usia dalam tahun penuh (2-20).
# Direkonstruksi dari data LMS CDC/NCHS 2000 Growth Charts, diambil pada titik
# tengah tiap tahun usia. Pendekatan tahunan (bukan per bulan) karena kolom
# Usia pada data skrining hanya tersedia dalam tahun bulat.
_CDC_BMI_REF_CSV = """Sex,Usia,P5,P85,P95
1,2,14.55,17.74,18.76
1,3,14.19,17.12,18.0
1,4,13.94,16.86,17.83
1,5,13.79,16.88,18.1
1,6,13.72,17.15,18.7
1,7,13.74,17.61,19.52
1,8,13.85,18.23,20.48
1,9,14.06,18.94,21.53
1,10,14.35,19.72,22.6
1,11,14.73,20.54,23.64
1,12,15.17,21.37,24.63
1,13,15.68,22.19,25.55
1,14,16.22,22.99,26.38
1,15,16.8,23.77,27.15
1,16,17.37,24.52,27.85
1,17,17.93,25.24,28.55
1,18,18.45,25.95,29.27
1,19,18.91,26.66,30.08
1,20,19.14,27.08,30.63
2,2,14.21,17.58,18.64
2,3,13.87,16.96,18.1
2,4,13.62,16.76,18.07
2,5,13.47,16.89,18.46
2,6,13.42,17.29,19.16
2,7,13.47,17.9,20.08
2,8,13.61,18.64,21.15
2,9,13.86,19.47,22.3
2,10,14.18,20.35,23.47
2,11,14.58,21.24,24.61
2,12,15.03,22.1,25.7
2,13,15.51,22.9,26.71
2,14,16.02,23.65,27.63
2,15,16.51,24.31,28.46
2,16,16.97,24.9,29.22
2,17,17.37,25.41,29.92
2,18,17.66,25.86,30.61
2,19,17.81,26.27,31.34
2,20,17.82,26.5,31.8
"""

CDC_BMI_REF = pd.read_csv(io.StringIO(_CDC_BMI_REF_CSV))

SEX_TO_CDC = {"L": 1, "P": 2}


# --------------------------------------------------------------------------
# Batas plausibilitas antropometri
# --------------------------------------------------------------------------
# Batas global longgar, dipakai sebagai saringan pertama untuk semua usia.
GLOBAL_BOUNDS = {"tinggi": (40.0, 250.0), "berat": (2.0, 300.0)}

# Rentang BMI manusia yang masuk akal, dari malnutrisi berat sampai obesitas morbid.
BMI_MIN, BMI_MAX = 8.0, 70.0

# Batas per kelompok usia. Batas global terlalu longgar untuk anak: tinggi 197 cm
# lolos saringan global tetapi mustahil untuk anak usia 0 tahun.
# Format: (usia_min, usia_max_inklusif) -> {"tinggi": (lo, hi), "berat": (lo, hi)}
CHILD_BOUNDS = {
    (0, 1): {"tinggi": (45.0, 95.0), "berat": (2.0, 20.0)},
    (2, 4): {"tinggi": (70.0, 130.0), "berat": (7.0, 40.0)},
    (5, 9): {"tinggi": (90.0, 160.0), "berat": (12.0, 80.0)},
    (10, 14): {"tinggi": (110.0, 190.0), "berat": (20.0, 120.0)},
}


# --------------------------------------------------------------------------
# Klasifikasi - skalar
# --------------------------------------------------------------------------

def classify_who_adult(bmi: float) -> str | float:
    """Klasifikasi WHO 8 kategori untuk dewasa. Mengembalikan NaN bila bmi NaN."""
    if pd.isna(bmi):
        return np.nan
    for upper, label in WHO_ADULT_BINS:
        if bmi < upper:
            return label
    return WHO_ADULT_BINS[-1][1]


def classify_cdc_child(bmi: float, age: float, sex: str) -> str | float:
    """
    Klasifikasi persentil CDC BMI-for-age untuk usia CHILD_MIN_AGE..CHILD_MAX_AGE.

    Label diberi awalan "Anak_" (lihat CDC_CHILD_LABELS).
    """
    if pd.isna(bmi) or pd.isna(age) or pd.isna(sex):
        return np.nan

    sex_code = SEX_TO_CDC.get(sex)
    if sex_code is None:
        return np.nan

    ref = CDC_BMI_REF[
        (CDC_BMI_REF["Sex"] == sex_code) & (CDC_BMI_REF["Usia"] == int(age))
    ]
    if ref.empty:
        return np.nan

    p5, p85, p95 = ref.iloc[0][["P5", "P85", "P95"]]
    if bmi < p5:
        return CDC_CHILD_LABELS["underweight"]
    if bmi < p85:
        return CDC_CHILD_LABELS["healthy"]
    if bmi < p95:
        return CDC_CHILD_LABELS["at_risk"]
    return CDC_CHILD_LABELS["overweight"]


def classify_bmi(bmi: float, age: float, sex: str) -> str | float:
    """
    Dispatcher utama.

        usia  < CHILD_MIN_AGE          -> LABEL_BALITA (sengaja tidak diklasifikasi)
        CHILD_MIN_AGE..CHILD_MAX_AGE   -> CDC persentil (berawalan "Anak_")
        usia  > CHILD_MAX_AGE          -> WHO dewasa (8 kategori)
    """
    if pd.isna(age):
        return np.nan

    if age < CHILD_MIN_AGE:
        # BMI-for-age tidak berlaku secara medis di bawah 2 tahun; WHO
        # merekomendasikan Weight-for-Length. Tabel itu tidak tersedia dengan
        # sumber yang dapat disitasi, jadi kelompok ini tidak diklasifikasi.
        return LABEL_BALITA

    if age <= CHILD_MAX_AGE:
        return classify_cdc_child(bmi, age, sex)

    return classify_who_adult(bmi)


def collapse_who4(label):
    """Ringkas 8 kategori WHO menjadi 4. Label non-WHO diteruskan apa adanya."""
    if pd.isna(label):
        return np.nan
    return WHO8_TO_WHO4.get(label, label)


# --------------------------------------------------------------------------
# Klasifikasi - vektorisasi (untuk dataset ratusan ribu baris)
# --------------------------------------------------------------------------

def classify_bmi_series(
    bmi: pd.Series, age: pd.Series, sex: pd.Series
) -> pd.Series:
    """
    Versi vektorisasi dari classify_bmi, hasilnya identik tetapi jauh lebih cepat
    pada dataset besar.
    """
    bmi = pd.Series(bmi).astype(float)
    age = pd.Series(age).astype(float)
    sex = pd.Series(sex)

    out = pd.Series(np.nan, index=bmi.index, dtype=object)

    is_balita = age < CHILD_MIN_AGE
    is_child = (age >= CHILD_MIN_AGE) & (age <= CHILD_MAX_AGE)
    is_adult = age > CHILD_MAX_AGE

    # --- balita ---
    out[is_balita] = LABEL_BALITA

    # --- dewasa: potong berdasarkan WHO_ADULT_BINS ---
    edges = [-np.inf] + [upper for upper, _ in WHO_ADULT_BINS]
    labels = [label for _, label in WHO_ADULT_BINS]
    adult_cat = pd.cut(
        bmi[is_adult], bins=edges, labels=labels, right=False, ordered=False
    )
    out[is_adult] = adult_cat.astype(object)

    # --- anak: lookup persentil CDC lewat merge ---
    if is_child.any():
        child = pd.DataFrame(
            {
                "bmi": bmi[is_child],
                "Usia": age[is_child].astype("Int64"),
                "Sex": sex[is_child].map(SEX_TO_CDC).astype("Int64"),
            }
        )
        merged = child.merge(CDC_BMI_REF, on=["Sex", "Usia"], how="left")
        merged.index = child.index

        child_label = pd.Series(np.nan, index=child.index, dtype=object)
        known = merged["P5"].notna() & merged["bmi"].notna()

        child_label[known & (merged["bmi"] < merged["P5"])] = CDC_CHILD_LABELS[
            "underweight"
        ]
        child_label[
            known & (merged["bmi"] >= merged["P5"]) & (merged["bmi"] < merged["P85"])
        ] = CDC_CHILD_LABELS["healthy"]
        child_label[
            known & (merged["bmi"] >= merged["P85"]) & (merged["bmi"] < merged["P95"])
        ] = CDC_CHILD_LABELS["at_risk"]
        child_label[known & (merged["bmi"] >= merged["P95"])] = CDC_CHILD_LABELS[
            "overweight"
        ]

        out[is_child] = child_label

    return out


# --------------------------------------------------------------------------
# Batas plausibilitas per usia
# --------------------------------------------------------------------------

def apply_child_bounds(
    df: pd.DataFrame,
    age_col: str = "Usia",
    height_col: str = "Tinggibadan",
    weight_col: str = "Berat Badan",
) -> pd.Series:
    """
    Mengembalikan mask boolean bernilai True untuk baris yang tinggi & beratnya
    MASUK AKAL untuk usianya.

    Baris dengan usia di luar rentang CHILD_BOUNDS (yaitu 15 tahun ke atas)
    selalu bernilai True di sini -- baris tersebut sudah disaring oleh batas
    global GLOBAL_BOUNDS di tahap sebelumnya.

    Dipakai oleh notebook Analisis Data Mentah (untuk melaporkan) dan notebook
    Persiapan Data (untuk membuang).
    """
    age = df[age_col]
    height = df[height_col]
    weight = df[weight_col]

    valid = pd.Series(True, index=df.index)

    for (age_lo, age_hi), bounds in CHILD_BOUNDS.items():
        in_band = age.between(age_lo, age_hi)
        if not in_band.any():
            continue

        h_lo, h_hi = bounds["tinggi"]
        w_lo, w_hi = bounds["berat"]

        plausible = height.between(h_lo, h_hi) & weight.between(w_lo, w_hi)
        valid &= ~in_band | plausible

    return valid
