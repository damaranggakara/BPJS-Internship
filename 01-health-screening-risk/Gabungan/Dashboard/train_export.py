"""
Melatih dan menyimpan model terbaik per penyakit untuk dipakai dashboard.

Memproses SETIAP wilayah yang datanya sudah ada -- Bantul, Sleman, dan Gabungan.
Hasilnya empat .joblib + metadata.json per wilayah, di
Dashboard/models/<wilayah>/. Wilayah yang notebook pemodelannya belum
dijalankan dilewati dengan pesan, bukan menggagalkan skrip.

Skrip ini TIDAK mengulang pencarian hyperparameter. Hyperparameter terbaik
dibaca dari hyperparameter_terpilih.json yang ditulis notebook pemodelan tiap
wilayah, sehingga pelatihan di sini hanya butuh beberapa detik dan tidak ada
angka yang perlu disalin dengan tangan.

Agar model yang diekspor benar-benar identik dengan model yang dilaporkan:
  - pembagian data latih/uji memakai RANDOM_STATE dan test_size yang sama
  - model dilatih HANYA pada bagian latih (80%), sama seperti di notebook
  - setelah dilatih, metrik pada data uji DIBANDINGKAN dengan ringkasan_model.csv

Bila ada satu saja metrik yang menyimpang, skrip berhenti dengan error. Dengan
begitu kesalahan penyalinan hyperparameter tidak mungkin lolos diam-diam.

Cara pakai:
    python Dashboard/train_export.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier
from xgboost import XGBClassifier

from imblearn.over_sampling import SMOTENC
from imblearn.pipeline import Pipeline as ImbPipeline
from imblearn.under_sampling import RandomUnderSampler

# --------------------------------------------------------------------------
# Lokasi -- semuanya relatif terhadap file ini, tidak ada path absolut.
# --------------------------------------------------------------------------
DASHBOARD_DIR = Path(__file__).resolve().parent
# Akar proyek = folder terdekat di atas yang memuat Bersama/ (pola yang sama
# dipakai seluruh notebook), jadi letak folder Dashboard bebas.
AKAR = DASHBOARD_DIR
while not (AKAR / "Bersama").exists():
    AKAR = AKAR.parent
if str(AKAR / "Bersama") not in sys.path:
    sys.path.insert(0, str(AKAR / "Bersama"))
import konfigurasi as cfg  # noqa: E402

# --------------------------------------------------------------------------
# Konfigurasi per wilayah
# --------------------------------------------------------------------------
# Skrip ini memproses SEMUA wilayah yang datanya sudah ada. Konstanta yang
# bergantung wilayah (FEATURES, DATA_DIR, MODEL_DIR, ...) di-set ulang oleh
# siapkan_wilayah() di dalam loop; fungsi-fungsi pembantu membacanya sebagai
# global, persis seperti sebelum skrip ini mendukung banyak wilayah.
RANDOM_STATE = 42
TEST_SIZE = 0.2

NUMERIC_COLS = ["Usia", "Tinggibadan", "Berat Badan", "IMT_recalculated"]
CATEG_DASAR = ["Jeniskelamin", "segmen"]

# Banyaknya baris uji yang dipakai menghitung SHAP global. TreeExplainer sendiri
# cepat; angka ini hanya membatasi memori.
N_SHAP = 20_000

# nama penyakit -> (file dataset, kolom target, label usia, batas usia minimum)
DISEASES = {
    "Diabetes Melitus": ("dataset_diabetes.csv", "Berisiko Diabetes Melitus", "15+", 15),
    "Hipertensi":       ("dataset_hipertensi.csv", "Berisiko Hipertensi", "15+", 15),
    "Kanker Paru":      ("dataset_kanker_paru.csv", "Berisiko Kanker Paru", "45+", 45),
    "TBC":              ("dataset_tbc.csv", "Berisiko TBC", "semua usia", 0),
}

# Nama file keluaran per penyakit.
SLUG = {
    "Diabetes Melitus": "diabetes",
    "Hipertensi": "hipertensi",
    "Kanker Paru": "kanker_paru",
    "TBC": "tbc",
}

# Nama folder model per wilayah.
SLUG_WILAYAH = {"Bantul": "bantul", "Sleman": "sleman", "Gabungan": "gabungan"}

# Diisi ulang tiap wilayah oleh siapkan_wilayah().
WILAYAH = None
DATA_DIR = None
MODEL_DIR = None
CATEG_COLS = list(CATEG_DASAR)
FEATURES = CATEG_COLS + NUMERIC_COLS
IDX_KATEGORIK = [FEATURES.index(c) for c in CATEG_COLS]
HYPERPARAMS = {}
PENYEIMBANG = {}


def siapkan_wilayah(wilayah: str) -> bool:
    """
    Menyiapkan seluruh konstanta untuk satu wilayah.

    Hyperparameter TIDAK lagi diketik ke dalam berkas ini. Ia dibaca dari
    hyperparameter_terpilih.json yang ditulis notebook pemodelan wilayah
    tersebut -- penyalinan manual adalah sumber kesalahan yang tidak terlihat,
    karena nilai yang salah ketik tetap menghasilkan model yang jalan dan hanya
    metriknya yang diam-diam berbeda. Kebenarannya tetap dijamin oleh tahap
    verifikasi terhadap ringkasan_model.csv di bawah.

    Mengembalikan False bila data wilayah ini belum ada, supaya wilayah yang
    notebooknya belum dijalankan dilewati alih-alih menggagalkan seluruh skrip.
    """
    global WILAYAH, DATA_DIR, MODEL_DIR
    global CATEG_COLS, FEATURES, IDX_KATEGORIK, HYPERPARAMS, PENYEIMBANG

    data_dir = cfg.folder_data(wilayah)
    hp_path = data_dir / "hyperparameter_terpilih.json"
    if not (data_dir / "ringkasan_model.csv").exists() or not hp_path.exists():
        return False

    WILAYAH = wilayah
    DATA_DIR = data_dir
    MODEL_DIR = DASHBOARD_DIR / "models" / SLUG_WILAYAH[wilayah]

    # Model gabungan memakai satu fitur kategorik tambahan: wilayah asal.
    CATEG_COLS = list(CATEG_DASAR) + (["wilayah"] if wilayah == "Gabungan" else [])
    FEATURES = CATEG_COLS + NUMERIC_COLS
    IDX_KATEGORIK = [FEATURES.index(c) for c in CATEG_COLS]

    hp = json.loads(hp_path.read_text(encoding="utf-8"))
    if hp.get("fitur") and sorted(hp["fitur"]) != sorted(FEATURES):
        raise SystemExit(
            f"{wilayah}: daftar fitur di {hp_path.name} tidak cocok.\n"
            f"  json  : {sorted(hp['fitur'])}\n"
            f"  skrip : {sorted(FEATURES)}")

    HYPERPARAMS = {n: (v["model_terbaik"], v["params"])
                   for n, v in hp["penyakit"].items()}
    PENYEIMBANG = {n: v["penyeimbang"] for n, v in hp["penyakit"].items()}
    return True


# Selisih maksimum yang masih dianggap sama saat verifikasi.
TOLERANSI = 1e-4


def build_preprocessor() -> ColumnTransformer:
    """Sama persis dengan build_preprocessor() di notebook."""
    return ColumnTransformer([
        ("num", StandardScaler(), NUMERIC_COLS),
        ("cat", OneHotEncoder(handle_unknown="ignore", drop="first",
                              sparse_output=False), CATEG_COLS),
    ])


def kelompok_fitur(nama_kolom: str) -> str:
    """"cat__segmen_BP PN" -> "segmen".  Sama persis dengan notebook Bagian 7."""
    if nama_kolom.startswith("num__"):
        return nama_kolom[len("num__"):]
    sisa = nama_kolom[len("cat__"):]
    for c in CATEG_COLS:
        if sisa.startswith(c + "_"):
            return c
    return sisa


def build_estimator(model_key: str, params: dict, penyeimbang: str | None,
                    pos_weight: float) -> Pipeline:
    """
    Membangun pipeline dengan hyperparameter yang sudah pasti.

    Penanganan ketimpangan mengikuti pilihan Bagian 4a notebook. Resampler selalu
    menjadi langkah pertama, sebelum ColumnTransformer -- SMOTENC butuh kolom
    kategorik yang masih berupa teks, dan langkah sampler otomatis dilewati saat
    predict sehingga data uji tidak tersentuh.
    """
    pakai_bobot = penyeimbang == "class_weight"
    bobot = "balanced" if pakai_bobot else None
    spw = pos_weight if pakai_bobot else 1.0

    if model_key == "logistic":
        clf = LogisticRegression(max_iter=1000, random_state=RANDOM_STATE,
                                 class_weight=bobot, **params)
    elif model_key == "decision_tree":
        clf = DecisionTreeClassifier(random_state=RANDOM_STATE,
                                     class_weight=bobot, **params)
    elif model_key == "xgboost":
        clf = XGBClassifier(objective="binary:logistic", eval_metric="logloss",
                            tree_method="hist", random_state=RANDOM_STATE,
                            n_jobs=1, scale_pos_weight=spw, **params)
    else:
        raise ValueError(f"model_key tidak didukung di sini: {model_key}")

    langkah = []
    if penyeimbang == "smote":
        langkah.append(("smote", SMOTENC(categorical_features=IDX_KATEGORIK,
                                         random_state=RANDOM_STATE)))
    elif penyeimbang == "undersample":
        langkah.append(("under", RandomUnderSampler(random_state=RANDOM_STATE)))
    langkah += [("pre", build_preprocessor()), ("clf", clf)]

    Pipe = ImbPipeline if penyeimbang in ("smote", "undersample") else Pipeline
    return Pipe(langkah)


def importansi(pipe: Pipeline, X_te: pd.DataFrame) -> dict:
    """
    Importance per fitur ASLI, dari dua sudut sekaligus.

    Keduanya dijumlahkan kembali per fitur asli lebih dulu: setelah One-Hot
    Encoding `segmen` pecah menjadi 6 kolom, dan tanpa penjumlahan itu ia tampak
    jauh lebih kecil daripada pengaruh sebenarnya (catatan analisis 3.9).

    Nilai-nilai inilah yang dibaca predictor.py, menggantikan angka yang dulu
    diketik langsung ke dalam kode dan tidak punya sumber mesin (catatan analisis 7.19).
    """
    pre, clf = pipe.named_steps["pre"], pipe.named_steps["clf"]
    kolom = list(pre.get_feature_names_out())
    X_enc = pd.DataFrame(pre.transform(X_te[FEATURES]), columns=kolom).head(N_SHAP)

    hasil: dict = {}

    # --- gain / koefisien: apa yang dilaporkan model tentang dirinya sendiri ---
    if hasattr(clf, "feature_importances_"):
        mentah = np.asarray(clf.feature_importances_, dtype=float)
    else:                                        # regresi logistik
        mentah = np.abs(np.asarray(clf.coef_, dtype=float).ravel())
    g = pd.Series(mentah, index=kolom).groupby(kelompok_fitur).sum()
    hasil["gain"] = {k: round(float(v), 6) for k, v in (g / g.sum()).items()}

    # --- SHAP: seberapa besar pengaruh tiap fitur pada prediksi peserta nyata ---
    if hasattr(clf, "coef_"):
        explainer = shap.LinearExplainer(clf, X_enc)
    else:
        explainer = shap.TreeExplainer(clf)
    nilai = explainer(X_enc).values
    if nilai.ndim == 3:                          # (n, fitur, kelas)
        nilai = nilai[:, :, 1]
    s = pd.Series(np.abs(nilai).mean(axis=0), index=kolom).groupby(kelompok_fitur).sum()
    hasil["shap"] = {k: round(float(v), 6) for k, v in (s / s.sum()).items()}

    hasil["teratas_gain"] = max(hasil["gain"], key=hasil["gain"].get)
    hasil["teratas_shap"] = max(hasil["shap"], key=hasil["shap"].get)
    hasil["n_shap"] = int(len(X_enc))
    return hasil


def aturan_imt(df: pd.DataFrame, target: str) -> dict:
    """
    P(Berisiko | IMT > 25) pada peserta dewasa -- bukti bahwa label Diabetes
    pada dasarnya adalah aturan ambang IMT, bukan penilaian klinis
    (catatan analisis 3.2). Dihitung dari data, bukan diketik.
    """
    dewasa = df[df["Usia"] > 20]
    atas = dewasa[dewasa["IMT_recalculated"] > 25]
    if len(atas) == 0:
        return {}
    p = float(atas[target].mean())
    return {
        "p": round(p, 6),
        "n": int(len(atas)),
        "pengecualian": int((atas[target] == 0).sum()),
    }


def metrik(y_true, y_pred, y_prob) -> dict:
    """Lima metrik yang sama dengan yang dilaporkan notebook."""
    return {
        "Accuracy": accuracy_score(y_true, y_pred),
        "Precision": precision_score(y_true, y_pred, zero_division=0),
        "Recall": recall_score(y_true, y_pred, zero_division=0),
        "F1-Score": f1_score(y_true, y_pred, zero_division=0),
        "ROC-AUC": roc_auc_score(y_true, y_prob),
    }


def proses_wilayah(wilayah: str) -> int:
    print("\n" + "=" * 78)
    print(f"EKSPOR MODEL UNTUK DASHBOARD -- WILAYAH {wilayah.upper()}")
    print("=" * 78)

    if not DATA_DIR.exists():
        print(f"\nGAGAL: folder dataset tidak ditemukan:\n  {DATA_DIR}")
        return 1

    ringkasan_path = DATA_DIR / "ringkasan_model.csv"
    if not ringkasan_path.exists():
        print(f"\nGAGAL: {ringkasan_path.name} tidak ditemukan. "
              "Jalankan Stacked Revisi.ipynb terlebih dahulu.")
        return 1

    ringkasan = pd.read_csv(ringkasan_path)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    metadata = {
        "dibuat": datetime.now().isoformat(timespec="seconds"),
        "random_state": RANDOM_STATE,
        "test_size": TEST_SIZE,
        "features": FEATURES,
        "numeric_cols": NUMERIC_COLS,
        "categ_cols": CATEG_COLS,
        "penyakit": {},
    }

    segmen_values: set[str] = set()
    gagal: list[str] = []

    for nama, (fname, target, usia_label, usia_min) in DISEASES.items():
        model_key, params = HYPERPARAMS[nama]
        print(f"\n{'-' * 78}\n{nama}  |  {model_key}  |  usia {usia_label}\n{'-' * 78}")

        df = pd.read_csv(DATA_DIR / fname)
        X = df.drop(columns=["id", target])
        y = df[target]
        base_rate = float(y.mean())
        segmen_values.update(X["segmen"].dropna().unique().tolist())

        # Pembagian identik dengan notebook.
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE)

        penyeimbang = PENYEIMBANG[nama]
        pakai_bobot = penyeimbang == "class_weight"
        pos_w = float((y_tr == 0).sum() / max((y_tr == 1).sum(), 1))
        print(f"  prevalensi {base_rate*100:.2f}%  |  ketimpangan: "
              f"{penyeimbang or 'tanpa penanganan (kelas positif mayoritas)'}")

        # Aturan bawaan notebook: seimbangkan hanya bila kelas positif minoritas.
        # Bila Bagian 4a memilih sesuatu yang lain, PENYEIMBANG di atas yang menang,
        # tetapi ketidakcocokannya harus terlihat -- bukan lolos diam-diam.
        if (base_rate < 0.5) != pakai_bobot and penyeimbang is None:
            print(f"  PERINGATAN: prevalensi {base_rate:.3f} tetapi penyeimbang None")

        pipe = build_estimator(model_key, params, penyeimbang, pos_w)
        pipe.fit(X_tr[FEATURES], y_tr)

        prob = pipe.predict_proba(X_te[FEATURES])[:, 1]
        pred = (prob >= 0.5).astype(int)
        hasil = metrik(y_te, pred, prob)

        # --- verifikasi terhadap angka yang dilaporkan ---
        acuan_baris = ringkasan[(ringkasan["Dataset"] == nama)
                                & (ringkasan["Model"] == model_key)]
        if acuan_baris.empty:
            print(f"  GAGAL: {nama}/{model_key} tidak ada di ringkasan_model.csv")
            gagal.append(nama)
            continue

        acuan = acuan_baris.iloc[0]
        print(f"  {'metrik':<12} {'dashboard':>12} {'laporan':>12}   status")
        cocok = True
        for k in ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"]:
            selisih = abs(hasil[k] - float(acuan[k]))
            ok = selisih <= TOLERANSI
            cocok &= ok
            print(f"  {k:<12} {hasil[k]:>12.4f} {float(acuan[k]):>12.4f}   "
                  f"{'sama' if ok else f'BEDA ({selisih:.2e})'}")

        if not cocok:
            gagal.append(nama)
            continue

        out_path = MODEL_DIR / f"model_{SLUG[nama]}.joblib"
        joblib.dump(pipe, out_path)
        print(f"  tersimpan: {out_path.name} "
              f"({out_path.stat().st_size / 1024:.0f} KB)")

        imp = importansi(pipe, X_te)
        sepakat = imp["teratas_gain"] == imp["teratas_shap"]
        print(f"  importance   teratas gain: {imp['teratas_gain']:<18} "
              f"teratas SHAP: {imp['teratas_shap']:<18} "
              f"{'sepakat' if sepakat else 'BEDA (lihat Bagian 7b)'}")

        metadata["penyakit"][nama] = {
            "slug": SLUG[nama],
            "file": out_path.name,
            "target": target,
            "model": model_key,
            "usia_label": usia_label,
            "usia_min": usia_min,
            "prevalensi": round(base_rate, 6),
            "penyeimbang": penyeimbang or "none",
            "pakai_bobot": bool(pakai_bobot),
            "n_latih": int(len(X_tr)),
            "n_uji": int(len(X_te)),
            "metrik": {k: round(v, 6) for k, v in hasil.items()},
            "importansi": imp,
        }

        if nama == "Diabetes Melitus":
            metadata["penyakit"][nama]["aturan_imt"] = aturan_imt(df, target)

    metadata["segmen_values"] = sorted(segmen_values)

    print("\n" + "=" * 78)
    if gagal:
        print("VERIFIKASI GAGAL untuk: " + ", ".join(gagal))
        print("Model TIDAK diekspor untuk penyakit tersebut.")
        print("Periksa hyperparameter_terpilih.json terhadap notebook pemodelan.")
        print("=" * 78)
        return 1

    meta_path = MODEL_DIR / "metadata.json"
    meta_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                         encoding="utf-8")

    print(f"BERHASIL -- keempat model {wilayah} cocok dengan ringkasan_model.csv")
    print(f"Model    : {MODEL_DIR}")
    print(f"Metadata : {meta_path.name}")
    print("=" * 78)
    return 0


def main() -> int:
    """
    Memproses setiap wilayah yang datanya sudah tersedia.

    Wilayah yang notebook pemodelannya belum dijalankan DILEWATI dengan pesan,
    bukan menggagalkan skrip -- supaya Bantul tetap bisa diekspor ulang selagi
    wilayah lain masih dikerjakan. Yang tetap menggagalkan skrip adalah metrik
    yang tidak cocok dengan ringkasan_model.csv.
    """
    print("=" * 78)
    print("EKSPOR MODEL UNTUK DASHBOARD")
    print("=" * 78)

    diproses, dilewati, gagal = [], [], []
    for wilayah in cfg.SEMUA_WILAYAH:
        if not siapkan_wilayah(wilayah):
            dilewati.append(wilayah)
            print(f"\n(dilewati) {wilayah}: ringkasan_model.csv atau "
                  "hyperparameter_terpilih.json belum ada")
            continue
        if proses_wilayah(wilayah) == 0:
            diproses.append(wilayah)
        else:
            gagal.append(wilayah)

    print("\n" + "=" * 78)
    print(f"RINGKASAN: {len(diproses)} wilayah diekspor "
          f"({', '.join(diproses) or '-'})")
    if dilewati:
        print(f"           {len(dilewati)} dilewati ({', '.join(dilewati)})")
    if gagal:
        print(f"           {len(gagal)} GAGAL ({', '.join(gagal)})")
    print("=" * 78)

    if not diproses:
        print("Tidak ada wilayah yang berhasil diekspor.")
        return 1
    return 1 if gagal else 0


if __name__ == "__main__":
    sys.exit(main())
