"""
Pembangun grafik untuk tab Analisis (matplotlib).

Seluruh angka dibaca dari models/<wilayah>/analysis.json yang dihasilkan
build_analysis.py -- satu berkas per wilayah.
Tidak ada perhitungan statistik di sini -- berkas ini hanya menggambar.

CATATAN WARNA
-------------
Warna diperiksa secara terhitung, bukan dikira-kira (lihat docstring theme.py).

- Dua kelas histogram memakai pasangan yang sudah lolos uji: Berisiko #c96f0f dan
  Tidak Berisiko #2d8746 (CVD dE 10,2; penglihatan normal dE 27,2; kontras 3,64
  dan 4,50 terhadap kartu putih).

- Skala warna notebook TIDAK dipakai ulang. `YlOrRd` memakai banyak corak warna
  dan `RdYlGn_r` memakai kuning di titik tengah; keduanya melanggar aturan
  sekuensial/divergen. Penggantinya:
    * prevalensi     -> tangga satu corak navy, sudah diuji: lightness menurun
      monoton, jarak antar langkah >= 0,101, corak hanya melebar 6,7 derajat, dan
      langkah paling terang tetap 2,01:1 terhadap putih.
    * risiko relatif -> divergen hijau<->oranye dengan titik tengah NETRAL (abu,
      chroma 0,005) yang dipasang tepat pada RR = 1,00.
"""

from __future__ import annotations

import matplotlib
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.pyplot as plt
import numpy as np

import theme as T

BERISIKO = T.ORANYE          # #c96f0f
TIDAK = T.HIJAU              # #2d8746
NAVY = T.NAVY
NAVY_TUA = "#0b2140"         # garis tepi penanda "Anda" pada batang navy

RAMP_NAVY = ["#9dbad8", "#7099c4", "#4a7aae", "#2c568a", "#153763"]
RAMP_DIVERGEN = ["#2d8746", "#7cb894", "#dcdfe2", "#e8b183", "#c96f0f"]

SEX_LABEL = {"L": "Laki-laki", "P": "Perempuan"}

# Label kendali skala. Dipakai bersama oleh piramida risiko dan grafik
# keseimbangan kelas, supaya kedua kendali di layar berbunyi persis sama.
SKALA_PERSEN = "Persen dalam kelompok"
SKALA_JUMLAH = "Jumlah orang"

# Nama pendek khusus sumbu peta panas -- nama penuh tetap dipakai di tooltip.
NAMA_PENDEK = {"Diabetes Melitus": "Diabetes"}

# SEMUA grafik di sini adalah figur matplotlib, bukan Altair.
#
# Alasannya perataan. Grafik Vega yang dipasang di dalam tab yang belum aktif
# terpasang saat lebarnya masih 0 lalu tidak pernah mencoba lagi, sehingga
# lebarnya HARUS dipatok dalam piksel -- baik use_container_width=True maupun
# width="container" sama-sama menghasilkan wadah kosong. Lebar piksel tetap itu
# tidak pernah pas dengan kolom teks yang lebarnya mengikuti layar: hasil audit
# 10 Agustus menunjukkan tiap grafik Altair meleset 47-97 px dari tepi kanan,
# sedangkan gambar matplotlib pas 0 px karena gambar ikut menyesuaikan wadah.
FONT = "Segoe UI, Arial, Helvetica, sans-serif"

# Font matplotlib dipatok eksplisit. Font bawaan matplotlib tidak punya bobot
# "semibold" -- memakainya membanjiri log dengan peringatan findfont.
matplotlib.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "Arial", "DejaVu Sans"],
    "axes.titleweight": "bold",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": T.GARIS,
    "axes.labelcolor": T.ABU_TUA,
    "xtick.color": T.ABU_GRAFIK,
    "ytick.color": T.ABU_GRAFIK,
    "grid.color": "#eef2f6",
})


CMAP_NAVY = LinearSegmentedColormap.from_list("navy", RAMP_NAVY)
CMAP_DIVERGEN = LinearSegmentedColormap.from_list("divergen", RAMP_DIVERGEN)


def _rapikan(ax):
    """Gaya sumbu seragam untuk semua figur."""
    ax.grid(True, alpha=0.35, linewidth=0.7)
    ax.set_axisbelow(True)
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)
    return ax


def _ribuan(v, _=None):
    return f"{abs(int(v)):,}".replace(",", ".")


# --------------------------------------------------------------------------
# 1a. Profil populasi
# --------------------------------------------------------------------------
def figur_piramida(a: dict):
    """Piramida peserta skrining: laki-laki ke kiri, perempuan ke kanan."""
    kel = a["piramida"]["kelompok"]
    L = np.array(a["piramida"]["L"], dtype=float)
    P = np.array(a["piramida"]["P"], dtype=float)
    y = np.arange(len(kel))

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.barh(y, -L, color=NAVY, height=0.72, label="Laki-laki")
    ax.barh(y, P, color=BERISIKO, height=0.72, label="Perempuan")
    ax.axvline(0, color=T.GARIS, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(kel)
    ax.set_ylabel("Kelompok usia")
    ax.set_xlabel("Jumlah catatan skrining")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_ribuan))
    ax.set_title("Komposisi peserta skrining", fontsize=12, color=NAVY, loc="left")
    ax.legend(frameon=False, fontsize=9, ncols=2, loc="lower right")
    _rapikan(ax)
    fig.tight_layout()
    return fig


