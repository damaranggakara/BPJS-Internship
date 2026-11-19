"""
Dashboard Prediksi Risiko Penyakit Kronis -- antarmuka web (Streamlit).

Seluruh logika ada di predictor.py; berkas ini hanya menampilkan. Gaya visual
ada di theme.py.

PENTING: setiap angka yang tampil di layar berasal dari
models/<wilayah>/metadata.json
lewat predictor.py. Deck presentasi BPJS hanya dipakai sebagai acuan VISUAL --
isinya sudah tidak sesuai dengan analisis terkini.

Cara pakai:
    streamlit run Dashboard/app_streamlit.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analysis as A  # noqa: E402
import predictor as P  # noqa: E402
import theme as T  # noqa: E402

st.set_page_config(page_title="Prediksi Risiko Penyakit Kronis",
                   page_icon="🩺", layout="wide",
                   initial_sidebar_state="expanded")

st.markdown(T.css(), unsafe_allow_html=True)
HTML = dict(unsafe_allow_html=True)


@st.cache_resource
def muat(wilayah: str):
    """
    Model dan metadata satu wilayah.

    PENTING: wilayah HARUS menjadi argumen, bukan dibaca dari luar. Kalau tidak,
    st.cache_resource akan mengembalikan hasil wilayah yang pertama dimuat untuk
    semua wilayah berikutnya -- angka Bantul akan tampil di bawah label Sleman
    tanpa galat apa pun.
    """
    return P.segmen_tersedia(wilayah), P.info_penyakit(wilayah)


@st.cache_resource
def muat_analisis(wilayah: str):
    """
    Angka tab Analisis, dihitung sekali oleh build_analysis.py.
    Mengembalikan None bila belum dibangun -- tab lain tetap berfungsi.
    """
    import json
    p = (Path(__file__).resolve().parent / "models"
         / P.SLUG_WILAYAH[wilayah] / "analysis.json")
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


WILAYAH_ADA = P.wilayah_tersedia()
if not WILAYAH_ADA:
    st.error("Belum ada model yang diekspor. Jalankan terlebih dahulu:\n\n"
             "    python Gabungan/Dashboard/train_export.py")
    st.stop()

KETERANGAN_WILAYAH = {
    "Bantul": "Model dilatih hanya pada data skrining Kabupaten Bantul.",
    "Sleman": "Model dilatih hanya pada data skrining Kabupaten Sleman.",
    "Gabungan": ("Model dilatih pada data kedua kabupaten sekaligus, dengan "
                 "kabupaten asal sebagai salah satu fitur."),
}


# --------------------------------------------------------------------------
# Pita kategori IMT -- menyesuaikan usia
# --------------------------------------------------------------------------
def pita_imt(usia: int, jenis_kelamin: str):
    """
    Mengembalikan (daftar_pita, keterangan) atau (None, keterangan).

    Ambang dewasa TIDAK berlaku untuk anak: usia 2-20 memakai persentil CDC yang
    bergeser tiap tahun usia, dan di bawah 2 tahun IMT-menurut-usia tidak berlaku
    secara medis. Menampilkan skala dewasa untuk anak akan salah.
    """
    if usia < P.bs.CHILD_MIN_AGE:
        return None, ("IMT-menurut-usia tidak berlaku secara medis di bawah 2 tahun, "
                      "sehingga kategori dan skala tidak ditampilkan. WHO menganjurkan "
                      "Weight-for-Length untuk kelompok usia ini.")

    if usia <= P.bs.CHILD_MAX_AGE:
        sex = P.bs.SEX_TO_CDC.get(jenis_kelamin)
        ref = P.bs.CDC_BMI_REF[(P.bs.CDC_BMI_REF["Sex"] == sex)
                               & (P.bs.CDC_BMI_REF["Usia"] == int(usia))]
        if ref.empty:
            return None, "Tabel persentil CDC tidak tersedia untuk usia ini."
        p5, p85, p95 = (float(ref.iloc[0][k]) for k in ("P5", "P85", "P95"))
        pita = [(10.0, p5, "Underweight"), (p5, p85, "Healthy"),
                (p85, p95, "At risk"), (p95, float("inf"), "Overweight")]
        ket = (f"Skala persentil CDC untuk anak usia {usia} tahun "
               f"({'laki-laki' if jenis_kelamin == 'L' else 'perempuan'}). "
               f"Ambangnya bergeser setiap tahun usia, jadi berbeda dari ambang dewasa.")
        return pita, ket

    pita = [(12.0, 18.5, "Underweight"), (18.5, 25.0, "Normal"),
            (25.0, 30.0, "Overweight"), (30.0, float("inf"), "Obese")]
    return pita, ("Skala WHO untuk dewasa (di atas 20 tahun). Kategori rinci "
                  "(8 tingkat) ada di tab Informasi.")


# --------------------------------------------------------------------------
# Sidebar
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="label-kecil">Wilayah</div>', **HTML)
    wilayah = st.selectbox(
        "Kumpulan model", WILAYAH_ADA,
        index=len(WILAYAH_ADA) - 1,      # Gabungan bila sudah ada
        help="Menentukan model DAN seluruh angka analisis yang ditampilkan.")
    st.caption(KETERANGAN_WILAYAH[wilayah])

    # Model Gabungan memakai kabupaten asal sebagai fitur ketujuh, jadi di sana
    # -- dan hanya di sana -- kabupaten peserta harus ditanyakan.
    asal = None
    if wilayah == "Gabungan":
        asal = st.radio("Kabupaten tempat skrining", ["Bantul", "Sleman"],
                        horizontal=True)

    # Dimuat SETELAH wilayah dipilih, karena daftar segmen dan seluruh angka
    # di layar berasal dari wilayah tersebut.
    try:
        SEGMEN, INFO = muat(wilayah)
    except FileNotFoundError as e:
        st.error(str(e))
        st.stop()
    ANALISIS = muat_analisis(wilayah)

    st.markdown('<div class="label-kecil">Data Diri</div>', **HTML)

    jk = st.radio("Jenis kelamin", ["L", "P"], horizontal=True,
                  format_func=lambda x: "Laki-laki" if x == "L" else "Perempuan")
    usia = st.number_input("Usia (tahun)", min_value=0, max_value=120, value=30, step=1)
    tinggi = st.number_input("Tinggi badan (cm)", min_value=40.0, max_value=250.0,
                             value=170.0, step=0.5)
    berat = st.number_input("Berat badan (kg)", min_value=2.0, max_value=300.0,
                            value=65.0, step=0.5)
    segmen = st.selectbox("Segmen kepesertaan BPJS", SEGMEN)
    # Jangan sebut segmen "penentu terbesar risiko TBC" di sini: menurut SHAP
    # penentu terbesarnya adalah usia, dan kartu TBC di sebelah kanan menampilkan
    # justru itu -- dua pernyataan yang bertentangan di satu layar.
    st.caption("Segmen dibutuhkan model, dan termasuk penentu risiko TBC.")

    hitung = st.button("Hitung Risiko", type="primary", use_container_width=True)

st.markdown(T.header(
    "Dashboard Prediksi Risiko Penyakit Kronis",
    f"Skrining {wilayah} 2025 · berbasis data skrining kesehatan BPJS"),
    **HTML)

tab_hasil, tab_skrining, tab_penyakit, tab_info = st.tabs(
    ["Hasil Prediksi", "Analisis Skrining", "Analisis per Penyakit", "Informasi"])


def _tampilkan(wadah, fig) -> None:
    """
    Menggambar figur matplotlib lalu menutupnya.

    use_container_width=True DISENGAJA di sini: gambar menyesuaikan lebar kolom
    sehingga tepi kanannya rata dengan teks. Itu berbeda dari figur histogram di
    tab per penyakit, yang memakai False karena ukurannya sudah menyentuh batas
    1460 px milik Streamlit dan akan diregangkan bila dibiarkan melar.
    """
    wadah.pyplot(fig, use_container_width=True)
    A.plt.close(fig)


def _angka(n) -> str:
    """Pemisah ribuan gaya Indonesia: 131768 -> 131.768."""
    return f"{int(n):,}".replace(",", ".")


def _pita_usia(a: dict, usia: int) -> str:
    """
    Kelompok usia milik seseorang, dicari lewat age_bins dari analysis.json.

    Tepi pitanya sengaja TIDAK disalin ke sini. Dua salinan konstanta yang sama
    adalah cara paling umum keduanya jadi berbeda diam-diam.
    """
    i = max(j for j, b in enumerate(a["age_bins"][:-1]) if usia >= b)
    return a["age_labels"][min(i, len(a["age_labels"]) - 1)]


# "Usia" sengaja TIDAK ditawarkan pada kurva desil tab Skrining. Piramida
# terpisah risiko tepat di atasnya sudah menjawab pertanyaan yang sama -- risiko
# menurut usia -- dan menjawabnya lebih baik: per pita DAN per jenis kelamin,
# dengan prevalensi tercetak di ujung tiap batang. Kurva desil Usia hanya
# mengulanginya dengan sumbu yang lebih kasar.
#
# Tab per penyakit TETAP menawarkan keempat variabel: di sana Usia menjawab
# pertanyaan lain, yaitu BENTUK sebaran kedua kelas (histogram + KDE), bukan
# tren risikonya.
#
# Disaring dari a["num_cols"], BUKAN ditulis ulang sebagai daftar baru: bila
# build_analysis.py menambah variabel numerik, variabel itu ikut muncul di sini.
VAR_DESIL_LEWAT = {"Usia"}

# Kata bilangan tingkat, supaya kalimat tetap wajar baik untuk 3 maupun 4
# pertanyaan. Angkanya SELALU dibaca dari sk["n_ditanya"], tidak pernah diketik:
# strata 1101 hanya menerima tiga pertanyaan, sehingga "Keempat jawaban" di sana
# salah -- persis kesalahan yang gerbang K8 di build_analysis.py ada untuk
# mencegah, tetapi K8 tidak bisa melihatnya karena angkanya diketik di tampilan,
# bukan disimpan di data.
URUTAN_ID = {2: "Kedua", 3: "Ketiga", 4: "Keempat"}


def _kontras_jumlah_prevalensi(a: dict, penyakit: str = "TBC"):
    """
    Mencari sepasang kelompok usia yang membuktikan bahwa MENGHITUNG orang bukan
    MENGUKUR risiko: kelompok A punya lebih banyak kasus daripada kelompok B,
    tetapi prevalensinya justru LEBIH RENDAH.

    Dihitung dari piramida_risiko, tidak diketik. Contoh yang dipakai
    catatan analisis 3.12 (65-74 = 11,71% vs 75+ = 8,02%) TIDAK selamat dari
    pembinan ulang menjadi delapan pita: kedua pita itu melebur menjadi "65+",
    dan di dalam delapan pita ini jumlah kasus TBC DAN prevalensinya sama-sama
    memuncak di 55-64 lalu turun. Kalimat lama karena itu salah di layar.

    Pasangan dipilih dengan memaksimalkan (kasus_A/kasus_B) x (prev_B/prev_A)
    supaya yang tampil adalah kontras TERKUAT, bukan yang pertama ditemukan.
    Mengembalikan None bila tidak ada pasangan yang memenuhi -- kalimatnya lalu
    tidak dicetak sama sekali, bukan dicetak dengan angka karangan.
    """
    p = a["piramida_risiko"]["penyakit"][penyakit]
    kel = a["piramida_risiko"]["kelompok"]
    baris = []
    for i, lbl in enumerate(kel):
        tot = p["L"]["total"][i] + p["P"]["total"][i]
        ber = p["L"]["berisiko"][i] + p["P"]["berisiko"][i]
        if tot > 0 and ber > 0:
            baris.append((lbl, ber, ber / tot * 100))

    terbaik = None
    for la, ka, pa in baris:
        for lb, kb, pb in baris:
            if ka > kb and pa < pb:
                skor = (ka / kb) * (pb / pa)
                if terbaik is None or skor > terbaik[0]:
                    terbaik = (skor, la, ka, pa, lb, kb, pb)
    return None if terbaik is None else terbaik[1:]


# --------------------------------------------------------------------------
# TAB 1 -- Hasil
# --------------------------------------------------------------------------
def _interpretasi_html(p, hasil, usia: int, jk: str, segmen: str) -> str:
    """Teks otomatis di bawah bar SHAP: penjelasan tiap ciri lalu saran."""
    penjelasan, saran = P.interpretasi_kontribusi(
        p, hasil.imt, hasil.kategori_who4, usia, jk, segmen)
    if not penjelasan:
        return ""
    li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
    html = (f'<div class="label-kecil" style="margin-top:14px;">Interpretasi</div>'
            f'<div style="font-size:.84rem;color:{T.TINTA};line-height:1.55;">'
            f'Berdasarkan hasil tersebut:<ul style="margin:4px 0 0 18px;padding:0;">'
            f'{li(penjelasan)}</ul></div>')
    if saran:
        html += (f'<div class="catatan"><b>Saran untuk Anda:</b>'
                 f'<ul style="margin:4px 0 0 18px;padding:0;">{li(saran)}</ul></div>')
    return html


def tampilkan_hasil(hasil, usia: int, jk: str, segmen: str) -> None:
    """Menggambar seluruh isi tab Hasil untuk satu prediksi yang valid."""
    layak = [p for p in hasil.penyakit if p.layak]
    tidak = [p for p in hasil.penyakit if not p.layak]
    pita, ket_pita = pita_imt(int(usia), jk)

    # --- ringkasan ---
    # Satu grid HTML, bukan st.columns, supaya kartu menyusun ulang sendiri
    # pada layar sempit (lihat .strip-statistik di theme.py).
    st.markdown(
        '<div class="strip-statistik">'
        + T.kartu_statistik("Indeks Massa Tubuh", f"{hasil.imt:.1f}",
                            "berat / tinggi kuadrat")
        + T.kartu_statistik("Kategori", hasil.kategori_who8,
                            f"ringkas: {hasil.kategori_who4}", teks=True)
        + T.kartu_statistik("Usia", f"{int(usia)}",
                            "tahun — menentukan model yang berlaku")
        + T.kartu_statistik("Penyakit Dinilai", f"{len(layak)}",
                            "dari 4, sesuai syarat usia")
        + "</div>", **HTML)

    # --- skala IMT ---
    st.markdown(T.judul_bagian("Posisi IMT Anda", ket_pita), **HTML)
    if pita:
        st.markdown(T.skala_imt(hasil.imt, pita), **HTML)
    else:
        st.markdown(f'<div class="kartu kartu-redup"><div style="font-size:.86rem;'
                    f'color:{T.ABU_TUA};">{ket_pita}</div></div>', **HTML)

    # --- hasil per penyakit ---
    st.markdown(T.judul_bagian(
        "Hasil Prediksi Risiko",
        "Panjang bar menunjukkan skor risiko Anda untuk tiap penyakit."), **HTML)

    for p in layak:
        berisiko = p.label == "Berisiko"
        m = p.metrik
        prevalensi = INFO[p.nama]["prevalensi"]
        warna = T.warna_status(berisiko)

        catatan_html = "".join(
            f'<div class="catatan-penting">{c}</div>' if c.startswith("PENTING")
            else f'<div class="catatan"><b>Catatan:</b> {c}</div>'
            for c in p.catatan)

        # Penjelasan lokal SHAP -- kenapa peserta INI mendapat angka itu.
        if p.kontribusi:
            kontribusi_html = (
                '<div class="label-kecil" style="margin-top:14px;">'
                'Apa yang membentuk angka ini</div>'
                + T.bar_kontribusi(p.kontribusi, P.LABEL_FITUR)
                + '<div class="catatan" style="margin-top:2px;">'
                'Dihitung dengan <b>SHAP</b>: seberapa jauh tiap ciri Anda menggeser '
                'prediksi dari rata-rata populasi, dan ke arah mana. Angkanya adalah '
                'pangsa tiap ciri terhadap total pergeseran itu, sehingga selalu '
                'berjumlah 100%. Ini penjelasan untuk <i>satu</i> orang — bukan '
                'tingkat kepentingan fitur pada model secara umum.</div>'
                + _interpretasi_html(p, hasil, usia, jk, segmen))
        else:
            kontribusi_html = ""

        st.markdown(f"""
