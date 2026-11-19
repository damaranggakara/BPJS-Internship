"""
Konfigurasi bersama untuk seluruh wilayah (Bantul, Sleman, Gabungan).

Satu-satunya tempat yang mengetahui DI MANA berkas berada dan BAGAIMANA berkas
mentah tiap wilayah harus dibaca. Sebelum berkas ini ada, keenam notebook
menuliskan sendiri jalur absolut ke folder pengguna, sehingga proyek rusak
di baris pertama begitu foldernya dipindah atau diserahkan ke orang lain.

Cara pakai di notebook (sel pertama):

    import sys
    from pathlib import Path

    AKAR = Path.cwd()
    while not (AKAR / "Bersama").exists():
        AKAR = AKAR.parent
    sys.path.insert(0, str(AKAR / "Bersama"))

    import konfigurasi as cfg
    import bmi_standards as bs
    import viz_style as vz

    WILAYAH = "Bantul"          # atau "Sleman"

PERINGATAN SATU: kedua berkas mentah TIDAK memakai format yang sama.
Bantul berupa UTF-16 dengan pemisah tab, Sleman berupa UTF-8 dengan pemisah
koma. Membaca salah satu dengan argumen milik yang lain menghasilkan
DataFrame satu kolom, bukan galat -- jadi jangan pernah menulis
`pd.read_csv(...)` langsung; pakai `cfg.baca_mentah(wilayah)`.

PERINGATAN DUA: setiap angka prevalensi milik SATU wilayah dan SATU pita usia.
Wilayah tidak boleh dibandingkan tanpa menyebut keduanya.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

__all__ = [
    "AKAR",
    "WILAYAH_DATA",
    "WILAYAH_UTAMA",
    "SEMUA_WILAYAH",
    "TARGETS",
    "DISEASE_TARGETS",
    "TARGET_MAPPING",
    "LABEL_MAP",
    "VALID_LABELS",
    "folder",
    "folder_data",
    "berkas_mentah",
    "baca_mentah",
    "baca_master",
    "baca_dataset",
    "baca_ringkasan",
]

# Akar proyek: folder yang memuat Bersama/, Bantul/, Sleman/, Gabungan/.
AKAR = Path(__file__).resolve().parent.parent


# --------------------------------------------------------------------------
# Wilayah
# --------------------------------------------------------------------------
# "baca" berisi argumen pd.read_csv yang WAJIB dipakai untuk berkas mentah
# wilayah tersebut. Nilainya berbeda dan perbedaannya tidak terlihat dari nama
# berkas -- lihat PERINGATAN SATU pada docstring.
WILAYAH_DATA: dict[str, dict] = {
    "Bantul": {
        "berkas": "Skrining_Bantul_2025.csv",
        "baca": {"encoding": "utf-16", "sep": "\t"},
    },
    "Sleman": {
        "berkas": "Skrining_Sleman_2025.csv",
        "baca": {"encoding": "utf-8", "sep": ","},
    },
}

# Wilayah yang punya berkas mentah sendiri (punya notebook pembersihan).
WILAYAH_UTAMA: list[str] = list(WILAYAH_DATA)

# Ditambah wilayah turunan yang datanya disusun dari gabungan keduanya.
SEMUA_WILAYAH: list[str] = WILAYAH_UTAMA + ["Gabungan"]


# --------------------------------------------------------------------------
# Konstanta target -- sama untuk semua wilayah
# --------------------------------------------------------------------------
TARGETS = [
    "Berisiko Diabetes Melitus",
    "Berisiko Hipertensi",
    "Berisiko Kanker Paru",
    "Berisiko TBC",
]

DISEASE_TARGETS = {
    "diabetes": "Berisiko Diabetes Melitus",
    "hipertensi": "Berisiko Hipertensi",
    "kanker_paru": "Berisiko Kanker Paru",
    "tbc": "Berisiko TBC",
}

TARGET_MAPPING = {"Tidak Berisiko": 0, "Berisiko": 1}

# Salah ketik yang ada di KEDUA ekspor BPJS, bukan hanya Bantul.
LABEL_MAP = {"Tidah Berisiko": "Tidak Berisiko"}
VALID_LABELS = {"Berisiko", "Tidak Berisiko", "Tidak Dapat Pertanyaan"}


# --------------------------------------------------------------------------
# Jalur
# --------------------------------------------------------------------------
def _periksa(wilayah: str, hanya_utama: bool = False) -> str:
    sah = WILAYAH_UTAMA if hanya_utama else SEMUA_WILAYAH
    if wilayah not in sah:
        raise KeyError(
            f"Wilayah {wilayah!r} tidak dikenal. Pilihan: {', '.join(sah)}"
        )
    return wilayah


def folder(wilayah: str) -> Path:
    """Folder wilayah, misalnya <akar>/Bantul."""
    return AKAR / _periksa(wilayah)


def folder_data(wilayah: str) -> Path:
    """Folder keluaran dataset bersih wilayah tersebut."""
    return folder(wilayah) / "Data Setiap Target"


def berkas_mentah(wilayah: str) -> Path:
    """Jalur berkas CSV mentah. Hanya untuk wilayah yang punya ekspor sendiri."""
    _periksa(wilayah, hanya_utama=True)
    return folder(wilayah) / WILAYAH_DATA[wilayah]["berkas"]


# --------------------------------------------------------------------------
# Pembacaan
# --------------------------------------------------------------------------
def baca_mentah(wilayah: str) -> pd.DataFrame:
    """
    Membaca ekspor mentah dengan encoding dan pemisah yang benar untuk
    wilayah tersebut.

    Sanitasi tipis di sini: kolom dipastikan sama persis dengan wilayah lain,
    supaya perbedaan format berkas tidak menjalar menjadi perbedaan analisis.
    Pembersihan yang sesungguhnya tetap di notebook Persiapan Data.
    """
    _periksa(wilayah, hanya_utama=True)
    berkas = berkas_mentah(wilayah)
    if not berkas.exists():
        raise FileNotFoundError(f"Berkas mentah tidak ditemukan:\n  {berkas}")

    df = pd.read_csv(berkas, **WILAYAH_DATA[wilayah]["baca"])

    # Kalau pemisahnya salah, seluruh baris masuk ke satu kolom. Itu tidak
    # memunculkan galat, jadi diperiksa di sini supaya gagal dengan keras.
    if df.shape[1] != 11:
        raise ValueError(
            f"{berkas.name} terbaca {df.shape[1]} kolom, seharusnya 11. "
            "Kemungkinan encoding atau pemisah salah."
        )
    return df


def baca_master(wilayah: str) -> pd.DataFrame:
    """dataset_master.csv wilayah tersebut (hasil notebook Persiapan Data)."""
    return _baca_hasil(wilayah, "dataset_master.csv")


def baca_dataset(wilayah: str, nama: str) -> pd.DataFrame:
    """
    Satu dataset per target, misalnya baca_dataset("Sleman", "tbc").

    Ingat: tiap dataset adalah SUBPOPULASI USIA yang berbeda, karena
    "Tidak Dapat Pertanyaan" adalah gerbang kelayakan, bukan data hilang.
    """
    if nama not in DISEASE_TARGETS:
        raise KeyError(
            f"Dataset {nama!r} tidak dikenal. Pilihan: {', '.join(DISEASE_TARGETS)}"
        )
    return _baca_hasil(wilayah, f"dataset_{nama}.csv")


def baca_ringkasan(wilayah: str) -> pd.DataFrame:
    """ringkasan_model.csv wilayah tersebut -- sumber kebenaran tiap metrik."""
    return _baca_hasil(wilayah, "ringkasan_model.csv")


def _baca_hasil(wilayah: str, nama_berkas: str) -> pd.DataFrame:
    p = folder_data(wilayah) / nama_berkas
    if not p.exists():
        raise FileNotFoundError(
            f"{nama_berkas} belum ada untuk wilayah {wilayah}:\n  {p}\n"
            "Jalankan dahulu notebook wilayah tersebut."
        )
    return pd.read_csv(p)