def figur_komposisi_segmen(a: dict):
    seg = list(a["segmen_jumlah"])
    val = np.array([a["segmen_jumlah"][k] for k in seg], dtype=float)
    urut = np.argsort(val)

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    ax.barh(np.arange(len(seg)), val[urut], color=NAVY, height=0.68)
    ax.set_yticks(np.arange(len(seg)))
    ax.set_yticklabels([seg[i] for i in urut])
    ax.set_xlabel("Jumlah catatan skrining")
    ax.xaxis.set_major_formatter(plt.FuncFormatter(_ribuan))
    ax.set_title("Segmen kepesertaan", fontsize=12, color=NAVY, loc="left")
    ax.margins(x=0.16)
    for i, v in enumerate(val[urut]):
        ax.annotate(_ribuan(v), xy=(v, i), xytext=(4, 0),
                    textcoords="offset points", va="center", fontsize=8.5,
                    color=T.ABU_GRAFIK)
    _rapikan(ax)
    fig.tight_layout()
    return fig


def figur_keseimbangan_kelas(a: dict, skala: str = SKALA_PERSEN):
    """
    Keseimbangan kelas tiap penyakit: Berisiko vs Tidak Berisiko.

    `skala` = SKALA_PERSEN (bawaan) | SKALA_JUMLAH, memakai konstanta yang sama
    dengan piramida risiko supaya kedua kendali di tab ini berbunyi sama.

    Kedua skala menjawab pertanyaan yang berbeda dan sama-sama perlu:
      - PERSEN menyamakan panjang batang, jadi ketimpangan keempat penyakit bisa
        diadu langsung meski jumlah pesertanya berbeda jauh.
      - JUMLAH mempertahankan besar populasinya, jadi terlihat bahwa prevalensi TBC
        yang kecil tetap berarti puluhan ribu orang -- hal yang justru disembunyikan
        tampilan persen.
    """
    nama = list(a["penyakit"])
    n = np.array([a["penyakit"][k]["n"] for k in nama], dtype=float)
    prev = np.array([a["penyakit"][k]["prevalensi"] for k in nama], dtype=float)
    pos, neg = n * prev, n * (1 - prev)
    y = np.arange(len(nama))
    persen = skala == SKALA_PERSEN

    kiri = prev * 100 if persen else pos
    kanan = (1 - prev) * 100 if persen else neg
    total = kiri + kanan

    fig, ax = plt.subplots(figsize=(13, 4.2))
    ax.barh(y, kiri, color=BERISIKO, height=0.62, label="Berisiko")
    ax.barh(y, kanan, left=kiri, color=TIDAK, height=0.62, label="Tidak Berisiko")

    for i in range(len(nama)):
        teks_pos = (_ribuan(pos[i]) if persen
                    else f"{_ribuan(pos[i])} ({prev[i]*100:.1f}%)")
        # Angka hanya dicetak di dalam batang bila muat. Di bawah ~14% lebar
        # total, teksnya meluber ke batang sebelah dan justru tak terbaca --
        # dan pada skala JUMLAH itu sering terjadi karena batang Kanker Paru
        # jauh lebih pendek daripada TBC.
        if kiri[i] >= 0.14 * total[i]:
            ax.text(kiri[i] / 2, i, teks_pos, ha="center", va="center",
                    color="white", fontsize=8.5, fontweight="bold")
        else:
            # Label mendarat DI ATAS batang hijau, jadi warnanya putih. Oranye
            # di atas hijau adalah pasangan berkontras rendah.
            ax.annotate(teks_pos, xy=(kiri[i], i), xytext=(5, 0),
                        textcoords="offset points", va="center", fontsize=8,
                        color="white", fontweight="bold")
        ax.text(kiri[i] + kanan[i] / 2, i, _ribuan(neg[i]), ha="center",
                va="center", color="white", fontsize=8.5)

    ax.set_yticks(y)
    ax.set_yticklabels([f"{k}\n(n = {_ribuan(n[i])})" for i, k in enumerate(nama)],
                       fontsize=8.5)
    if persen:
        ax.set_xlabel("% catatan dalam kelompok yang ditanyai")
        ax.set_xlim(0, 100)
    else:
        ax.set_xlabel("Jumlah catatan skrining")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_ribuan))
    ax.invert_yaxis()
    ax.set_title("Keseimbangan kelas tiap penyakit", fontsize=12, color=NAVY,
                 loc="left")
    # Batang memenuhi sumbu, jadi tidak ada ruang kosong di dalamnya: legenda
    # ditaruh DI BAWAH, bukan "lower right" yang akan menimpa batang TBC.
    ax.legend(frameon=False, fontsize=9, ncols=2,
              loc="upper center", bbox_to_anchor=(0.5, -0.16))
    _rapikan(ax)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig


def figur_klasifikasi_bmi(a: dict):
    """
    Sebaran kategori IMT, dewasa dan anak dipisah (Bersih Lengkap II.2).

    Dua panel, bukan satu: dewasa memakai ambang WHO yang tetap, anak memakai
    persentil CDC yang bergeser tiap tahun usia. Digabung dalam satu sumbu,
    "Overweight" akan berarti dua hal berbeda sekaligus.
    """
    k = a["klasifikasi_bmi"]
    fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.6))

    for ax, kel, warna, judul in (
            (axes[0], "dewasa", NAVY, "Kategori WHO: Dewasa"),
            (axes[1], "anak", TIDAK, "Kategori CDC: Anak")):
        kat = k[kel]["kategori"]
        label = [l.replace("Anak_", "") for l in kat]
        nilai = np.array(list(kat.values()), dtype=float)
        x = np.arange(len(label))

        ax.bar(x, nilai, color=warna, width=0.68)
        ax.set_xticks(x)
        ax.set_xticklabels(label, rotation=35, ha="right", fontsize=8)
        ax.set_ylabel("Jumlah catatan")
        ax.set_title(f"{judul} ({k[kel]['batas']}, n = {_ribuan(k[kel]['n'])})",
                     fontsize=11, color=NAVY, loc="left")
        ax.yaxis.set_major_formatter(plt.FuncFormatter(_ribuan))
        ax.margins(y=0.16)
        for i, v in enumerate(nilai):
            ax.annotate(_ribuan(v), xy=(i, v), xytext=(0, 3),
                        textcoords="offset points", ha="center", fontsize=7.5,
                        color=T.ABU_GRAFIK)
        _rapikan(ax)
        ax.grid(axis="x", visible=False)

    fig.tight_layout()
    return fig


def figur_prevalensi_usia(a: dict):
    """
    Prevalensi menurut kelompok usia untuk keempat penyakit (Bersih B3).

    Sumbu x dibangun dari a["age_labels"] yang kanonik, lalu tiap penyakit
    dipetakan ke posisi itu.

    Versi lama menyerahkan sumbu x kepada matplotlib dengan mengirim daftar
    STRING pada empat panggilan plot terpisah. Matplotlib menambahkan kategori
    baru di urutan pertama kali dilihat, sehingga "0-4" dan "5-14" -- yang hanya
    dimiliki TBC, penyakit terakhir yang digambar -- mendarat di UJUNG KANAN
    sumbu. Sumbunya terbaca 15-24 ... 65+, 0-4, 5-14.

    pos[l] sengaja dibiarkan melempar KeyError bila ada label tak dikenal:
    berhenti dengan error jauh lebih baik daripada sumbu yang diam-diam
    diurutkan ulang. build_analysis.py memeriksa sisi datanya (X1), jadi
    celahnya tertutup dari dua arah.
    """
    label = a["age_labels"]
    pos = {l: i for i, l in enumerate(label)}
    warna = [NAVY, "#316cc3", BERISIKO, TIDAK]

    fig, ax = plt.subplots(figsize=(13, 4.6))

    # Dua kelompok termuda hanya ditanyai TBC. Tanpa penanda ini pembaca
    # melihat tiga garis yang mulai di 15-24 dan menyimpulkan prevalensinya nol
    # di bawah itu, padahal pertanyaannya memang tidak diajukan.
    ax.axvspan(-0.4, 1.5, color=T.LATAR_TINT, zorder=0, lw=0)

    for (nama, d), w in zip(a["penyakit"].items(), warna):
        xi = [pos[l] for l in d["kelompok_usia"]["label"]]
        ax.plot(xi, d["kelompok_usia"]["prev"],
                marker="o", lw=2.2, markersize=5, color=w, label=nama)

    ax.set_xticks(np.arange(len(label)))
    ax.set_xticklabels(label)
    ax.set_xlim(-0.4, len(label) - 0.6)
    ax.set_xlabel("Kelompok usia")
    ax.set_ylabel("% Berisiko")
    ax.set_title("Prevalensi menurut kelompok usia (bukan jumlah kasus)",
                 fontsize=12, color=NAVY, loc="left")
    ax.legend(frameon=False, fontsize=10, ncols=4)
    ax.margins(y=0.20)
    _rapikan(ax)
    ax.text(-0.3, ax.get_ylim()[1], "hanya TBC yang ditanya\ndi dua kelompok ini",
            va="top", ha="left", fontsize=8.5, color=T.ABU_GRAFIK, zorder=1)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1b. Peta panas
# --------------------------------------------------------------------------
def _warna_teks(cmap, norm, v):
    """
    Putih atau tinta, dipilih dari LUMINANS warna selnya -- bukan dari ambang
    nilai. Memakai ambang nilai membuat angka gelap mendarat di atas sel navy
    yang sudah pekat (mis. 36,7 pada peta prevalensi) sehingga sulit dibaca.
    """
    r, g, b, _ = cmap(norm(float(v)))

    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    lum = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    return "white" if lum < 0.45 else T.TINTA