<div class="kartu">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;">
    <div>
      <div class="nama-penyakit">{p.nama}</div>
      <div class="meta-model">Model {p.model} · berlaku usia {p.usia_label}</div>
    </div>
    <div style="text-align:right;">
      {T.pil(p.label, berisiko)}
      <div style="font-size:1.7rem;font-weight:700;color:{warna};line-height:1.2;
                  margin-top:6px;">{p.probabilitas * 100:.1f}%</div>
    </div>
  </div>
  {T.bar_probabilitas(p.probabilitas, prevalensi, berisiko)}
  {kontribusi_html}
  <div class="baris-metrik">
    Akurasi {m['Accuracy']:.3f} · Presisi {m['Precision']:.3f} ·
    Recall {m['Recall']:.3f} · F1 {m['F1-Score']:.3f} · ROC-AUC {m['ROC-AUC']:.3f}
  </div>
  {catatan_html}
</div>
""", **HTML)

    # --- tidak berlaku ---
    if tidak:
        st.markdown(T.judul_bagian("Tidak Dinilai",
                                   "Pertanyaan berikut tidak diajukan pada usia Anda, "
                                   "sehingga modelnya tidak dijalankan."), **HTML)
        for p in tidak:
            st.markdown(
                f'<div class="kartu kartu-redup">'
                f'<div style="font-weight:700;color:{T.ABU_TUA};font-size:.95rem;">'
                f'{p.nama}</div>'
                f'<div style="font-size:.82rem;color:{T.ABU_TUA};margin-top:4px;">'
                f'{p.alasan}</div></div>', **HTML)

    st.markdown(f'<div class="catatan-penting">{P.DISCLAIMER}</div>', **HTML)


# st.button hanya bernilai True pada satu kali jalan tepat setelah ditekan.
# Tanpa pengunci ini, hasil hilang begitu pengguna menyentuh widget apa pun
# (termasuk berpindah tab), seolah-olah dashboard mengosongkan dirinya sendiri.
if hitung:
    st.session_state["sudah_hitung"] = True
sudah_hitung = st.session_state.get("sudah_hitung", False)

# Dihitung sekali di sini, di luar blok tab, supaya tab Hasil dan tab Analisis
# memakai hasil yang sama persis dan tidak mungkin berbeda.
_hasil = (P.prediksi(int(usia), jk, float(tinggi), float(berat), segmen,
                    wilayah=wilayah, asal=asal)
          if sudah_hitung else None)
_hasil_valid = _hasil if (_hasil is not None and _hasil.valid) else None


with tab_hasil:
    # Percabangan if/else, BUKAN st.stop(). st.stop() menghentikan SELURUH
    # skrip, sehingga tab Informasi ikut kosong -- padahal justru tab itu yang
    # ingin dibaca orang sebelum menekan Hitung.
    if not sudah_hitung:
        st.markdown(
            f'<div class="kartu"><div class="label-kecil">Mulai</div>'
            f'<div style="color:{T.TINTA};font-size:.92rem;">Isi data diri di panel '
            f'kiri, lalu tekan <b>Hitung Risiko</b>.</div>'
            f'<div class="catatan">Model hanya memakai jenis kelamin, usia, tinggi, '
            f'berat, dan segmen kepesertaan. Penjelasan lengkap ada di tab '
            f'<b>Informasi</b>.</div></div>', **HTML)
    elif _hasil_valid is None:
        st.markdown(
            f'<div class="kartu" style="border-left:4px solid {T.ORANYE};">'
            f'<div class="label-kecil">Masukan belum dapat diproses</div>'
            f'<div style="color:{T.TINTA};font-size:.92rem;">{_hasil.error}</div>'
            f'</div>', **HTML)
    else:
        tampilkan_hasil(_hasil_valid, int(usia), jk, segmen)


# --------------------------------------------------------------------------
# TAB 2 & 3 -- Analisis
# --------------------------------------------------------------------------
def _analisis_belum_siap() -> None:
    st.markdown(
        f'<div class="kartu" style="border-left:4px solid {T.ORANYE};">'
        f'<div class="label-kecil">Data analisis belum tersedia</div>'
        f'<div style="color:{T.TINTA};font-size:.92rem;">Jalankan terlebih dahulu:'
        f'<br><code>python Dashboard/build_analysis.py</code></div></div>', **HTML)


# Nilai pengguna dihitung sekali, dipakai oleh kedua tab analisis.
_punya_nilai = sudah_hitung and _hasil_valid is not None
NILAI_PENGGUNA = ({"Usia": float(usia), "Tinggibadan": float(tinggi),
                   "Berat Badan": float(berat),
                   "IMT_recalculated": _hasil_valid.imt}
                  if _punya_nilai else {})
SEGMEN_PENGGUNA = segmen if _punya_nilai else None
LAYAK_PENGGUNA = ({p.nama for p in _hasil_valid.penyakit if p.layak}
                  if _punya_nilai else set())


with tab_skrining:
    if ANALISIS is None:
        _analisis_belum_siap()
    else:
        a = ANALISIS

        # ---------------- 0. ringkasan populasi ----------------
        # Satu grid HTML, bukan st.columns: kartu menyusun ulang sendiri pada
        # layar sempit (lihat .strip-statistik di theme.py). st.columns(4) tidak
        # pernah melipat, sehingga angkanya patah di layar kecil.
        st.markdown(T.judul_bagian(
            "Profil Populasi Skrining",
            "Siapa yang mengikuti skrining, dan bagaimana risikonya tersebar. "
            "Semua angka berasal dari data yang sudah dibersihkan."), **HTML)

        st.markdown(
            '<div class="strip-statistik">'
            + T.kartu_statistik("Catatan Skrining", _angka(a["n_total"]),
                                "bukan jumlah orang")
            + T.kartu_statistik("Rentang Usia",
                                f"{a['usia_min']}–{a['usia_max']}", "tahun")
            + T.kartu_statistik("Segmen", str(len(a["segmen_urut"])),
                                "kategori kepesertaan")
            + T.kartu_statistik("Penyakit", "4", "target skrining")
            + "</div>", **HTML)

        # ---------------- 1. komposisi peserta ----------------
        c1, c2 = st.columns(2)
        _tampilkan(c1, A.figur_piramida(a))
        _tampilkan(c2, A.figur_komposisi_segmen(a))

        # ---------------- 2. prevalensi menurut kelompok usia ----------------
        _tampilkan(st, A.figur_prevalensi_usia(a))

        # Contoh pembanding dihitung dari data, bukan diketik: pita usia
        # dashboard (delapan) lebih kasar daripada pita notebook, sehingga
        # contoh 65-74 vs 75+ pada catatan analisis 3.12 tidak berlaku di sini.
        _kontras = _kontras_jumlah_prevalensi(a)
        _contoh = ""
        if _kontras is not None:
            la, ka, pa, lb, kb, pb = _kontras
            _contoh = (
                f' Contohnya pada TBC: kelompok <b>{la}</b> mencatat '
                f'<b>{_angka(ka)}</b> kasus sedangkan kelompok <b>{lb}</b> hanya '
                f'<b>{_angka(kb)}</b> — sekitar {ka / kb:.1f} kali lebih banyak — '
                f'padahal risikonya justru <i>lebih rendah</i>, <b>{pa:.2f}%</b> '
                f'berbanding <b>{pb:.2f}%</b>. Yang berbeda di antara keduanya '
                f'bukan risikonya, melainkan besar kelompoknya.')

        st.markdown(
            '<div class="catatan"><b>Catatan:</b> grafik ini memakai <b>prevalensi</b> '
            '(persentase), bukan jumlah kasus. Grafik jumlah akan menyesatkan karena '
            'kelompok usia yang pesertanya banyak otomatis punya kasus banyak.'
            + _contoh +
            ' Perhatikan juga bahwa tiap garis dimulai pada kelompok usia tempat '
            'pertanyaannya <i>mulai diajukan</i> (Diabetes dan Hipertensi 15+, '
            'Kanker Paru 45+, TBC semua usia) — bukan karena prevalensinya nol di '
            'bawah itu.</div>', **HTML)

        # ---------------- 2b. keseimbangan kelas & klasifikasi IMT ----------------
        st.markdown(T.judul_bagian(
            "Keseimbangan Kelas tiap Penyakit",
            "Berapa besar porsi peserta yang ditandai Berisiko pada masing-masing "
            "penyakit."), **HTML)

        skala_kk = st.radio("Skala", [A.SKALA_PERSEN, A.SKALA_JUMLAH],
                            horizontal=True, key="skrining_skala_kelas",
                            label_visibility="collapsed")
        _tampilkan(st, A.figur_keseimbangan_kelas(a, skala_kk))

        st.markdown(
            '<div class="catatan"><b>Kenapa ini penting untuk pemodelan:</b> keempat '
            'penyakit sangat berbeda keseimbangan kelasnya. Hipertensi justru didominasi '
            'kelas <i>Berisiko</i>, sedangkan TBC dan Kanker Paru sangat timpang. Model '
            'yang menebak kelas mayoritas saja sudah mencetak akurasi tinggi pada dua '
            'penyakit terakhir tanpa menemukan satu pun kasus; karena itu akurasi bukan '
            'ukuran yang dipakai, dan penanganan ketimpangan kelas diuji tersendiri di '
            'notebook pemodelan.</div>', **HTML)

        st.markdown(T.judul_bagian(
            "Distribusi Kategori IMT",
            "Sebaran status gizi peserta, dewasa dan anak dihitung dengan standar "
            "yang berbeda."), **HTML)

        _tampilkan(st, A.figur_klasifikasi_bmi(a))

        kb = a["klasifikasi_bmi"]
        st.markdown(
            f'<div class="catatan"><b>Dua standar, bukan satu.</b> Dewasa '
            f'({_angka(kb["dewasa"]["n"])} catatan) memakai ambang WHO yang tetap; anak '
            f'({_angka(kb["anak"]["n"])} catatan) memakai persentil CDC yang bergeser '
            f'setiap tahun usia dan jenis kelamin. Keduanya tidak boleh disatukan dalam '
            f'satu sumbu, karena "Overweight" akan berarti dua hal berbeda. '
            f'{_angka(kb["balita"]["n"])} catatan balita ({kb["balita"]["batas"]}) tidak '
            f'diklasifikasi sama sekali, karena IMT-menurut-usia tidak berlaku secara '
            f'medis di bawah 2 tahun.</div>', **HTML)

        # ---------------- 3. telusuri satu penyakit ----------------
        st.markdown(T.judul_bagian(
            "Telusuri Satu Penyakit",
            "Pilih satu penyakit untuk melihat siapa yang ditandai berisiko, "
            "lalu pilih satu variabel untuk melihat bagaimana risikonya berubah."),
            **HTML)
        st.caption("Kendali di bawah ini hanya mengubah grafik pada bagian ini — "
                   "tidak mengubah prediksi Anda. Data diri tetap diisi di panel kiri.")

        var_desil = [c for c in a["num_cols"] if c not in VAR_DESIL_LEWAT]
        # st.session_state bertahan melewati hot-reload. Bila pengguna sedang
        # memilih "Usia" saat daftar opsi ini menyusut, selectbox menerima nilai
        # yang tidak ada di dalam opsinya dan melempar StreamlitAPIException.
        if st.session_state.get("skrining_variabel") not in var_desil:
            st.session_state.pop("skrining_variabel", None)

        with st.container(border=True):
            k1, k2, k3 = st.columns(3)
            pilih_p = k1.selectbox("Penyakit yang ditampilkan", list(a["penyakit"]),
                                   key="skrining_penyakit")
            skala = k2.radio("Skala piramida",
                             [A.SKALA_PERSEN, A.SKALA_JUMLAH],
                             key="skrining_skala")
            var_s = k3.selectbox("Variabel untuk kurva desil", var_desil,
                                 key="skrining_variabel")

        dps = a["penyakit"][pilih_p]

        # Penanda "posisi Anda" HANYA untuk penyakit yang syarat usianya
        # terpenuhi -- persis seperti tab per penyakit. Bila tidak, tab analisis
        # akan bertentangan dengan gerbang usia di tab Hasil.
        tandai_s = _punya_nilai and pilih_p in LAYAK_PENGGUNA
        if _punya_nilai and not tandai_s:
            st.markdown(
                f'<div class="catatan">Penanda "posisi Anda" tidak ditampilkan untuk '
                f'{pilih_p} karena pada usia {int(usia)} tahun pertanyaannya tidak '
                f'diajukan (berlaku usia {dps["usia_label"]}).</div>', **HTML)

        _tampilkan(st, A.figur_piramida_risiko(
            a, pilih_p, skala,
            sorot=(_pita_usia(a, int(usia)), jk) if tandai_s else None))

        st.markdown(
            '<div class="catatan"><b>Cara membaca:</b> panjang batang oranye pada mode '
            '<i>Jumlah orang</i> adalah <b>jumlah</b> yang ditandai, dan jumlah selalu '
            'mengikuti besar kelompoknya — kelompok usia yang pesertanya banyak otomatis '
            'punya penanda banyak. Angka persen di ujung tiap batang adalah '
            '<b>prevalensinya</b>; itulah yang menyatakan risiko.</div>', **HTML)

        if pilih_p == "Kanker Paru":
            st.markdown(
                f'<div class="catatan-penting">Perbedaan laki-laki dan perempuan pada '
                f'penyakit ini sangat besar: {a["kp_prev_sex"]["L"]:.2f}% berbanding '
                f'{a["kp_prev_sex"]["P"]:.2f}%. Jenis kelamin di sini diduga menandai '
                f'kebiasaan merokok, yang tidak terekam dalam data.</div>', **HTML)

        st.checkbox("Pisahkan menurut jenis kelamin", key="skrining_pisah_jk")
        _tampilkan(st, A.figur_kurva_desil(
            a, pilih_p, var_s,
            pisah_jk=st.session_state.get("skrining_pisah_jk", False),
            nilai_pengguna=NILAI_PENGGUNA.get(var_s) if tandai_s else None))

        n_desil = len(dps["variabel"][var_s]["desil_x"])
        st.markdown(
            f'<div class="catatan"><b>Catatan:</b> desil membagi peserta menjadi sepuluh '
            f'kelompok sama besar menurut variabel ini, sehingga tiap titik disandarkan '
            f'pada jumlah baris yang mirip — jumlah itu dicetak kecil di bawah tiap titik. '
            + (f'Pada {var_s} hanya terbentuk {n_desil} desil karena nilainya dicatat '
               f'dalam pembulatan sehingga beberapa batas desil bernilai sama. '
               if n_desil < 10 else '')
            + 'Usia tidak ditawarkan di sini karena piramida di atas sudah '
              'menunjukkan risiko menurut usia — dan menunjukkannya per jenis '
              'kelamin sekaligus. Sebaran menurut usia ada di tab '
              '<b>Analisis per Penyakit</b>.</div>', **HTML)

        if pilih_p == "Kanker Paru" and var_s == "Tinggibadan":
            p_ = a["perancu"]
            st.markdown(
                f'<div class="catatan-penting">Centang <b>Pisahkan menurut jenis '
                f'kelamin</b> di atas, lalu perhatikan kedua garisnya menjadi datar. '
                f'Kenaikan pada garis gabungan seluruhnya berasal dari komposisi jenis '
                f'kelamin: laki-laki lebih tinggi <i>dan</i> laki-laki yang menanggung '
                f'risikonya. Korelasinya jatuh dari {p_["tinggi_kp_pooled"]:+.3f} menjadi '
                f'{p_["tinggi_kp_L"]:+.3f} (L) dan {p_["tinggi_kp_P"]:+.3f} (P). '
                f'<b>Jangan menulis bahwa orang lebih tinggi berisiko kanker paru.</b>'
                f'</div>', **HTML)

        if pilih_p == "Diabetes Melitus" and var_s == "IMT_recalculated":
            st.markdown(
                '<div class="catatan-penting">Kurva ini nyaris menyentuh 100% pada desil '
                'teratas bukan karena temuan epidemiologis, melainkan karena label Diabetes '
                'pada kuesioner memang praktis mengikuti aturan IMT di atas 25. Hubungan '
                'itu bersifat melingkar.</div>', **HTML)

        # ---------------- 4. kookurensi penanda ----------------
        ko = a["kookurensi"]
        st.markdown(T.judul_bagian(
            "Ditandai Lebih dari Satu Penyakit",
            "Berapa banyak penanda Berisiko yang dipegang satu catatan sekaligus."),
            **HTML)
        st.caption("Kelompok di bawah ini dibentuk menurut pertanyaan yang benar-benar "
                   "diajukan, bukan menurut pita usia.")

        opsi = {f"Usia {s['usia_min']}–{s['usia_max']} · {s['n_ditanya']} dari 4 "
                f"pertanyaan ({_angka(s['n'])} catatan)": s["kode"]
                for s in ko["strata"]}
        pilih_k = st.radio("Kelompok yang ditanyai", list(opsi), horizontal=True,
                           key="skrining_strata")
        sk = next(s for s in ko["strata"] if s["kode"] == opsi[pilih_k])

        _tampilkan(st, A.figur_kookurensi(a, sk["kode"]))

        # Personalisasi di sini berupa KALIMAT, bukan penanda pada grafik.
        # Menandai pengguna berarti menaruh jumlah prediksi empat model -- dua
        # di antaranya berpresisi 0,224 dan 0,103 -- di atas sebaran jawaban
        # kuesioner yang benar-benar tercatat. Galatnya menumpuk dan kedua hal
        # itu bukan besaran yang sama.
        if _punya_nilai:
            milik = next((s for s in ko["strata"]
                          if s["usia_min"] <= int(usia) <= s["usia_max"]), None)
            # Kedua batas dibaca DARI DATA. "Tidak masuk strata" punya dua sebab
            # yang sangat berbeda: terlalu muda (memang hanya TBC yang ditanya)
            # atau lebih tua daripada catatan tertua pada data. Menyamakan
            # keduanya membuat orang berusia 114 tahun diberi tahu bahwa hanya
            # TBC yang ditanyakan, padahal tab Hasil menilai keempat penyakit.
            usia_min_strata = min(s["usia_min"] for s in ko["strata"])
            usia_max_strata = max(s["usia_max"] for s in ko["strata"])
            if milik is not None:
                st.markdown(
                    f'<div class="catatan">Pada usia {int(usia)} tahun, Anda termasuk '
                    f'kelompok yang mendapat {milik["n_ditanya"]} dari 4 pertanyaan '
                    f'({_angka(milik["n"])} catatan).</div>', **HTML)
            elif int(usia) < usia_min_strata:
                st.markdown(
                    f'<div class="catatan">Pada usia {int(usia)} tahun hanya pertanyaan '
                    f'TBC yang diajukan, sehingga Anda tidak termasuk kedua kelompok di '
                    f'atas.</div>', **HTML)
            else:
                st.markdown(
                    f'<div class="catatan">Usia {int(usia)} tahun berada di luar rentang '
                    f'usia yang tercatat pada data skrining ini (tertinggi '
                    f'{usia_max_strata} tahun), sehingga tidak ada kelompok pembanding '
                    f'yang cocok. Prediksi di tab <b>Hasil</b> tetap dijalankan karena '
                    f'gerbang usianya hanya menetapkan batas bawah, bukan batas '
                    f'atas.</div>', **HTML)

        dm_ht = {"Diabetes Melitus", "Hipertensi"} <= set(sk["penyakit"])
        st.markdown(f"""
