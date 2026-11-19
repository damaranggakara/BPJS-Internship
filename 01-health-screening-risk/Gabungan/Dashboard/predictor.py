"""
Mesin prediksi dashboard -- seluruh logika ada di sini, tanpa satu pun elemen UI.

Dipakai bersama oleh app_tkinter.py dan app_streamlit.py supaya kedua antarmuka
tidak mungkin memberi hasil yang berbeda.

Aturan penting yang ditegakkan modul ini:

1. GERBANG USIA. Tiap model hanya berlaku pada rentang usia yang dilatihkan
   (Diabetes & Hipertensi 15+, Kanker Paru 45+, TBC semua usia). Di luar rentang
   itu model TIDAK dijalankan sama sekali -- bukan dijalankan lalu disembunyikan.
   Label "Tidak Dapat Pertanyaan" pada data asli berarti responden tidak memenuhi
   syarat usia untuk ditanyai, bukan data hilang.

2. VALIDASI TUBUH. Tinggi, berat, dan IMT hasil hitungan harus masuk akal, dan
   untuk anak dipakai batas per kelompok usia. Ambangnya diambil dari
   bmi_standards.py, tidak ditulis ulang di sini.

3. KETERUSTERANGAN. Tiap hasil membawa catatan tentang keterbatasannya. Lihat
   catatan_penyakit() -- ini bagian dari keluaran, bukan hiasan.

4. TIDAK ADA ANGKA YANG DIKETIK. Setiap angka yang muncul di layar berasal dari
   metadata.json, yang ditulis oleh train_export.py dari data dan model yang
   sebenarnya. Sebelumnya lima nilai importance diketik langsung ke dalam file
   ini tanpa sumber mesin, sehingga pelatihan ulang akan meninggalkannya basi
   tanpa ada yang menangkap (catatan analisis 7.19). Jangan kembalikan pola itu.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

DASHBOARD_DIR = Path(__file__).resolve().parent
# Akar proyek = folder terdekat di atas yang memuat Bersama/ (pola yang sama
# dipakai seluruh notebook), jadi letak folder Dashboard bebas.
AKAR = DASHBOARD_DIR
while not (AKAR / "Bersama").exists():
    AKAR = AKAR.parent
ROOT = AKAR                             # nama lama, dipakai verify.py
BERSAMA = AKAR / "Bersama"              # bmi_standards + konfigurasi
MODEL_ROOT = DASHBOARD_DIR / "models"   # berisi satu subfolder per wilayah

# Nama folder model per wilayah. Urutannya menentukan urutan pemilih di UI.
SLUG_WILAYAH = {"Bantul": "bantul", "Sleman": "sleman", "Gabungan": "gabungan"}

# bmi_standards.py dan konfigurasi.py ada di Bersama/ pada akar proyek.
if str(BERSAMA) not in sys.path:
    sys.path.insert(0, str(BERSAMA))

import bmi_standards as bs  # noqa: E402

AMBANG = 0.5  # ambang probabilitas untuk melabeli "Berisiko"


# --------------------------------------------------------------------------
# Struktur hasil
# --------------------------------------------------------------------------

@dataclass
class HasilPenyakit:
    nama: str
    layak: bool                     # memenuhi syarat usia?
    alasan: str = ""                # diisi bila tidak layak
    probabilitas: float | None = None
    label: str = ""                 # "Berisiko" / "Tidak Berisiko"
    model: str = ""
    usia_label: str = ""
    metrik: dict = field(default_factory=dict)
    catatan: list[str] = field(default_factory=list)
    # Penjelasan lokal SHAP: [(fitur asli, kontribusi bertanda), ...] urut dari
    # yang paling berpengaruh. Positif mendorong ke "Berisiko", negatif menjauh.
    kontribusi: list[tuple[str, float]] = field(default_factory=list)
    dasar: float | None = None      # base value: prediksi rata-rata populasi
    # Skala nilai SHAP: "probabilitas" (pohon sklearn) atau "log_odds" (XGBoost,
    # regresi logistik). Sifat aditif hanya berlaku PADA SKALA INI, jadi setiap
    # pemeriksaan penjumlahan wajib membacanya lebih dulu.
    skala: str = ""


@dataclass
class HasilPrediksi:
    valid: bool
    error: str = ""
    imt: float | None = None
    kategori_who8: str = ""
    kategori_who4: str = ""
    usia: int | None = None
    penyakit: list[HasilPenyakit] = field(default_factory=list)


# --------------------------------------------------------------------------
# Pemuatan model (sekali saja, disimpan di cache modul)
# --------------------------------------------------------------------------

# Satu bundel per wilayah: {"meta": ..., "models": {...}, "explainers": {...}}.
# Cache-nya BERKUNCI WILAYAH. Kalau tidak, dashboard akan menampilkan angka
# milik satu wilayah di bawah label wilayah lain -- kesalahan yang tidak
# menimbulkan galat apa pun dan hanya terlihat kalau angkanya diperiksa.
_bundel: dict[str, dict] = {}

# Wilayah yang dipakai bila pemanggil tidak menyebutkannya.
WILAYAH_BAWAAN = "Bantul"


def folder_model(wilayah: str) -> Path:
    return MODEL_ROOT / SLUG_WILAYAH[wilayah]


def wilayah_tersedia() -> list[str]:
    """Wilayah yang modelnya sudah diekspor -- untuk mengisi pemilih wilayah."""
    return [w for w in SLUG_WILAYAH
            if (folder_model(w) / "metadata.json").exists()]


def _muat(wilayah: str = WILAYAH_BAWAAN) -> dict:
    """Memuat metadata dan keempat model satu wilayah. Aman dipanggil berulang."""
    if wilayah in _bundel:
        return _bundel[wilayah]["meta"]

    if wilayah not in SLUG_WILAYAH:
        raise KeyError(f"Wilayah {wilayah!r} tidak dikenal. "
                       f"Pilihan: {', '.join(SLUG_WILAYAH)}")

    model_dir = folder_model(wilayah)
    meta_path = model_dir / "metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(
            f"metadata.json untuk wilayah {wilayah} tidak ditemukan di "
            f"{model_dir}.\n"
            "Jalankan terlebih dahulu:  python Gabungan/Dashboard/train_export.py"
        )

    import joblib  # diimpor di sini supaya modul ringan bila hanya butuh IMT

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    models = {nama: joblib.load(model_dir / info["file"])
              for nama, info in meta["penyakit"].items()}
    _bundel[wilayah] = {"meta": meta, "models": models, "explainers": {}}
    return meta


def _model(wilayah: str, nama: str):
    _muat(wilayah)
    return _bundel[wilayah]["models"][nama]


def segmen_tersedia(wilayah: str = WILAYAH_BAWAAN) -> list[str]:
    """Daftar nilai segmen yang dikenal model -- untuk mengisi dropdown."""
    return list(_muat(wilayah)["segmen_values"])


# --------------------------------------------------------------------------
# Penjelasan lokal (SHAP) -- Tinjauan Pustaka 2.1.6
# --------------------------------------------------------------------------

# Explainer disimpan per wilayah di dalam _bundel, bukan di sini -- satu cache
# global akan mencampur explainer milik model wilayah yang berbeda.

# Nama fitur sebagaimana ditulis di layar.
LABEL_FITUR = {
    "IMT_recalculated": "IMT",
    "Usia": "Usia",
    "Tinggibadan": "Tinggi badan",
    "Berat Badan": "Berat badan",
    "Jeniskelamin": "Jenis kelamin",
    "segmen": "Segmen kepesertaan",
    "wilayah": "Kabupaten",          # hanya ada pada model Gabungan
}


def _kelompok_fitur(nama_kolom: str, categ_cols: list[str]) -> str:
    """"cat__segmen_BP PN" -> "segmen".  Sama persis dengan notebook Bagian 7."""
    if nama_kolom.startswith("num__"):
        return nama_kolom[len("num__"):]
    sisa = nama_kolom[len("cat__"):]
    for c in categ_cols:
        if sisa.startswith(c + "_"):
            return c
    return sisa


def _explainer(wilayah: str, nama: str):
    """TreeExplainer (atau LinearExplainer) per penyakit, dibangun sekali saja."""
    _muat(wilayah)
    cache = _bundel[wilayah]["explainers"]
    if nama in cache:
        return cache[nama]

    import shap  # diimpor di sini supaya modul tetap ringan bila hanya butuh IMT

    clf = _model(wilayah, nama).named_steps["clf"]
    if hasattr(clf, "coef_"):
        # Regresi logistik: TreeExplainer tidak berlaku. Latar belakang berupa
        # vektor nol pada skala terstandardisasi = rata-rata populasi.
        import numpy as np
        latar = np.zeros((1, len(clf.coef_.ravel())))
        cache[nama] = shap.LinearExplainer(clf, latar)
    else:
        cache[nama] = shap.TreeExplainer(clf)
    return cache[nama]


def kontribusi_lokal(nama: str, baris,
                     wilayah: str = WILAYAH_BAWAAN
                     ) -> tuple[list[tuple[str, float]], float, str]:
    """
    Kenapa peserta INI diprediksi begitu.

    Mengembalikan (daftar kontribusi per fitur asli, nilai dasar, skala).

    Nilai SHAP dijumlahkan per fitur asli -- `segmen` pecah menjadi 6 kolom
    setelah encoding, dan tanpa penjumlahan itu pengaruhnya tampak jauh lebih
    kecil daripada yang sebenarnya (catatan analisis 3.9). Penjumlahan tidak merusak
    sifat aditif SHAP: dasar + seluruh kontribusi tetap sama dengan keluaran
    model.

    PENTING -- skalanya berbeda antar jenis model, dan ini pernah membuat
    pemeriksaan aditivitas salah:

      - pohon sklearn (DecisionTree, RandomForest) mengeluarkan **probabilitas**
        di daunnya, jadi dasar + kontribusi = probabilitas, langsung.
      - XGBoost dan regresi logistik mengeluarkan **log-odds**, jadi hasil
        penjumlahannya masih perlu dilewatkan fungsi sigmoid.

    Menerapkan sigmoid pada keduanya membuat Kanker Paru meleset 0,12. Skalanya
    dibaca dari `explainer.model.tree_output`, bukan ditebak.
    """
    import numpy as np

    meta = _muat(wilayah)
    pipe = _model(wilayah, nama)
    pre = pipe.named_steps["pre"]
    kolom = list(pre.get_feature_names_out())

    X_enc = pd.DataFrame(pre.transform(baris[meta["features"]]), columns=kolom)
    explainer = _explainer(wilayah, nama)
    sv = explainer(X_enc)

    nilai = sv.values
    dasar = sv.base_values
    if nilai.ndim == 3:                       # (n, fitur, kelas)
        nilai, dasar = nilai[:, :, 1], dasar[:, 1]

    keluaran = getattr(getattr(explainer, "model", None), "tree_output", None)
    skala = "probabilitas" if keluaran == "probability" else "log_odds"

    grup: dict[str, float] = {}
    for k, v in zip(kolom, np.asarray(nilai)[0]):
        asal = _kelompok_fitur(k, meta["categ_cols"])
        grup[asal] = grup.get(asal, 0.0) + float(v)

    urut = sorted(grup.items(), key=lambda kv: abs(kv[1]), reverse=True)
    return urut, float(np.ravel(dasar)[0]), skala


def info_penyakit(wilayah: str = WILAYAH_BAWAAN) -> dict:
    """Metadata per penyakit (model, metrik, gerbang usia)."""
    return dict(_muat(wilayah)["penyakit"])


# --------------------------------------------------------------------------
# Perhitungan dasar
# --------------------------------------------------------------------------

# Notebook Persiapan Data menyimpan IMT_recalculated dengan .round(2), sehingga
# SELURUH model dilatih pada nilai yang sudah dibulatkan dua desimal.
PEMBULATAN_IMT = 2


def hitung_imt(berat_kg: float, tinggi_cm: float) -> float:
    """
    IMT = berat (kg) dibagi kuadrat tinggi (meter), dibulatkan dua desimal.

    Pembulatannya WAJIB, bukan kosmetik. Notebook Persiapan Data menyimpan
    `IMT_recalculated` dengan `.round(2)`, jadi model tidak pernah melihat nilai
    yang tidak dibulatkan. Menghitung IMT penuh presisi di sini berarti memberi
    model masukan yang sedikit berbeda dari data latihnya.

    Selisihnya nyaris selalu tak terlihat, tetapi tepat di ambang kategori ia
    berubah menjadi jawaban yang berbeda. Contoh nyata yang ditemukan
    verify.py: 64 kg pada 160 cm bernilai 25 tepat secara matematis, tetapi
    float64 menghasilkan 24,999999999999996. Tanpa pembulatan, dashboard
    menyebutnya "Normal" sementara dataset menyimpannya sebagai "Overweight" --
    dua jawaban berbeda untuk orang yang sama.
    """
    if tinggi_cm <= 0:
        raise ValueError("Tinggi badan harus lebih besar dari nol.")
    return round(berat_kg / (tinggi_cm / 100.0) ** 2, PEMBULATAN_IMT)


def validasi(usia: int, tinggi_cm: float, berat_kg: float,
             jenis_kelamin: str, segmen: str,
             wilayah: str = WILAYAH_BAWAAN) -> str:
    """
    Mengembalikan pesan error bila masukan tidak masuk akal, atau "" bila lolos.

    Ambang diambil dari bmi_standards.py supaya konsisten dengan tahap
    pembersihan data.
    """
    if jenis_kelamin not in bs.SEX_TO_CDC:
        return (f"Jenis kelamin '{jenis_kelamin}' tidak dikenal. "
                f"Gunakan salah satu dari: {', '.join(bs.SEX_TO_CDC)}.")

    tersedia = segmen_tersedia(wilayah)
    if segmen not in tersedia:
        return (f"Segmen '{segmen}' tidak dikenal model. "
                f"Pilih salah satu dari: {', '.join(tersedia)}.")

    if not (0 <= usia <= 120):
        return "Usia harus berada antara 0 dan 120 tahun."

    t_lo, t_hi = bs.GLOBAL_BOUNDS["tinggi"]
    if not (t_lo <= tinggi_cm <= t_hi):
        return f"Tinggi badan harus antara {t_lo:.0f} dan {t_hi:.0f} cm."

    b_lo, b_hi = bs.GLOBAL_BOUNDS["berat"]
    if not (b_lo <= berat_kg <= b_hi):
        return f"Berat badan harus antara {b_lo:.0f} dan {b_hi:.0f} kg."

    # Batas per kelompok usia -- batas global terlalu longgar untuk anak.
    # Memakai fungsi yang sama dengan notebook persiapan data.
    baris = pd.DataFrame([{
        "Usia": usia, "Tinggibadan": tinggi_cm, "Berat Badan": berat_kg,
    }])
    if not bool(bs.apply_child_bounds(baris).iloc[0]):
        for (lo, hi), batas in bs.CHILD_BOUNDS.items():
            if lo <= usia <= hi:
                th_lo, th_hi = batas["tinggi"]
                bb_lo, bb_hi = batas["berat"]
                return (f"Untuk usia {lo}-{hi} tahun, tinggi wajar "
                        f"{th_lo:.0f}-{th_hi:.0f} cm dan berat "
                        f"{bb_lo:.0f}-{bb_hi:.0f} kg. "
                        "Periksa kembali angka yang dimasukkan.")
        return "Kombinasi usia, tinggi, dan berat tidak masuk akal."

    imt = hitung_imt(berat_kg, tinggi_cm)
    if not (bs.BMI_MIN <= imt <= bs.BMI_MAX):
        return (f"IMT hasil hitungan {imt:.1f} di luar rentang manusia yang "
                f"wajar ({bs.BMI_MIN:.0f}-{bs.BMI_MAX:.0f}). "
                "Periksa kembali tinggi dan berat badan.")

    return ""


# --------------------------------------------------------------------------
# Catatan keterusterangan
# --------------------------------------------------------------------------

def catatan_penyakit(nama: str, info: dict, berisiko: bool) -> list[str]:
    """
    Catatan keterbatasan yang WAJIB ditampilkan bersama tiap hasil.

    Tanpa ini, label "Berisiko" pada Kanker Paru dan TBC menyesatkan: sebagian
    besar orang yang ditandai berisiko sebenarnya tidak berisiko menurut
    kuesioner. Lihat catatan analisis 3.2 dan bagian Keterbatasan Stacked Revisi.
    """
    catatan: list[str] = []
    presisi = info["metrik"]["Precision"]

    # Semua angka di bawah dibaca dari metadata.json -- tidak ada yang diketik.
    shap_imp = info.get("importansi", {}).get("shap", {})

    def besar(fitur: str) -> str:
        v = shap_imp.get(fitur)
        return f" ({v:.3f})".replace(".", ",") if v is not None else ""

    if nama == "Diabetes Melitus":
        aturan = info.get("aturan_imt", {})
        p = f" (P = {aturan['p']:.4f})".replace(".", ",") if aturan.get("p") else ""
        catatan.append(
            "Model ini pada dasarnya merekonstruksi aturan kuesioner skrining: "
            f"hampir semua orang dewasa dengan IMT di atas 25 otomatis ditandai "
            f"berisiko{p}. Hasil di bawah lebih tepat dibaca sebagai penerapan "
            "ulang aturan IMT, bukan prediksi penyakit."
        )
    elif nama == "Hipertensi":
        catatan.append(
            f"IMT adalah penentu terbesar{besar('IMT_recalculated')}, tetapi "
            "hubungannya tidak sekaku Diabetes -- masih banyak pengecualian, "
            "sehingga hasilnya benar-benar prediksi, bukan sekadar aturan."
        )
    elif nama == "Kanker Paru":
        catatan.append(
            "Prediksi ini hampir seluruhnya ditentukan jenis kelamin"
            f"{besar('Jeniskelamin')}, yang di sini menjadi proksi kebiasaan "
            "merokok. Status merokok sendiri tidak tersedia dalam data."
        )
    elif nama == "TBC":
        catatan.append(
            f"Penentu terbesar adalah usia{besar('Usia')}, disusul segmen "
            f"kepesertaan{besar('segmen')} sebagai proksi kondisi sosial ekonomi. "
            "Tidak ada satu pun ciri yang menjelaskan TBC dengan kuat -- inilah "
            "sebabnya model TBC paling lemah di antara keempatnya."
        )

    if berisiko and presisi < 0.5:
        n = round(presisi * 100)
        catatan.append(
            f"PENTING: dari 100 orang yang ditandai BERISIKO oleh model ini, "
            f"hanya sekitar {n} yang benar-benar berisiko menurut kuesioner. "
            "Hasil ini jauh lebih berguna sebagai penyaring awal daripada "
            "sebagai kesimpulan."
        )

    return catatan


def interpretasi_kontribusi(p: HasilPenyakit, imt: float, kategori_who4: str,
                            usia: int, jenis_kelamin: str, segmen: str
                            ) -> tuple[list[str], list[str]]:
    """
    Membaca bar SHAP menjadi kalimat: (daftar penjelasan, daftar saran).

    Pangsa dihitung sama persis dengan theme.bar_kontribusi supaya angka di
    teks cocok dengan angka di grafik. Setiap ciri mendapat satu poin; saran
    hanya lahir dari ciri yang menaikkan risiko, dan saran terakhir selalu
    menjawab "perlu ke dokter atau tidak".

    "Alasan" di sini adalah alasan medis yang lazim untuk pola yang dipelajari
    model, bukan klaim sebab-akibat dari SHAP: SHAP menjelaskan model, bukan
    tubuh peserta.
    """
    if not p.kontribusi:
        return [], []

    total = sum(abs(v) for _, v in p.kontribusi) or 1.0
    # Label anak berbentuk "Anak_Underweight", "Anak_Healthy weight", dst.
    anak = kategori_who4.startswith("Anak_")
    kat = kategori_who4.removeprefix("Anak_")
    kurus = "Underweight" in kat
    normal = kat in ("Normal", "Healthy weight")
    gemuk = any(k in kat for k in ("Overweight", "Obese"))   # termasuk "At risk of overweight"
    imt_teks = f"IMT Anda {imt:.1f} ({kat})".replace(".", ",")
    jk_teks = "laki-laki" if jenis_kelamin == "L" else "perempuan"
    target_imt = ("berat badan sesuai kurva pertumbuhan anak" if anak
                  else "IMT normal 18,5-24,9")

    # Kaitan medis IMT -> penyakit. Hanya ditulis bila memang ada dasarnya;
    # selain itu teksnya jujur menyebut ini pola di data, bukan sebab.
    MEKANISME_GEMUK = {
        "Diabetes Melitus": "Kelebihan lemak tubuh memicu resistensi insulin, "
                            "sehingga gula darah sulit dikendalikan.",
        "Hipertensi": "Kelebihan berat badan menambah beban kerja jantung dan "
                      "menaikkan tekanan pada pembuluh darah.",
    }
    MEKANISME_KURUS = {
        "TBC": "Kekurangan gizi melemahkan daya tahan tubuh, sehingga lebih rentan "
               "terhadap infeksi kuman TBC.",
    }
    MEKANISME_USIA = {
        "Diabetes Melitus": "kemampuan tubuh mengolah gula menurun",
        "Hipertensi": "pembuluh darah makin kaku",
        "Kanker Paru": "paparan zat berbahaya seperti asap rokok dan polusi menumpuk",
        "TBC": "daya tahan tubuh terhadap infeksi menurun",
    }
    pola_data = (f"Di data skrining, nilai seperti ini lebih sering ditandai berisiko "
                 f"{p.nama}, meski secara medis kaitannya tidak langsung.")

    # Untuk saran penutup "perlu ke dokter?": (pemeriksaan, gejala waspada).
    DOKTER = {
        "Diabetes Melitus": ("pemeriksaan gula darah (puasa atau HbA1c)",
                             "sering haus, sering buang air kecil, mudah lapar, "
                             "atau luka yang sulit sembuh"),
        "Hipertensi": ("pengukuran tekanan darah",
                       "sakit kepala berat, tengkuk terasa tegang, atau pusing"),
        "Kanker Paru": ("pemeriksaan paru (rontgen dada bila diperlukan)",
                        "batuk lama, batuk berdarah, sesak napas, atau nyeri dada"),
        "TBC": ("pemeriksaan dahak (gratis di Puskesmas)",
                "batuk lebih dari 2 minggu, demam, berkeringat malam, atau berat "
                "badan turun tanpa sebab"),
    }

    def alasan(fitur: str, naik: bool) -> tuple[str, str | None]:
        """(alasan, saran atau None) untuk satu ciri pada arah tertentu."""
        # IMT dan berat badan berbagi saran yang SAMA supaya tidak tercetak dua kali.
        if fitur in ("IMT_recalculated", "Berat Badan"):
            if not naik:
                return (f"{imt_teks} berada pada rentang yang lebih menguntungkan "
                        f"dibanding peserta lain untuk {p.nama}.", None)
            if kurus:
                return (f"{imt_teks} tergolong kurus. "
                        + MEKANISME_KURUS.get(p.nama, pola_data),
                        "Perbaiki asupan gizi (protein, sayur, buah) untuk mencapai "
                        f"{target_imt}; konsultasikan ke tenaga gizi di Puskesmas "
                        "bila berat badan terus turun.")
            if gemuk:
                langkah = ("atur pola makan dan ajak anak aktif bergerak minimal 60 "
                           "menit per hari; konsultasikan ke Puskesmas" if anak else
                           "turunkan berat badan bertahap (5-10% dalam 6 bulan) "
                           "dengan pola makan seimbang, kurangi gula dan gorengan, "
                           "dan aktivitas fisik minimal 150 menit per minggu")
                return (f"{imt_teks} di atas normal. "
                        + MEKANISME_GEMUK.get(p.nama, pola_data),
                        f"Menuju {target_imt}: {langkah}.")
            if normal:
                return (f"{imt_teks} masih dalam rentang normal, tetapi model "
                        "membacanya sedikit ke arah berisiko.",
                        "Pertahankan berat badan Anda dan jaga agar tidak naik.")
            return (f"{imt_teks}. {pola_data}", None)   # balita: kategori tak berlaku
        if fitur == "Usia":
            if not naik:
                return (f"Usia {usia} tahun termasuk kelompok dengan risiko "
                        f"{p.nama} lebih rendah dibanding rata-rata peserta.", None)
            return (f"Usia {usia} tahun berada pada kelompok yang lebih sering "
                    f"berisiko {p.nama}. Seiring bertambahnya usia, "
                    f"{MEKANISME_USIA.get(p.nama, 'risiko penyakit kronis meningkat')}.",
                    "Usia tidak bisa diubah, jadi lakukan skrining kesehatan rutin "
                    "minimal setahun sekali lewat BPJS di FKTP Anda.")
        if fitur == "Tinggibadan":
            if not naik:
                return ("Tinggi badan Anda, dalam kombinasi dengan berat badan, "
                        "sedikit menurunkan risiko menurut model.", None)
            return ("Tinggi badan memengaruhi model lewat perhitungan IMT dan "
                    "proporsi tubuh.", None)   # tidak bisa diubah, tidak ada saran
        if fitur == "Jeniskelamin":
            if p.nama == "Kanker Paru":
                if not naik:
                    return (f"Sebagai {jk_teks}, Anda termasuk kelompok yang lebih "
                            "jarang merokok di data, sehingga risiko turun.", None)
                return (f"Sebagai {jk_teks}, Anda termasuk kelompok dengan kebiasaan "
                        "merokok lebih tinggi di data; jenis kelamin di sini menjadi "
                        "proksi merokok.",
                        "Status merokok adalah faktor yang bisa Anda ubah: berhenti "
                        "merokok menurunkan risiko kanker paru secara nyata.")
            return (f"Jenis kelamin ({jk_teks}) {'menaikkan' if naik else 'menurunkan'}"
                    f" risiko karena pola {p.nama} berbeda antara laki-laki dan "
                    "perempuan di data skrining.", None)
        if fitur == "segmen":
            if not naik:
                return (f"Segmen {segmen} memiliki angka {p.nama} lebih rendah "
                        "di data skrining.", None)
            return (f"Segmen {segmen} memiliki angka {p.nama} lebih tinggi di data. "
                    "Segmen menjadi proksi kondisi sosial ekonomi, seperti kepadatan "
                    "hunian dan akses layanan kesehatan.",
                    "Manfaatkan layanan skrining dan pemeriksaan gratis BPJS di "
                    "FKTP tempat Anda terdaftar.")
        if fitur == "wilayah":   # hanya ada pada model Gabungan
            return (f"Peserta dari kabupaten skrining ini {'lebih' if naik else 'kurang'} "
                    f"sering ditandai berisiko {p.nama} di data.", None)
        return (f"{LABEL_FITUR.get(fitur, fitur)} "
                f"{'menaikkan' if naik else 'menurunkan'} risiko.", None)

    penjelasan: list[str] = []
    saran: list[str] = []

    for fitur, nilai in p.kontribusi:
        naik = nilai >= 0
        pangsa = abs(nilai) / total * 100
        label = LABEL_FITUR.get(fitur, fitur)
        if pangsa < 0.5:
            penjelasan.append(f"<b>{label}</b> hampir tidak memengaruhi risiko "
                              f"(&lt;1%).")
            continue
        teks, s = alasan(fitur, naik)
        sama = [x for x in penjelasan if teks in x]     # IMT & berat badan
        if sama:
            teks = f"Alasannya sama dengan poin {sama[0].split('</b>')[0][3:]}."
        arah = "menaikkan" if naik else "menurunkan"
        penjelasan.append(f"<b>{label}</b> {arah} risiko ({pangsa:.0f}%). {teks}")
        if naik and s and s not in saran:
            saran.append(s)

    # Penutup wajib: perlu ke dokter atau tidak, mengikuti label model.
    periksa, gejala = DOKTER.get(p.nama, ("pemeriksaan lebih lanjut",
                                          "keluhan yang tidak biasa"))
    if p.label == "Berisiko":
        saran.append(f"<b>Perlu ke dokter: ya.</b> Hasil Anda <i>Berisiko</i> "
                     f"{p.nama}, jadi sebaiknya temui dokter di Puskesmas/FKTP untuk "
                     f"{periksa}. Hasil ini bukan diagnosis; pemeriksaan dokterlah "
                     "yang memastikannya.")
    else:
        saran.append(f"<b>Perlu ke dokter: belum perlu</b> khusus untuk {p.nama}; "
                     "cukup skrining rutin. Namun segera temui dokter bila muncul "
                     f"{gejala}.")

    return penjelasan, saran


DISCLAIMER = (
    "Dashboard ini memperkirakan penanda risiko pada kuesioner skrining BPJS, "
    "BUKAN diagnosis medis. Faktor risiko terpenting -- riwayat keluarga, status "
    "merokok, tekanan darah, lingkar perut, dan aktivitas fisik -- tidak tersedia "
    "dalam data sehingga tidak diperhitungkan. Untuk kepastian, periksakan diri "
    "ke tenaga kesehatan."
)


# --------------------------------------------------------------------------
# Prediksi
# --------------------------------------------------------------------------

def prediksi(usia: int, jenis_kelamin: str, tinggi_cm: float,
             berat_kg: float, segmen: str,
             wilayah: str = WILAYAH_BAWAAN,
             asal: str | None = None) -> HasilPrediksi:
    """
    Menghitung IMT, mengkategorikannya, lalu memprediksi risiko untuk setiap
    penyakit yang syarat usianya terpenuhi.

    `wilayah` memilih KUMPULAN MODEL yang dipakai ("Bantul", "Sleman", atau
    "Gabungan"). `asal` adalah kabupaten tempat peserta diskrining, dan hanya
    berarti bagi model Gabungan -- di sanalah `wilayah` menjadi fitur ketujuh.
    Untuk model satu wilayah, `asal` diabaikan karena modelnya memang hanya
    pernah melihat satu kabupaten.
    """
    meta = _muat(wilayah)

    pesan = validasi(usia, tinggi_cm, berat_kg, jenis_kelamin, segmen, wilayah)
    if pesan:
        return HasilPrediksi(valid=False, error=pesan)

    imt = hitung_imt(berat_kg, tinggi_cm)
    who8 = bs.classify_bmi(imt, usia, jenis_kelamin)
    who4 = bs.collapse_who4(who8)

    # Satu baris masukan; nama kolom harus persis sama dengan saat pelatihan.
    # Kolom "wilayah" selalu disiapkan, lalu pemilihan meta["features"] di
    # bawahlah yang menentukan apakah ia benar-benar dipakai -- sehingga model
    # enam fitur dan model tujuh fitur ditangani jalur kode yang sama.
    asal_dipakai = asal or (wilayah if wilayah != "Gabungan" else "Bantul")
    baris = pd.DataFrame([{
        "Jeniskelamin": jenis_kelamin,
        "segmen": segmen,
        "wilayah": asal_dipakai,
        "Usia": float(usia),
        "Tinggibadan": float(tinggi_cm),
        "Berat Badan": float(berat_kg),
        "IMT_recalculated": float(imt),
    }])[meta["features"]]

    hasil: list[HasilPenyakit] = []

    for nama, info in meta["penyakit"].items():
        usia_min = info["usia_min"]

        if usia < usia_min:
            hasil.append(HasilPenyakit(
                nama=nama, layak=False, usia_label=info["usia_label"],
                model=info["model"], metrik=info["metrik"],
                alasan=(f"Tidak ditampilkan: pertanyaan {nama} hanya diajukan "
                        f"pada usia {usia_min} tahun ke atas, sehingga model "
                        f"tidak pernah dilatih untuk usia {usia} tahun."),
            ))
            continue

        prob = float(_model(wilayah, nama).predict_proba(baris)[0, 1])
        berisiko = prob >= AMBANG

        # Penjelasan lokal tidak boleh menjatuhkan prediksi kalau SHAP gagal --
        # angka prediksinya tetap sah tanpa penjelasan.
        try:
            kontrib, dasar, skala = kontribusi_lokal(nama, baris, wilayah)
        except Exception:
            kontrib, dasar, skala = [], None, ""

        hasil.append(HasilPenyakit(
            nama=nama, layak=True, probabilitas=prob,
            label="Berisiko" if berisiko else "Tidak Berisiko",
            model=info["model"], usia_label=info["usia_label"],
            metrik=info["metrik"],
            catatan=catatan_penyakit(nama, info, berisiko),
            kontribusi=kontrib, dasar=dasar, skala=skala,
        ))

    return HasilPrediksi(
        valid=True, imt=imt, kategori_who8=str(who8), kategori_who4=str(who4),
        usia=usia, penyakit=hasil,
    )