def _sel_peta(ax, nilai, label_x, label_y, cmap, norm, fmt, rotasi=25):
    """Menggambar kisi peta panas beserta angkanya. Mengembalikan mappable."""
    im = ax.imshow(nilai, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(np.arange(len(label_x)))
    ax.set_xticklabels(label_x, rotation=rotasi, ha="right")
    ax.set_yticks(np.arange(len(label_y)))
    ax.set_yticklabels(label_y)
    # Kisi putih di antara sel; garis besar dimatikan supaya tidak dobel.
    ax.set_xticks(np.arange(len(label_x) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(label_y) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for i in range(nilai.shape[0]):
        for j in range(nilai.shape[1]):
            v = nilai[i, j]
            ax.text(j, i, format(v, fmt), ha="center", va="center",
                    fontsize=10, color=_warna_teks(cmap, norm, v))
    for sisi in ax.spines.values():
        sisi.set_visible(False)
    return im


def figur_heatmap_segmen(a: dict, mode: str = "prevalensi",
                         sorot: str | None = None):
    h = a["heatmap"]
    kunci = "prevalensi" if mode == "prevalensi" else "risiko_relatif"
    seg = h["segmen"]
    peny = [NAMA_PENDEK.get(p, p) for p in h["penyakit"]]
    nilai = np.array([h[kunci][s] for s in seg], dtype=float)

    if mode == "prevalensi":
        cmap = CMAP_NAVY
        norm = plt.Normalize(float(nilai.min()), float(nilai.max()))
        judul = "Prevalensi mentah (%) — beban layanan"
        fmt, legenda = ".1f", "% Berisiko"
    else:
        rng = max(abs(nilai.max() - 1), abs(1 - nilai.min()))
        cmap = CMAP_DIVERGEN
        norm = plt.Normalize(1 - rng, 1 + rng)
        judul = "Risiko relatif (1,00 = rata-rata penyakit itu)"
        fmt, legenda = ".2f", "risiko relatif"

    fig, ax = plt.subplots(figsize=(6.6, 5.0))
    im = _sel_peta(ax, nilai, peny, seg, cmap, norm, fmt)
    if sorot in seg:
        i = seg.index(sorot)
        ax.add_patch(plt.Rectangle((-0.5, i - 0.5), len(peny), 1, fill=False,
                                   edgecolor=NAVY, linewidth=2.5, zorder=5))
    ax.set_title(judul, fontsize=11.5, color=NAVY, loc="left")
    fig.colorbar(im, ax=ax, label=legenda, fraction=0.046, pad=0.03)
    fig.tight_layout()
    return fig


def figur_heatmap_asosiasi(a: dict):
    kol = a["asosiasi"]["kolom"]
    peny = list(a["asosiasi"]["nilai"])
    nilai = np.array([a["asosiasi"]["nilai"][p] for p in peny], dtype=float)

    fig, ax = plt.subplots(figsize=(13, 4.2))
    im = ax.imshow(np.abs(nilai), cmap=CMAP_NAVY,
                   norm=plt.Normalize(0, 0.65), aspect="auto")
    ax.set_xticks(np.arange(len(kol)))
    ax.set_xticklabels(kol, rotation=18, ha="right")
    ax.set_yticks(np.arange(len(peny)))
    ax.set_yticklabels(peny)
    ax.set_xticks(np.arange(len(kol) + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(len(peny) + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="white", linewidth=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    for i in range(nilai.shape[0]):
        for j in range(nilai.shape[1]):
            ax.text(j, i, f"{nilai[i, j]:+.3f}", ha="center", va="center",
                    fontsize=10.5,
                    color=_warna_teks(CMAP_NAVY, plt.Normalize(0, 0.65),
                                      abs(nilai[i, j])))
    for sisi in ax.spines.values():
        sisi.set_visible(False)
    ax.set_title("Kekuatan hubungan tiap variabel dengan tiap penyakit",
                 fontsize=12, color=NAVY, loc="left")
    fig.colorbar(im, ax=ax, label="kekuatan (nilai mutlak)",
                 fraction=0.022, pad=0.02)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1c. Telusuri satu penyakit
# --------------------------------------------------------------------------
KELAS = ("Tidak Berisiko", "Berisiko")
WARNA_KELAS = {"Tidak Berisiko": TIDAK, "Berisiko": BERISIKO}



def figur_piramida_risiko(a: dict, penyakit: str, skala: str = SKALA_PERSEN,
                          sorot: tuple | None = None):
    """
    Piramida peserta yang tiap batangnya dipecah Berisiko / Tidak Berisiko.

    `skala` = SKALA_PERSEN (bawaan) | SKALA_JUMLAH.
    `sorot` = (label_kelompok_usia, "L"|"P") atau None.

    URUTAN TUMPUKAN ITU PENTING, bukan selera. Berisiko diletakkan di SISI
    DALAM, menempel garis tengah. Bila ia diletakkan di luar, titik mulainya
    bergantung pada panjang segmen hijau di depannya, sehingga blok berisiko
    laki-laki dan perempuan tidak lagi berbagi garis dasar dan panjangnya tak
    bisa dibandingkan dengan mata. Dengan Berisiko di dalam, kedua blok oranye
    bertemu di x = 0 dan membentuk satu bentuk utuh.

    KEDELAPAN pita usia selalu digambar, termasuk yang tidak ditanyai (diberi
    keterangan "tidak ditanya"). Dengan begitu sumbu y-nya sama untuk keempat
    penyakit dan tidak melompat saat penyakit diganti.

    Angka persen dicetak di ujung TIAP batang pada KEDUA mode. Itu jawaban
    struktural untuk catatan analisis 3.12: pada mode jumlah, panjang batang adalah
    "peserta x risiko" dan kelompok yang pesertanya banyak otomatis terlihat
    paling parah. Prevalensinya harus selalu ada di gambar, bukan hanya di
    kalimat di bawahnya.
    """
    p = a["piramida_risiko"]["penyakit"][penyakit]
    d = a["penyakit"][penyakit]
    kel = a["piramida_risiko"]["kelompok"]
    y = np.arange(len(kel))
    persen = skala == SKALA_PERSEN

    fig, ax = plt.subplots(figsize=(13, 5.2))

    for sisi, tanda in (("L", -1), ("P", 1)):
        tot = np.array(p[sisi]["total"], dtype=float)
        ber = np.array(p[sisi]["berisiko"], dtype=float)
        aman = tot - ber
        with np.errstate(invalid="ignore", divide="ignore"):
            prev = np.where(tot > 0, ber / np.where(tot > 0, tot, 1) * 100, np.nan)

        if persen:
            b_plot = np.where(tot > 0, prev, 0.0)
            a_plot = np.where(tot > 0, 100 - prev, 0.0)
        else:
            b_plot, a_plot = ber, aman

        ax.barh(y, tanda * b_plot, color=BERISIKO, height=0.72,
                label="Berisiko" if sisi == "L" else None)
        ax.barh(y, tanda * a_plot, left=tanda * b_plot, color=TIDAK, height=0.72,
                label="Tidak Berisiko" if sisi == "L" else None)

        for i in range(len(kel)):
            if tot[i] == 0:
                continue
            ujung = tanda * (b_plot[i] + a_plot[i])
            ax.annotate(f"{prev[i]:.1f}%", xy=(ujung, y[i]),
                        xytext=(6 * tanda, 0), textcoords="offset points",
                        va="center", ha="left" if tanda > 0 else "right",
                        fontsize=8.5, color=T.ABU_TUA)

        # Penanda "Anda": garis tepi + label, TIDAK mengubah warna. Mewarnai
        # ulang batangnya akan bertabrakan dengan oranye yang sudah berarti
        # "Berisiko" pada legenda di sebelahnya.
        if sorot and sorot[1] == sisi and sorot[0] in kel:
            i = kel.index(sorot[0])
            lebar = b_plot[i] + a_plot[i]
            if lebar > 0:
                x0 = min(0, tanda * lebar)
                ax.add_patch(plt.Rectangle((x0, y[i] - 0.36), lebar, 0.72,
                                           fill=False, edgecolor=NAVY_TUA,
                                           linewidth=2.2, zorder=6))
                ax.annotate("Anda", xy=(tanda * lebar / 2, y[i] + 0.42),
                            ha="center", va="bottom", fontsize=9.5,
                            fontweight="bold", color=NAVY_TUA, zorder=7)

    for i, ada in enumerate(p["ditanya"]):
        if not ada:
            ax.text(0, y[i], "  tidak ditanya  ", ha="center", va="center",
                    fontsize=9, style="italic", color=T.ABU_GRAFIK,
                    bbox=dict(facecolor="white", edgecolor=T.GARIS, pad=2.5))

    ax.axvline(0, color=T.GARIS, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels(kel)
    ax.set_ylabel("Kelompok usia")
    if persen:
        # Ruang di luar 100% memang disediakan. Bila sumbu dipatok tepat pada
        # -100..100, angka prevalensi di ujung batang jatuh di luar area gambar
        # dan bertindihan dengan label kelompok usia.
        ax.set_xlim(-118, 118)
        ax.set_xticks([-100, -75, -50, -25, 0, 25, 50, 75, 100])
        ax.set_xlabel("← Laki-laki      % dalam kelompok      Perempuan →")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{abs(v):.0f}%"))
    else:
        ax.set_xlabel("← Laki-laki      Jumlah catatan skrining      Perempuan →")
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_ribuan))
        ax.margins(x=0.10)
    ax.set_title(
        f"{penyakit}  —  siapa yang ditandai berisiko\n"
        f"usia {d['usia_label']}  |  n = {_ribuan(d['n'])}  |  "
        f"prevalensi {d['prevalensi'] * 100:.2f}%",
        fontsize=13, fontweight="bold", color=NAVY, loc="left")
    ax.legend(frameon=False, fontsize=10, ncols=2, loc="lower right")
    _rapikan(ax)
    fig.tight_layout()
    return fig


# Jenis kelamin TIDAK boleh dibedakan dengan warna di sini: oranye dan hijau
# sudah dipakai untuk kelas risiko dan akan terbaca "laki-laki = berisiko",
# sedangkan mengambil dua langkah dari tangga navy melanggar aturan tangga
# sekuensial itu sendiri. Jadi pembedanya bentuk: gaya garis + bentuk penanda +
# label langsung di ujung garis. Ini mengikuti preseden theme.py, yang menolak
# hijau-vs-abu (dE 14,2) lalu menggantinya dengan garis putus-putus, bukan warna.
GAYA_DESIL = {
    "gabungan":  {"ls": "-",  "marker": "o", "label": "Semua"},
    "L":         {"ls": "--", "marker": "s", "label": "Laki-laki"},
    "P":         {"ls": ":",  "marker": "^", "label": "Perempuan"},
}


def figur_kurva_desil(a: dict, penyakit: str, var: str,
                      pisah_jk: bool = False,
                      nilai_pengguna: float | None = None):
    """
    Prevalensi menurut desil sebuah variabel.

    Desil membagi peserta menjadi sepuluh kelompok sama besar menurut variabel
    ini, lalu tiap titik menunjukkan persentase Berisiko di dalam kelompoknya.
    Karena tiap titik disandarkan pada jumlah baris yang mirip, kurvanya boleh
    dibaca sebagai "risiko naik/turun mengikuti variabel" -- berbeda dari
    histogram jumlah yang lebih dulu dipengaruhi besar kelompoknya.

    JUMLAHNYA BELUM TENTU SEPULUH. Tinggibadan dicatat kelipatan 5 cm sehingga
    beberapa batas desil runtuh dan hanya sembilan yang terbentuk. Semua array
    dibaca apa adanya dari analysis.json, tidak ada yang mengasumsikan 10.

    Tampilan `pisah_jk` adalah peragaan langsung perancu catatan analisis 3.10: pada
    Kanker Paru x Tinggibadan garis gabungan menanjak 3,99% -> 25,41%, tetapi
    begitu dipisah, kedua garisnya mendatar. Tingginya menandai jenis kelamin,
    bukan risikonya.
    """
    d = a["penyakit"][penyakit]
    v = d["variabel"][var]
    x = np.asarray(v["desil_x"], dtype=float)
    prev = np.asarray(v["desil_prev"], dtype=float)
    n_d = v["desil_n"]

    fig, ax = plt.subplots(figsize=(13, 4.8))

    # Garis prevalensi keseluruhan: navy putus-putus. Konvensi yang sama
    # dipakai T.bar_probabilitas untuk garis acuan, jadi tidak ada kosakata
    # visual baru yang perlu dipelajari pembaca.
    ax.axhline(d["prevalensi"] * 100, color=NAVY, lw=1.4, ls=(0, (6, 4)),
               alpha=0.8)
    ax.annotate(f"prevalensi keseluruhan {d['prevalensi'] * 100:.2f}%",
                xy=(0.995, d["prevalensi"] * 100), xycoords=("axes fraction", "data"),
                xytext=(0, 5), textcoords="offset points", ha="right",
                fontsize=9, color=NAVY)

    seri = [("gabungan", prev)]
    if pisah_jk:
        seri += [(s, np.array([np.nan if p_ is None else p_
                               for p_ in v["desil_jk"][s]["prev"]], dtype=float))
                 for s in ("L", "P")]

    for kunci, nilai in seri:
        g = GAYA_DESIL[kunci]
        ax.plot(x, nilai, color=NAVY, lw=2.4 if kunci == "gabungan" else 2.0,
                ls=g["ls"], marker=g["marker"], markersize=6,
                markerfacecolor="white" if kunci != "gabungan" else NAVY,
                label=g["label"])
        # Label langsung di ujung garis -- lebih mudah diikuti daripada
        # legenda ketika ketiga garisnya sewarna.
        if pisah_jk:
            ax.annotate(f" {g['label']}", xy=(x[-1], nilai[-1]),
                        xytext=(6, 0), textcoords="offset points",
                        va="center", fontsize=9.5, color=NAVY,
                        fontweight="bold" if kunci == "gabungan" else "normal")

    # Pita kosong di bawah nol, khusus untuk angka jumlah baris. Tanpa pita
    # ini angka-angka itu menempel pada garis yang paling rendah (pada Kanker
    # Paru garis Perempuan hanya di 2-3%), dan tanpa rotasi mereka bertindihan
    # satu sama lain -- median desil Tinggibadan bisa hanya berjarak 1 cm.
    # Tick negatif dibuang supaya sumbu y tidak pernah menampilkan persen minus.
    ymax = float(np.nanmax(np.concatenate([np.asarray(n, dtype=float)
                                           for _, n in seri])))
    pita = ymax * 0.18
    ax.set_ylim(-pita, ymax * 1.15)
    ax.set_yticks([t for t in ax.get_yticks() if 0 <= t <= ymax * 1.15])

    # Jumlah baris tiap desil. Tanpa ini, desil berisi 6.600 baris terbaca
    # sama kuatnya dengan desil berisi 30.000 baris.
    for xi, ni in zip(x, n_d):
        # bbox putih supaya garis "Anda" yang membelah sumbu tidak memotong
        # angka ini bila kebetulan jatuh tepat di atas salah satu desil.
        ax.annotate(_ribuan(ni), xy=(xi, -pita * 0.52), ha="center", va="center",
                    rotation=90, fontsize=7.5, color=T.ABU_GRAFIK, zorder=8,
                    bbox=dict(facecolor="white", edgecolor="none", pad=1.0))

    if nilai_pengguna is not None and v["xlim"][0] <= nilai_pengguna <= v["xlim"][1]:
        ax.axvline(nilai_pengguna, color=NAVY, lw=2.2)
        # Di sepertiga kanan sumbu, label dipindah ke sisi kiri garis: di sana
        # sudah ada label ujung tiap garis dan keduanya akan bertumpuk.
        di_kanan = nilai_pengguna > v["xlim"][0] + 0.7 * (v["xlim"][1] - v["xlim"][0])
        ax.text(nilai_pengguna, 0.97, "Anda " if di_kanan else " Anda",
                transform=ax.get_xaxis_transform(),
                ha="right" if di_kanan else "left", va="top",
                fontsize=10, color=NAVY, fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.5))
        # Cincin pada titik desil yang memuat nilai itu -- dicari lewat tepi
        # desil, bukan ditebak dari jarak terdekat.
        i = int(np.clip(np.searchsorted(v["desil_tepi"], nilai_pengguna,
                                        side="left") - 1, 0, len(x) - 1))
        ax.plot(x[i], prev[i], marker="o", markersize=15, markerfacecolor="none",
                markeredgecolor=NAVY_TUA, markeredgewidth=2.2, zorder=6)

    ax.set_xlim(*v["xlim"])
    ax.set_xlabel(f"{var}   (titik = nilai tengah tiap desil; "
                  f"angka kecil = jumlah baris di desil itu)")
    ax.set_ylabel("% Berisiko")
    ax.set_title(
        f"{penyakit}  —  {var}\n"
        f"prevalensi per desil  |  {len(x)} desil  |  n = {_ribuan(d['n'])}  |  "
        f"r = {v['r']:+.3f}  [{v['tafsir']}]",
        fontsize=13, fontweight="bold", color=NAVY, loc="left")
    _rapikan(ax)
    fig.tight_layout()
    return fig


# --------------------------------------------------------------------------
# 1d. Kookurensi penanda
# --------------------------------------------------------------------------
def figur_kookurensi(a: dict, kode: str):
    """
    Berapa penanda "Berisiko" yang dipegang satu catatan sekaligus.

    Strata ditentukan oleh POLA PERTANYAAN YANG DIAJUKAN, bukan pita usia, dan
    seluruh label dibaca dari data (n_ditanya, rentang usia, denominator).
    Karena itu sumbu x-nya berbunyi "dari 3 pertanyaan yang diajukan" pada
    kelompok 15-44 dan "dari 4" pada kelompok 45+, dan tidak mungkin salah
    menulis "dari 4 penyakit" untuk kelompok yang hanya ditanyai tiga.

    Batang memakai tangga navy, BUKAN oranye/hijau. Di grafik ini oranye akan
    terbaca "makin banyak penyakit = makin oranye = makin berisiko", padahal
    oranye di seluruh dashboard berarti satu hal saja: kelas Berisiko.
    """
    s = next(x for x in a["kookurensi"]["strata"] if x["kode"] == kode)
    m = s["n_ditanya"]
    k = np.arange(m + 1)
    persen = np.asarray(s["persen"], dtype=float)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 4.8),
                                   width_ratios=[1.35, 1])

    warna = [CMAP_NAVY(i / max(m, 1)) for i in k]
    ax1.bar(k, persen, color=warna, width=0.68)
    for ki, pi, ji in zip(k, persen, s["jumlah"]):
        ax1.annotate(f"{pi:.1f}%\n{_ribuan(ji)}", xy=(ki, pi),
                     xytext=(0, 5), textcoords="offset points", ha="center",
                     fontsize=9, color=T.ABU_TUA)

    # Harapan bila keempat penanda saling bebas -- lingkaran BERONGGA, sekali
    # lagi garis tepi dan bukan warna. Jaraknya terhadap batang adalah ukuran
    # penumpukan; ia bukan model dan tidak menyatakan sebab-akibat.
    ax1.plot(k, s["harapan_bebas"], linestyle="none", marker="o", markersize=11,
             markerfacecolor="none", markeredgecolor=NAVY_TUA, markeredgewidth=2,
             label="bila penanda saling bebas")

    ax1.set_xticks(k)
    ax1.set_xlabel(f"Jumlah penanda Berisiko (dari {m} pertanyaan yang diajukan)")
    ax1.set_ylabel("% catatan dalam kelompok ini")
    ax1.set_title("Sebaran jumlah penanda", fontsize=11.5, color=NAVY, loc="left")
    ax1.legend(frameon=False, fontsize=9.5, loc="upper right")
    ax1.margins(y=0.22)
    _rapikan(ax1)

    nilai = np.array([[s["pasangan"][i][j] / s["n"] * 100 for j in range(m)]
                      for i in range(m)], dtype=float)
    peny = [NAMA_PENDEK.get(p, p) for p in s["penyakit"]]
    norm = plt.Normalize(float(nilai.min()), float(nilai.max()))
    _sel_peta(ax2, nilai, peny, peny, CMAP_NAVY, norm, ".1f")
    ax2.set_title("% yang ditandai KEDUANYA (diagonal = penyakit itu sendiri)",
                  fontsize=11.5, color=NAVY, loc="left")

    fig.suptitle(
        f"Denominator: {_ribuan(s['n'])} catatan yang mendapat {m} dari 4 "
        f"pertanyaan  ·  usia {s['usia_min']}–{s['usia_max']}",
        fontsize=12.5, fontweight="bold", color=NAVY, x=0.006, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    return fig


# --------------------------------------------------------------------------
# 2. Histogram + KDE untuk satu penyakit / satu variabel
# --------------------------------------------------------------------------


def figur_histogram_kde(a: dict, penyakit: str, var: str,
                        tampilkan: str = "Keduanya",
                        nilai_pengguna: float | None = None):
    """
    Satu histogram kepadatan dengan garis KDE di atasnya.

    `tampilkan` = "Keduanya" | "Berisiko" | "Tidak Berisiko".

    Histogram dan KDE sama-sama kepadatan, jadi keduanya berbagi sumbu y dan
    boleh ditumpuk. Kurva KDE dihitung lebih dulu oleh build_analysis.py pada
    seluruh baris yang memenuhi syarat.

    Catatan pembacaan: Tinggibadan, Berat Badan, dan Usia dicatat dalam
    pembulatan (tinggi umumnya kelipatan 5 cm), sehingga histogramnya berbentuk
    deretan paku pada nilai-nilai bulat itu. Dengan ratusan ribu baris, lebar pita
    Scott menjadi sangat sempit, jadi **KDE ikut mengikuti paku itu, bukan
    meratakannya** -- kurvanya bergelombang mengikuti kelipatan 5 cm. Itu jujur:
    pengelompokan tersebut memang ada di data.

    Gunanya KDE di sini bukan menghaluskan pembulatan, melainkan membuat bentuk
    kedua kelas bisa dibandingkan sebagai dua garis. Batang transparan yang saling
    bertumpuk sulit dibaca; garisnya langsung memperlihatkan, misalnya, bahwa
    puncak kelompok Tidak Berisiko ada di 150-155 cm sedangkan Berisiko di
    160-170 cm.
    """
    d = a["penyakit"][penyakit]
    v = d["variabel"][var]
    lo, hi = v["xlim"]
    tepi = np.asarray(v["bins"], dtype=float)
    lebar_bin = np.diff(tepi)
    grid = np.asarray(v["kde"]["grid"], dtype=float)

    kelas = KELAS if tampilkan == "Keduanya" else (tampilkan,)

    # Streamlit MEMOTONG setiap gambar pada MAXIMUM_CONTENT_WIDTH = 2*730 = 1460 px,
    # berapa pun dpi-nya. Karena itu dpi figur tidak diutak-atik di sini; yang
    # penting st.pyplot dipanggil dengan use_container_width=False supaya gambar
    # 1460 px tidak diregangkan melebihi ukuran aslinya pada layar lebar.
    #
    # Diverifikasi di browser 10 Agustus: naturalWidth gambar ini memang 1460.
    # Jangan tertipu oleh fig.savefig(dpi=100) di luar Streamlit, yang hanya
    # menghasilkan 1300 px -- Streamlit menggambar ulang pada 2x untuk layar
    # rapat (devicePixelRatio 2), jadi 13 inci menjadi ~2548 px lalu DIPOTONG
    # ke 1460.
    fig, ax = plt.subplots(figsize=(13, 5.6))

    for lbl in kelas:
        warna = WARNA_KELAS[lbl]
        ax.bar(tepi[:-1], v["hist"][lbl], width=lebar_bin, align="edge",
               alpha=0.40, color=warna, linewidth=0,
               label=f"{lbl} (histogram)")
        kurva = v["kde"][lbl]
        if kurva is not None:
            ax.plot(grid, kurva, color=warna, lw=2.6,
                    label=f"{lbl} (KDE)")

    if nilai_pengguna is not None and lo <= nilai_pengguna <= hi:
        ax.axvline(nilai_pengguna, color=NAVY, lw=2.2)
        ax.text(nilai_pengguna, 0.97, " Anda",
                transform=ax.get_xaxis_transform(), ha="left", va="top",
                fontsize=10, color=NAVY, fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1.5))

    ax.set_xlim(lo, hi)
    ax.set_xlabel(var)
    ax.set_ylabel("kepadatan")
    ax.set_title(
        f"{penyakit}  —  {var}\n"
        f"usia {d['usia_label']}  |  n = {_ribuan(d['n'])}  |  "
        f"r = {v['r']:+.3f}  [{v['tafsir']}]",
        fontsize=13, fontweight="bold", color=NAVY, loc="left")
    ax.legend(frameon=False, fontsize=10)
    ax.grid(True, which="major", color=T.GARIS, alpha=0.9, linewidth=0.8)
    ax.grid(True, which="minor", color=T.GARIS, alpha=0.45, linewidth=0.5)
    ax.minorticks_on()
    ax.set_axisbelow(True)
    for sisi in ("top", "right"):
        ax.spines[sisi].set_visible(False)

    fig.tight_layout()
    return fig