<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Yang harus dibaca bersama grafik ini</div>
  <div class="catatan"><b>1. Bukan "dari 4 penyakit".</b> Sumbu grafik berbunyi
    <i>dari {sk['n_ditanya']} pertanyaan yang diajukan</i>, karena kelompok ini menerima
    {sk['n_ditanya']} dari 4 pertanyaan{
      ' — pertanyaan ' + ', '.join(p for p in ko['urutan_penyakit']
                                   if p not in sk['penyakit'])
      + ' belum diajukan pada usia ini'
      if sk['n_ditanya'] < 4 else ''}.</div>
  <div class="catatan"><b>2. Denominatornya {_angka(sk['n'])} catatan</b> berusia
    {sk['usia_min']}–{sk['usia_max']} tahun, yaitu {sk['cakupan']:.2f}% dari
    {_angka(sk['n_pita_usia'])} catatan pada rentang usia yang sama.</div>
  <div class="catatan"><b>3. <i>Tidak Dapat Pertanyaan</i> berarti pertanyaannya tidak
    diajukan</b>, bukan jawabannya "tidak". Karena itu tidak ada satu denominator yang
    berlaku untuk keempat penyakit sekaligus, dan kedua kelompok di atas tidak boleh
    digabungkan.</div>
  <div class="catatan-penting"><b>4. Siapa yang tidak masuk, dan ke arah mana angkanya
    bias.</b> {_angka(sk['keluar']['n'])} catatan pada rentang usia yang sama tidak
    menerima seluruh {sk['n_ditanya']} pertanyaan itu. Prevalensi TBC pada kelompok yang
    keluar tersebut <b>{sk['keluar']['prev']['TBC']:.2f}%</b>, dibanding
    <b>{sk['prev_strata']['TBC']:.2f}%</b> di dalam kelompok ini — ketidaklengkapannya
    jelas tidak acak, dan justru catatan dengan penanda terbanyak yang tersingkir.
    <b>Penumpukan yang terlihat di grafik hampir pasti terlalu rendah, bukan terlalu
    tinggi.</b></div>
  {f'<div class="catatan"><b>5. Sebagian penumpukan bersifat definisional.</b> Diabetes '
   f'dan Hipertensi sama-sama sangat ditentukan IMT, sehingga satu orang ber-IMT di atas '
   f'25 hampir pasti ditandai keduanya. Angka besar pada k = 2 tidak boleh dibaca sebagai '
   f'dua penyakit yang saling menyebabkan. Lingkaran berongga menunjukkan harapan bila '
   f'{sk["n_ditanya"]} penanda itu saling bebas; jaraknya dari batang adalah ukuran '
   f'penumpukan, bukan bukti sebab-akibat.</div>' if dm_ht else ''}
  <div class="catatan"><b>{'6' if dm_ht else '5'}. Per catatan skrining, bukan per
    orang.</b> {URUTAN_ID.get(sk['n_ditanya'], f"Semua {sk['n_ditanya']}")} jawaban itu
    berada pada baris yang sama sehingga penumpukannya sah dalam satu kali skrining,
    tetapi <code>id</code> pada data ini diacak sehingga baris tidak dapat digabungkan
    menjadi orang.</div>
  <div class="catatan" style="opacity:.85;">Tidak digambar:
    {_angka(ko['pola_ditanya'].get('0001', 0))} catatan yang hanya ditanyai TBC, dan
    {_angka(ko['n_pola_lain'])} catatan dengan pola pertanyaan lain.</div>
