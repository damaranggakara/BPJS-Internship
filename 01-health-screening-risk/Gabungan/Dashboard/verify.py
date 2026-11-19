"""
Uji mesin prediksi terhadap data asli, untuk SETIAP wilayah.

Seluruh pemeriksaan di bawah dijalankan sekali per wilayah yang modelnya
sudah diekspor (Bantul, Sleman, Gabungan). Mesin prediksinya satu; yang
berbeda hanya kumpulan modelnya, jadi pemeriksaan yang sama harus lulus
di semuanya.

Menjalankan seluruh pemeriksaan pada bagian Verification rencana kerja:
  1. probabilitas predictor.py sama dengan predict_proba pipeline pada baris yang sama
  2. kategori IMT sama dengan Kategori_BMI_WHO8 yang tersimpan di dataset_master.csv
  3. gerbang usia berperilaku benar pada usia 1, 10, 30, dan 50
  4. masukan tidak masuk akal ditolak dengan pesan, bukan diprediksi
  5. kumpulan model sama dengan yang didefinisikan Tinjauan Pustaka 2.1.4
  6. importance SHAP punya sumber mesin, dan penjelasan lokalnya aditif
  7. gerbang usia tepat pada batas 14/15 dan 44/45
  8. teks interpretasi SHAP: satu poin per variabel, saran tidak ganda,
     anak tidak diberi target IMT dewasa, saran terakhir selalu soal dokter

Cara pakai:
    python Gabungan/Dashboard/verify.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import predictor as P  # noqa: E402

DASHBOARD = P.DASHBOARD_DIR
sys.path.insert(0, str(P.BERSAMA))
import konfigurasi as cfg  # noqa: E402

N_SAMPEL = 200

# Diisi ulang tiap wilayah oleh periksa_wilayah().
WILAYAH = None
DATA_DIR = None

lulus = 0
gagal = 0


def cek(nama: str, kondisi: bool, detail: str = "") -> None:
    global lulus, gagal
    if kondisi:
        lulus += 1
        print(f"  LULUS  {nama}")
    else:
        gagal += 1
        print(f"  GAGAL  {nama}   {detail}")




def periksa_wilayah(wilayah: str) -> tuple[int, int]:
    """
    Menjalankan seluruh pemeriksaan untuk SATU wilayah.

    Dijalankan berulang, sekali per wilayah yang modelnya sudah diekspor.
    Pemeriksaan yang sama harus lulus di setiap wilayah -- mesin prediksinya
    satu, hanya modelnya yang berbeda.
    """
    global WILAYAH, DATA_DIR, lulus, gagal
    WILAYAH = wilayah
    DATA_DIR = cfg.folder_data(wilayah)
    lulus, gagal = 0, 0

    def prediksi(*a, **k):
        """P.prediksi untuk wilayah yang sedang diperiksa.

        Ada supaya wilayah tidak perlu diselipkan satu per satu ke delapan
        pemanggilan di bawah -- satu yang terlewat akan diam-diam menguji model
        wilayah lain dan tetap lulus.
        """
        k.setdefault("wilayah", wilayah)
        return P.prediksi(*a, **k)

    print("=" * 78)
    print(f"VERIFIKASI MESIN PREDIKSI -- {wilayah}")
    print("=" * 78)

    master = pd.read_csv(DATA_DIR / "dataset_master.csv")
    meta = P.info_penyakit(wilayah)

    # --------------------------------------------------------------------------
    print(f"\n1. Probabilitas cocok dengan pipeline ({N_SAMPEL} baris acak)")
    # --------------------------------------------------------------------------
    sampel = master.sample(N_SAMPEL, random_state=7)
    beda_maks = 0.0
    n_diuji = 0

    for _, r in sampel.iterrows():
        # Kabupaten asal baris ini. Hanya berarti bagi model Gabungan, tempat
        # "wilayah" menjadi fitur ketujuh; untuk model satu wilayah nilainya
        # diabaikan. dataset_master.csv Gabungan membawa kolomnya.
        asal_baris = r["wilayah"] if "wilayah" in sampel.columns else None

        hasil = prediksi(int(r["Usia"]), r["Jeniskelamin"],
                           float(r["Tinggibadan"]), float(r["Berat Badan"]),
                           r["segmen"], asal=asal_baris)
        if not hasil.valid:
            continue

        baris = pd.DataFrame([{
            "Jeniskelamin": r["Jeniskelamin"], "segmen": r["segmen"],
            "wilayah": asal_baris,
            "Usia": float(r["Usia"]), "Tinggibadan": float(r["Tinggibadan"]),
            "Berat Badan": float(r["Berat Badan"]),
            "IMT_recalculated": P.hitung_imt(float(r["Berat Badan"]),
                                             float(r["Tinggibadan"])),
        }])[P._muat(wilayah)["features"]]

        for h in hasil.penyakit:
            if not h.layak:
                continue
            acuan = float(P._model(wilayah, h.nama).predict_proba(baris)[0, 1])
            beda_maks = max(beda_maks, abs(h.probabilitas - acuan))
            n_diuji += 1

    cek(f"selisih probabilitas maksimum {beda_maks:.2e} pada {n_diuji} prediksi",
        beda_maks < 1e-12, f"beda_maks={beda_maks}")

    # --------------------------------------------------------------------------
    print(f"\n2. Kategori IMT cocok dengan Kategori_BMI_WHO8 tersimpan")
    # --------------------------------------------------------------------------
    cocok = tidak_cocok = 0
    contoh_beda = []

    for _, r in sampel.iterrows():
        hasil = prediksi(int(r["Usia"]), r["Jeniskelamin"],
                           float(r["Tinggibadan"]), float(r["Berat Badan"]),
                           r["segmen"])
        if not hasil.valid:
            continue
        if hasil.kategori_who8 == r["Kategori_BMI_WHO8"]:
            cocok += 1
        else:
            tidak_cocok += 1
            if len(contoh_beda) < 3:
                contoh_beda.append(
                    f"usia {int(r['Usia'])}: dashboard={hasil.kategori_who8} "
                    f"tersimpan={r['Kategori_BMI_WHO8']}")

    cek(f"{cocok} kategori cocok, {tidak_cocok} berbeda",
        tidak_cocok == 0, "; ".join(contoh_beda))

    # --------------------------------------------------------------------------
    print("\n3. Gerbang usia")
    # --------------------------------------------------------------------------
    SEG = P.segmen_tersedia(wilayah)[0]


    def layak_pada(usia: int, tinggi: float, berat: float) -> set[str]:
        h = prediksi(usia, "L", tinggi, berat, SEG)
        assert h.valid, h.error
        return {p.nama for p in h.penyakit if p.layak}


    cek("usia 1  -> hanya TBC", layak_pada(1, 75, 9) == {"TBC"},
        str(layak_pada(1, 75, 9)))
    cek("usia 10 -> hanya TBC", layak_pada(10, 140, 35) == {"TBC"},
        str(layak_pada(10, 140, 35)))
    cek("usia 30 -> Diabetes, Hipertensi, TBC (tanpa Kanker Paru)",
        layak_pada(30, 170, 65) == {"Diabetes Melitus", "Hipertensi", "TBC"},
        str(layak_pada(30, 170, 65)))
    cek("usia 50 -> keempat penyakit", len(layak_pada(50, 170, 65)) == 4,
        str(layak_pada(50, 170, 65)))

    h1 = prediksi(1, "L", 75, 9, SEG)
    cek("usia 1  -> kategori Balita (0-2th)",
        h1.kategori_who8 == P.bs.LABEL_BALITA, h1.kategori_who8)

    # --------------------------------------------------------------------------
    print("\n4. Masukan mustahil ditolak")
    # --------------------------------------------------------------------------
    kasus = [
        ("tinggi 260 cm", (30, "L", 260.0, 70.0, SEG)),
        ("berat 1 kg", (30, "L", 170.0, 1.0, SEG)),
        ("bayi 0 th setinggi 197 cm", (0, "L", 197.0, 8.0, SEG)),
        ("IMT mustahil (150 cm / 250 kg)", (30, "L", 150.0, 250.0, SEG)),
        ("segmen tidak dikenal", (30, "L", 170.0, 70.0, "TIDAK ADA")),
        ("jenis kelamin tidak dikenal", (30, "X", 170.0, 70.0, SEG)),
    ]
    for nama, args in kasus:
        h = prediksi(*args)
        cek(f"{nama} ditolak", (not h.valid) and bool(h.error),
            "diterima padahal seharusnya ditolak")

    # --------------------------------------------------------------------------
    print("\n5. Kasus wajar tetap berjalan")
    # --------------------------------------------------------------------------
    h = prediksi(45, "L", 170, 85, SEG)
    cek("dewasa IMT 29,4 -> valid dan ada hasil", h.valid and len(h.penyakit) == 4)
    # Dibandingkan dengan nilai yang SUDAH dibulatkan, karena itulah yang
    # dilihat model: dataset menyimpan IMT_recalculated dengan .round(2).
    cek("IMT dihitung benar (dibulatkan 2 desimal seperti dataset)",
        abs(h.imt - round(85 / 1.70 ** 2, P.PEMBULATAN_IMT)) < 1e-12, f"{h.imt}")
    cek("IMT > 25 -> Diabetes ditandai Berisiko",
        next(p for p in h.penyakit if p.nama == "Diabetes Melitus").label == "Berisiko")
    cek("tiap hasil layak membawa catatan",
        all(p.catatan for p in h.penyakit if p.layak))

    # --------------------------------------------------------------------------
    print("\n6. Kumpulan model sesuai Tinjauan Pustaka 2.1.4")
    # --------------------------------------------------------------------------
    ALGORITMA_SAH = {"dummy", "logistic", "decision_tree", "xgboost"}
    INFO = P.info_penyakit(wilayah)
    META = P._muat(wilayah)          # `meta` di atas sudah dipakai untuk info_penyakit()

    dipakai = {i["model"] for i in INFO.values()}
    cek("hanya algoritma yang didefinisikan di Bab II yang dipakai",
        dipakai <= ALGORITMA_SAH, f"asing: {sorted(dipakai - ALGORITMA_SAH)}")
    cek("model yang diekspor tidak pernah 'dummy'", "dummy" not in dipakai)

    ringkasan = pd.read_csv(DATA_DIR / "ringkasan_model.csv")
    cek("ringkasan_model.csv memuat keempat algoritma",
        set(ringkasan["Model"].unique()) == ALGORITMA_SAH,
        str(sorted(ringkasan["Model"].unique())))

    for nama, info in INFO.items():
        baris = ringkasan[(ringkasan["Dataset"] == nama)
                          & (ringkasan["Model"] == info["model"])]
        ok = (not baris.empty) and all(
            abs(float(baris.iloc[0][k]) - info["metrik"][k]) < 1e-4
            for k in ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC"])
        cek(f"{nama}: metadata.json cocok dengan ringkasan_model.csv", ok)

        # Model yang diekspor harus F1 tertinggi DI ANTARA MODEL SUNGGUHAN.
        # `dummy` wajib dikecualikan: pada Hipertensi F1-nya 0,7552 -- lebih tinggi
        # daripada xgboost 0,7448 -- dan tanpa pengecualian ini pemeriksaannya
        # justru menuntut dummy diekspor sebagai "model terbaik".
        g = ringkasan[(ringkasan["Dataset"] == nama) & (ringkasan["Model"] != "dummy")]
        cek(f"{nama}: model yang diekspor adalah F1 tertinggi (tanpa dummy)",
            g.loc[g["F1-Score"].idxmax(), "Model"] == info["model"],
            f"diekspor {info['model']}, tertinggi {g.loc[g['F1-Score'].idxmax(), 'Model']}")

        semua = ringkasan[ringkasan["Dataset"] == nama]
        if semua.loc[semua["F1-Score"].idxmax(), "Model"] == "dummy":
            cek(f"{nama}: dummy memang F1 tertinggi keseluruhan, dan tetap tidak dipilih",
                info["model"] != "dummy")

    # --------------------------------------------------------------------------
    print("\n7. SHAP: importance global punya sumber mesin, penjelasan lokal aditif")
    # --------------------------------------------------------------------------
    for nama, info in INFO.items():
        imp = info.get("importansi", {})
        cek(f"{nama}: metadata.json memuat importance SHAP dan gain",
            bool(imp.get("shap")) and bool(imp.get("gain")))
        if imp.get("shap"):
            cek(f"{nama}: SHAP ternormalisasi (jumlah = 1)",
                abs(sum(imp["shap"].values()) - 1.0) < 1e-3,
                f"jumlah {sum(imp['shap'].values()):.6f}")
            cek(f"{nama}: SHAP dikelompokkan ke 6 fitur asli, bukan kolom encoding",
                set(imp["shap"]) == set(META["features"]),
                str(sorted(imp["shap"])))

    # Angka yang dulu diketik ke predictor.py kini harus berasal dari metadata.
    sumber = (DASHBOARD / "predictor.py").read_text(encoding="utf-8")
    for angka in ["0,9990", "0,642", "0,918", "0,547", "0,319",
                  "0.9990", "0.642", "0.918", "0.547", "0.319"]:
        cek(f"predictor.py tidak lagi mengetik importance {angka}",
            angka not in sumber, "angka tanpa sumber mesin muncul kembali")

    # Sifat aditif: dasar + seluruh kontribusi = keluaran model (log-odds).
    h = prediksi(52, "L", 168, 78, SEG)
    for p in [x for x in h.penyakit if x.layak]:
        cek(f"{p.nama}: ada penjelasan lokal per fitur", bool(p.kontribusi),
            "kontribusi kosong")
        if not p.kontribusi:
            continue
        cek(f"{p.nama}: kontribusi mencakup keenam fitur",
            {k for k, _ in p.kontribusi} == set(META["features"]))

        # Aditivitas hanya berlaku pada skala keluaran modelnya sendiri. Pohon
        # sklearn mengeluarkan probabilitas; XGBoost dan regresi logistik
        # mengeluarkan log-odds. Menyamakan keduanya membuat Kanker Paru meleset 0,12.
        cek(f"{p.nama}: skala SHAP dikenali", p.skala in ("probabilitas", "log_odds"),
            f"skala={p.skala!r}")
        total = p.dasar + sum(v for _, v in p.kontribusi)
        prob_shap = total if p.skala == "probabilitas" else 1.0 / (1.0 + math.exp(-total))
        cek(f"{p.nama}: dasar + jumlah SHAP = probabilitas model ({p.skala})",
            abs(prob_shap - p.probabilitas) < 1e-4,
            f"SHAP {prob_shap:.6f} vs model {p.probabilitas:.6f}")

    # --------------------------------------------------------------------------
    print("\n8. Gerbang usia tepat di batasnya")
    # --------------------------------------------------------------------------
    for usia, batas, nama in [(14, 15, "Diabetes Melitus"), (15, 15, "Diabetes Melitus"),
                              (44, 45, "Kanker Paru"), (45, 45, "Kanker Paru")]:
        layak = nama in layak_pada(usia, 170, 65)
        cek(f"usia {usia}: {nama} {'dinilai' if usia >= batas else 'TIDAK dinilai'}",
            layak == (usia >= batas))


    # --------------------------------------------------------------------------
    print("\n6. Interpretasi SHAP otomatis")
    # --------------------------------------------------------------------------
    def teks(usia, jk, tinggi, berat, nama):
        h = prediksi(usia, jk, tinggi, berat, SEG)
        p = next(p for p in h.penyakit if p.nama == nama)
        e, s = P.interpretasi_kontribusi(p, h.imt, h.kategori_who4, usia, jk, SEG)
        return " ".join(e), s

    e, s = teks(55, "P", 155, 85, "Diabetes Melitus")          # obesitas
    cek("obesitas: IMT menaikkan risiko DM + saran turunkan berat",
        "<b>IMT</b> menaikkan" in e and any("turunkan berat" in x for x in s), e)
    cek("saran berat badan tidak tercetak dua kali", len(s) == len(set(s)), str(s))
    e, s = teks(17, "L", 175, 45, "TBC")                       # anak kurus
    cek("anak kurus tidak disebut 'di atas normal'", "di atas normal" not in e, e)
    cek("anak tidak diberi target IMT dewasa", "18,5" not in " ".join(s), str(s))

    h = prediksi(30, "L", 170, 65, SEG)
    for p in (p for p in h.penyakit if p.layak):
        e, s = P.interpretasi_kontribusi(p, h.imt, h.kategori_who4, 30, "L", SEG)
        cek(f"{p.nama}: satu poin per variabel", len(e) == len(p.kontribusi), str(e))
        cek(f"{p.nama}: saran terakhir = perlu ke dokter?",
            s[-1].startswith("<b>Perlu ke dokter"), str(s))
        if all(v < 0 for _, v in p.kontribusi):
            cek(f"{p.nama}: tanpa faktor naik -> hanya saran dokter", len(s) == 1, str(s))

    print(f"\n  {wilayah}: LULUS {lulus}   GAGAL {gagal}")
    return lulus, gagal


def main() -> int:
    print("=" * 78)
    print("VERIFIKASI MESIN PREDIKSI -- SEMUA WILAYAH")
    print("=" * 78)

    tersedia = P.wilayah_tersedia()
    if not tersedia:
        print("Tidak ada model yang sudah diekspor. "
              "Jalankan dahulu: python Gabungan/Dashboard/train_export.py")
        return 1

    total_l = total_g = 0
    per_wilayah = []
    for w in tersedia:
        l, g = periksa_wilayah(w)
        total_l += l
        total_g += g
        per_wilayah.append((w, l, g))

    print("\n" + "=" * 78)
    for w, l, g in per_wilayah:
        print(f"  {w:<10} LULUS {l:>3}   GAGAL {g:>3}")
    print(f"  {'TOTAL':<10} LULUS {total_l:>3}   GAGAL {total_g:>3}")
    print("=" * 78)
    return 1 if total_g else 0


if __name__ == "__main__":
    sys.exit(main())