</div>
""", **HTML)

        st.markdown(
            '<div class="catatan-penting">Semua angka di tab ini adalah <b>hubungan '
            'statistik, bukan sebab-akibat</b>. Data ini tidak memuat riwayat keluarga, '
            'status merokok, tekanan darah, lingkar perut, maupun aktivitas fisik, '
            'sehingga variabel yang tampak berpengaruh bisa saja hanya menandai faktor '
            'lain yang tidak terekam.</div>', **HTML)



with tab_penyakit:
    if ANALISIS is None:
        _analisis_belum_siap()
    else:
        a = ANALISIS
        punya_nilai = _punya_nilai

        # ---------------- 1. kendali + histogram/KDE ----------------
        st.markdown(T.judul_bagian(
            "Sebaran Variabel per Penyakit",
            "Pilih penyakit, kelas yang ingin dilihat, dan variabelnya. "
            "Batang = histogram kepadatan, garis = KDE (perkiraan sebaran yang dihaluskan)."),
            **HTML)

        d1, d2, d3 = st.columns(3)
        pilih = d1.selectbox("Penyakit", list(a["penyakit"]),
                             key="analisis_penyakit")
        tampilkan = d2.selectbox("Tampilkan",
                                 ["Keduanya", "Berisiko", "Tidak Berisiko"],
                                 key="analisis_kelas")
        var = d3.selectbox("Variabel", a["num_cols"], key="analisis_variabel")

        dp = a["penyakit"][pilih]
        st.markdown(
            f'<div class="meta-model">Berlaku usia {dp["usia_label"]} · '
            f'{dp["n"]:,} catatan · prevalensi {dp["prevalensi"]*100:.2f}% · '
            f"Cramer's V segmen {dp['segmen']['v']:.3f} · "
            f"jenis kelamin {dp['jenis_kelamin']['v']:.3f}</div>"
            .replace(",", "."), **HTML)

        tandai = pilih in LAYAK_PENGGUNA
        if punya_nilai and not tandai:
            st.markdown(
                f'<div class="catatan">Penanda "posisi Anda" tidak ditampilkan untuk '
                f'{pilih} karena pada usia {int(usia)} tahun pertanyaannya tidak diajukan '
                f'(berlaku usia {dp["usia_label"]}).</div>', **HTML)

        # st.pyplot menghasilkan gambar statis, sehingga masalah pemasangan
        # grafik Vega di dalam tab non-aktif tidak berlaku di sini.
        fig = A.figur_histogram_kde(
            a, pilih, var, tampilkan,
            NILAI_PENGGUNA.get(var) if tandai else None)
        # use_container_width=False: Streamlit membatasi gambar pada 1460 px
        # (MAXIMUM_CONTENT_WIDTH = 2*730). Dengan True, pada layar lebih lebar
        # gambar itu DIREGANGKAN melebihi ukuran aslinya sehingga tampak pecah.
        st.pyplot(fig, use_container_width=False)
        A.plt.close(fig)

        if var in ("Tinggibadan", "Berat Badan", "Usia"):
            st.markdown(
                '<div class="catatan"><b>Catatan:</b> variabel ini dicatat dalam '
                'pembulatan (tinggi umumnya kelipatan 5 cm), sehingga histogramnya '
                'berbentuk deretan paku. Dengan ratusan ribu baris, garis KDE ikut '
                'mengikuti paku itu alih-alih meratakannya — pengelompokan tersebut '
                'memang ada di data. Gunanya garis di sini adalah membandingkan '
                'bentuk kedua kelas, yang sulit dibaca dari batang yang saling '
                'bertumpuk.</div>', **HTML)

        if pilih == "Diabetes Melitus" and var == "IMT_recalculated":
            st.markdown(
                '<div class="catatan-penting">Perhatikan bahwa kurva Tidak Berisiko '
                'jatuh ke nol tepat di IMT 25 dan digantikan kurva Berisiko. Itu bukan '
                'temuan epidemiologis, melainkan aturan penilaian kuesioner skrining '
                'yang memang menandai IMT di atas 25 sebagai berisiko.</div>', **HTML)

        # ---------------- 2. peta panas segmen x penyakit ----------------
        st.markdown(T.judul_bagian(
            "Segmen Kepesertaan vs Keempat Penyakit",
            "Dua sudut pandang atas data yang sama."), **HTML)

        h1, h2 = st.columns(2)
        _tampilkan(h1, A.figur_heatmap_segmen(a, "prevalensi",
                                              sorot=SEGMEN_PENGGUNA))
        _tampilkan(h2, A.figur_heatmap_segmen(a, "risiko_relatif",
                                              sorot=SEGMEN_PENGGUNA))

        st.markdown(
            '<div class="catatan"><b>Catatan:</b> peta kiri memakai prevalensi mentah — '
            'berguna untuk memperkirakan beban layanan. Peta kanan memakai risiko relatif '
            'terhadap rata-rata penyakit itu sendiri, sehingga penyakit dengan prevalensi '
            'sangat berbeda tetap dapat dibandingkan. Keduanya perlu dibaca bersama.</div>',
            **HTML)

        # ---------------- 3. heatmap lengkap ----------------
        st.markdown(T.judul_bagian(
            "Heatmap Lengkap — Semua Variabel vs Semua Penyakit",
            "Numerik memakai korelasi point-biserial (bertanda); kategorik memakai "
            "Cramer's V (0–1, tanpa arah)."), **HTML)

        _tampilkan(st, A.figur_heatmap_asosiasi(a))

        p = a["perancu"]
        st.markdown(f"""
<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Tiga hubungan yang ternyata dikacaukan variabel lain</div>
  <table class="tabel-info">
    <tr><th>Hubungan</th><th>Sebelum dikendalikan</th><th>Sesudah</th><th>Penyebab</th></tr>
    <tr><td>Tinggi ↔ Berat</td><td class="angka">{p['tinggi_berat_pooled']:.3f}</td>
        <td class="angka">{p['tinggi_berat_dewasa']:.3f}</td><td>usia (pertumbuhan anak)</td></tr>
    <tr><td>Tinggi → Kanker Paru</td><td class="angka">{p['tinggi_kp_pooled']:+.3f}</td>
        <td class="angka">{p['tinggi_kp_L']:+.3f} (L) / {p['tinggi_kp_P']:+.3f} (P)</td>
        <td><b>jenis kelamin</b></td></tr>
    <tr><td>Usia ↔ IMT</td><td class="angka">{p['usia_imt_pooled']:+.3f}</td>
        <td class="angka">{p['usia_imt_dewasa']:+.3f}</td><td>pertumbuhan anak</td></tr>
  </table>
  <div class="catatan-penting">
    <b>Jangan menulis bahwa orang lebih tinggi berisiko kanker paru.</b> Hubungan
    +{p['tinggi_kp_pooled']:.3f} itu hilang begitu jenis kelamin dipisahkan. Laki-laki lebih
    tinggi <i>dan</i> laki-laki yang menanggung risikonya
    ({a['kp_prev_sex']['L']:.2f}% vs {a['kp_prev_sex']['P']:.2f}%) — tinggi badan hanya
    menandai jenis kelamin.
  </div>
  <div class="catatan"><b>Catatan:</b> angka terbesar pada peta di atas
    (IMT ↔ Diabetes {a['asosiasi']['nilai']['Diabetes Melitus'][3]:.3f}) justru paling tidak
    informatif — label Diabetes pada kuesioner memang praktis mengikuti aturan IMT di atas 25,
    sehingga hubungan itu bersifat melingkar. Hubungan IMT ↔ Hipertensi
    ({a['asosiasi']['nilai']['Hipertensi'][3]:.3f}) lebih layak dilaporkan.</div>
  <div class="catatan">Usia ↔ IMT <b>berbalik tanda</b>: {p['usia_imt_pooled']:+.3f} pada
    seluruh data adalah efek pertumbuhan anak, sedangkan pada orang dewasa IMT justru
    sedikit menurun seiring usia ({p['usia_imt_dewasa']:+.3f}).</div>
</div>
""", **HTML)


        st.markdown(
            '<div class="catatan-penting">Semua angka di tab ini adalah <b>hubungan '
            'statistik, bukan sebab-akibat</b>. Data ini tidak memuat riwayat keluarga, '
            'status merokok, tekanan darah, lingkar perut, maupun aktivitas fisik, sehingga '
            'variabel yang tampak berpengaruh bisa saja hanya menandai faktor lain yang '
            'tidak terekam.</div>', **HTML)


# --------------------------------------------------------------------------
# TAB 4 -- Informasi
# --------------------------------------------------------------------------
with tab_info:
    contoh_b, contoh_t = 70.0, 170.0
    contoh_imt = P.hitung_imt(contoh_b, contoh_t)

    st.markdown(T.judul_bagian("1. Bagaimana IMT dihitung",
                               "Indeks Massa Tubuh membandingkan berat badan "
                               "dengan tinggi badan."), **HTML)
    st.markdown(f"""
<div class="kartu">
  <div class="rumus">IMT = berat (kg) &divide; [ tinggi (m) ]&sup2;</div>
  <div style="font-size:.88rem;color:{T.TINTA};">
    Contoh: berat {contoh_b:.0f} kg, tinggi {contoh_t:.0f} cm = {contoh_t/100:.2f} m<br>
    IMT = {contoh_b:.0f} &divide; ({contoh_t/100:.2f} &times; {contoh_t/100:.2f})
    = <b>{contoh_imt:.1f}</b>
  </div>
  <div class="catatan"><b>Catatan:</b> tinggi diubah dari sentimeter ke meter lebih
  dulu. IMT tidak membedakan massa otot dan lemak, sehingga pada orang yang sangat
  berotot nilainya bisa terlihat tinggi tanpa berarti kelebihan lemak.</div>
</div>
""", **HTML)

    # --- kategori ---
    st.markdown(T.judul_bagian("2. Bagaimana IMT dikategorikan",
                               "Ambang untuk dewasa dan anak berbeda, dan itu "
                               "disengaja."), **HTML)

    baris_who = []
    bawah = None
    for atas, nama in P.bs.WHO_ADULT_BINS:
        if bawah is None:
            rentang = f"kurang dari {atas:g}"
        elif atas == float("inf"):
            rentang = f"{bawah:g} ke atas"
        else:
            rentang = f"{bawah:g} – {atas:g}"
        baris_who.append(f"<tr><td>{nama}</td><td class='angka'>{rentang}</td></tr>")
        bawah = atas

    st.markdown(f"""
<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Dewasa (di atas {P.bs.CHILD_MAX_AGE} tahun) — standar WHO, 8 kategori</div>
  <table class="tabel-info">
    <tr><th>Kategori</th><th>Rentang IMT</th></tr>
    {''.join(baris_who)}
  </table>
  <div class="catatan"><b>Catatan:</b> di dashboard, skala ringkas menggunakan
  4 kelompok (Underweight, Normal, Overweight, Obese) agar mudah dibaca, sedangkan
  kategori rinci di atas tetap ditampilkan sebagai teks.</div>
</div>

<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Anak &amp; remaja ({P.bs.CHILD_MIN_AGE}–{P.bs.CHILD_MAX_AGE} tahun) — persentil CDC</div>
  <div style="font-size:.88rem;color:{T.TINTA};margin-top:6px;">
    Anak masih tumbuh, sehingga IMT yang sehat berubah menurut usia dan jenis
    kelamin. Ambang dewasa tidak dipakai. Yang dipakai adalah persentil:
  </div>
  <table class="tabel-info">
    <tr><th>Kategori</th><th>Posisi persentil</th></tr>
    <tr><td>Underweight</td><td class="angka">di bawah persentil 5</td></tr>
    <tr><td>Healthy weight</td><td class="angka">persentil 5 – 85</td></tr>
    <tr><td>At risk of overweight</td><td class="angka">persentil 85 – 95</td></tr>
    <tr><td>Overweight</td><td class="angka">persentil 95 ke atas</td></tr>
  </table>
  <div class="catatan"><b>Catatan:</b> label anak diberi awalan <code>Anak_</code>
  supaya tidak tertukar dengan label dewasa — kata "Overweight" berarti dua hal
  berbeda pada dua kelompok usia.</div>
</div>

<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Balita (di bawah {P.bs.CHILD_MIN_AGE} tahun) — tidak dikategorikan</div>
  <div style="font-size:.88rem;color:{T.TINTA};margin-top:6px;">
    IMT-menurut-usia tidak berlaku secara medis di bawah 2 tahun. WHO menganjurkan
    Weight-for-Length. Kelompok ini tetap dihitung IMT-nya, tetapi sengaja tidak
    diberi kategori.
  </div>
  <div class="catatan">Sumber standar: {P.bs.SOURCE_URL}</div>
</div>
""", **HTML)

    # --- bagaimana prediksi dibuat ---
    st.markdown(T.judul_bagian("3. Bagaimana prediksi dibuat",
                               "Model dilatih dari data skrining kesehatan, bukan "
                               "dari pemeriksaan klinis."), **HTML)

    baris_model = "".join(
        f"<tr><td>{nama}</td><td>{i['model']}</td>"
        f"<td class='angka'>{i['usia_label']}</td>"
        f"<td class='angka'>{i['prevalensi'] * 100:.2f}%</td></tr>"
        for nama, i in INFO.items())

    st.markdown(f"""
<div class="kartu">
  <div style="font-size:.88rem;color:{T.TINTA};">
    Anda mengisi <b>lima</b> hal: jenis kelamin, usia, tinggi badan, berat badan,
    dan segmen kepesertaan BPJS. IMT dihitung otomatis dari tinggi dan berat,
    sehingga model menerima enam angka.
    Setiap penyakit punya modelnya sendiri, dipilih sebagai model dengan F1-Score
    terbaik saat pengujian.
  </div>
  <table class="tabel-info">
    <tr><th>Penyakit</th><th>Model</th><th>Berlaku usia</th>
        <th>Prevalensi populasi</th></tr>
    {baris_model}
  </table>
  <div class="catatan"><b>Catatan:</b> model dilatih pada 80% data dan diuji pada
  20% sisanya yang tidak pernah dilihat saat pelatihan. Angka pada kolom prevalensi
  adalah proporsi peserta skrining yang ditandai berisiko — dipakai sebagai garis
  putus-putus pembanding pada hasil.</div>
</div>

<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">Batas usia</div>
  <div style="font-size:.88rem;color:{T.TINTA};margin-top:6px;">
    Pada kuesioner skrining aslinya, tidak semua pertanyaan diajukan ke semua umur.
    Model hanya dilatih pada kelompok usia yang memang ditanyai, sehingga di luar
    rentang itu model <b>tidak dijalankan sama sekali</b> — bukan dijalankan lalu
    disembunyikan. Anak usia 10 tahun hanya menerima hasil TBC.
  </div>
</div>
""", **HTML)

    # --- arti hasil ---
    st.markdown(T.judul_bagian("4. Arti hasil prediksi",
                               "Yang diperkirakan adalah penanda pada kuesioner, "
                               "bukan penyakitnya."), **HTML)
    st.markdown(f"""
<div class="kartu">
  <table class="tabel-info">
    <tr><th>Yang tampil</th><th>Artinya</th></tr>
    <tr><td>Probabilitas (%)</td>
        <td>Perkiraan peluang bahwa kuesioner skrining akan menandai Anda
            "Berisiko", berdasarkan orang-orang dengan profil serupa pada data.</td></tr>
    <tr><td>Berisiko</td>
        <td>Probabilitas 50% atau lebih. Artinya <b>kuesioner kemungkinan menandai
            Anda</b>, bukan bahwa Anda menderita penyakit tersebut.</td></tr>
    <tr><td>Tidak Berisiko</td>
        <td>Probabilitas di bawah 50%. Bukan jaminan sehat.</td></tr>
  </table>
  <div class="catatan"><b>Catatan:</b> ambang 50% adalah pilihan yang lazim, bukan
  ketentuan medis. Menurunkan ambang akan menjaring lebih banyak orang berisiko
  tetapi juga menambah peringatan palsu.</div>
</div>
""", **HTML)

    # --- keterbatasan ---
    st.markdown(T.judul_bagian("5. Keterbatasan yang perlu diketahui",
                               "Bagian terpenting untuk dibaca sebelum "
                               "menyimpulkan apa pun."), **HTML)

    pres_kp = INFO["Kanker Paru"]["metrik"]["Precision"]
    pres_tbc = INFO["TBC"]["metrik"]["Precision"]

    st.markdown(f"""
<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Faktor risiko terpenting tidak ada dalam data</div>
  <div style="font-size:.88rem;color:{T.TINTA};margin-top:6px;">
    Riwayat keluarga, status merokok, tekanan darah, lingkar perut, dan aktivitas
    fisik tidak tersedia. Inilah penyebab utama batas kemampuan model — bukan
    pilihan algoritmanya.
  </div>
</div>

<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Hasil Diabetes mengikuti aturan IMT</div>
  <div style="font-size:.88rem;color:{T.TINTA};margin-top:6px;">
    Pada data skrining, hampir semua orang dengan IMT di atas 25 otomatis ditandai
    berisiko diabetes. Model mempelajari kembali aturan itu. Jadi hasil Diabetes
    lebih tepat dibaca sebagai penerapan ulang aturan IMT, bukan prediksi penyakit.
  </div>
</div>

<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">
    Kanker Paru dan TBC banyak memberi peringatan palsu</div>
  <table class="tabel-info">
    <tr><th>Penyakit</th><th>Dari 100 yang ditandai berisiko, benar sekitar</th></tr>
    <tr><td>Kanker Paru</td><td class="angka">{round(pres_kp * 100)} orang</td></tr>
    <tr><td>TBC</td><td class="angka">{round(pres_tbc * 100)} orang</td></tr>
  </table>
  <div class="catatan"><b>Catatan:</b> keduanya jauh lebih berguna sebagai penyaring
  awal untuk pemeriksaan lanjutan daripada sebagai kesimpulan.</div>
</div>

<div class="kartu">
  <div style="font-weight:700;color:{T.NAVY};font-size:.95rem;">Cakupan data</div>
  <div style="font-size:.88rem;color:{T.TINTA};margin-top:6px;">
    Data berasal dari <b>peserta yang mengikuti skrining</b>, bukan seluruh penduduk
    {"kedua kabupaten" if wilayah == "Gabungan" else f"Kabupaten {wilayah}"}.
    Setiap angka berlaku per catatan skrining, bukan per orang, karena
    identitas peserta sengaja diacak untuk melindungi data asli.
  </div>
</div>

<div class="catatan-penting">{P.DISCLAIMER}</div>
""", **HTML)
