"""
Gaya visual bersama untuk seluruh notebook Skrining Bantul 2025.

Dipakai oleh kelima notebook supaya ukuran gambar, ukuran huruf, dan makna warna
konsisten di seluruh laporan -- serta supaya perubahan gaya cukup dilakukan di
satu tempat.

Pemakaian di awal tiap notebook:

    import viz_style as vz
    vz.apply_style()

KEBIJAKAN UKURAN GAMBAR
-----------------------
Gunakan konstanta di bawah alih-alih menulis angka figsize langsung:

    FIG_SINGLE = (14, 7)     satu panel
    FIG_WIDE   = (16, 6)     satu panel melebar (deret waktu, bar panjang)
    FIG_2X2    = (16, 11)    kisi 2x2
    FIG_2X4    = (24, 12)    kisi 2x4
    FIG_1X2    = (17, 7)     dua panel berdampingan

Deret 1x4 yang padat sebaiknya diubah menjadi kisi 2x2: luas tiap panel menjadi
sekitar tiga kali lipat tanpa membuat notebook terasa jauh lebih panjang.
"""

from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

__all__ = [
    "apply_style",
    "annotate_bars",
    "thousands",
    "PALETTE",
    "FIG_SINGLE", "FIG_WIDE", "FIG_1X2", "FIG_2X2", "FIG_2X4",
]

# --------------------------------------------------------------------------
# Ukuran gambar baku
# --------------------------------------------------------------------------
FIG_SINGLE = (14, 7)
FIG_WIDE = (16, 6)
FIG_1X2 = (17, 7)
FIG_2X2 = (16, 11)
FIG_2X4 = (24, 12)


# --------------------------------------------------------------------------
# Palet warna bersama -- satu makna warna di seluruh laporan
# --------------------------------------------------------------------------
PALETTE = {
    # Jenis kelamin
    "SEX": {"L": "#4A90D9", "P": "#E8748C"},

    # Label risiko pada data mentah (tiga kemungkinan)
    "RISK": {
        "Berisiko": "#D62728",
        "Tidak Berisiko": "#2CA02C",
        "Tidak Dapat Pertanyaan": "#8C8C8C",
    },

    # Model
    "MODEL": {
        "dummy": "#9E9E9E",
        "logistic": "#1F77B4",
        "decision_tree": "#FF7F0E",
        "xgboost": "#2CA02C",
        "stacking": "#9467BD",
    },

    # Status gizi ringkas (WHO-4)
    "WHO4": {
        "Underweight": "#6BAED6",
        "Normal": "#74C476",
        "Overweight": "#FD8D3C",
        "Obese": "#DE2D26",
    },

    # Sebelum vs sesudah pembersihan
    "BEFORE": "#F08080",
    "AFTER": "#3CB371",

    # Wilayah. Dipakai KONSISTEN di seluruh notebook perbandingan supaya satu
    # warna selalu berarti satu kabupaten.
    #
    # Warnanya sengaja diambil dari palet dashboard yang sudah diuji kontras
    # (Dashboard/theme.py): navy #153763 dan oranye #C96F0F, keduanya lulus
    # ambang 3:1 terhadap kartu putih. Merah/hijau TIDAK dipakai di sini karena
    # sudah bermakna Berisiko/Tidak Berisiko pada PALETTE["RISK"] -- memakai
    # ulang keduanya untuk wilayah akan membuat legenda saling bertabrakan.
    "WILAYAH": {
        "Bantul": "#153763",
        "Sleman": "#C96F0F",
        "Gabungan": "#6B7280",
    },
}


# --------------------------------------------------------------------------
# Penerapan gaya
# --------------------------------------------------------------------------

def apply_style(base_scale: float = 1.0) -> None:
    """
    Terapkan gaya baku untuk seluruh grafik.

    base_scale menaikkan/menurunkan seluruh ukuran huruf secara proporsional
    (mis. 1.15 bila notebook ditampilkan pada layar besar).
    """
    sns.set_theme(style="whitegrid")

    s = base_scale
    plt.rcParams.update({
        # --- ukuran & resolusi ---
        "figure.figsize": FIG_SINGLE,
        "figure.dpi": 110,
        "savefig.dpi": 140,
        "savefig.bbox": "tight",

        # --- huruf ---
        "font.size": 12 * s,
        "axes.titlesize": 14 * s,
        "axes.labelsize": 12.5 * s,
        "xtick.labelsize": 11 * s,
        "ytick.labelsize": 11 * s,
        "legend.fontsize": 11 * s,
        "figure.titlesize": 16 * s,

        # --- tata letak ---
        "axes.titlepad": 12,
        "axes.labelpad": 8,
        # "bold", bukan "semibold": font bawaan matplotlib (DejaVu Sans) tidak punya
        # varian semibold, sehingga memicu peringatan findfont di setiap grafik.
        "axes.titleweight": "bold",

        # --- kisi & bingkai ---
        "axes.grid": True,
        "grid.alpha": 0.3,
        "grid.linewidth": 0.8,
        "axes.edgecolor": "#666666",
        "axes.linewidth": 0.9,

        # --- legenda ---
        "legend.frameon": True,
        "legend.framealpha": 0.9,
        "legend.edgecolor": "#CCCCCC",

        # --- garis ---
        "lines.linewidth": 2.0,
        "lines.markersize": 6,
    })


# --------------------------------------------------------------------------
# Pembantu anotasi
# --------------------------------------------------------------------------

def annotate_bars(ax, fmt="{:,.0f}", pct_of=None, fontsize=10, pad=0.01,
                  horizontal=False):
    """
    Tulis nilai di ujung tiap batang.

    fmt        : format angka utama, mis. "{:,.0f}" atau "{:.1f}%"
    pct_of     : bila diisi angka, tambahkan persentase terhadap nilai itu
                 pada baris kedua (mis. total baris data)
    horizontal : True untuk barh (label ditulis di kanan batang)

    Mengembalikan ax supaya bisa dirangkai.
    """
    if horizontal:
        span = max((p.get_width() for p in ax.patches), default=0)
    else:
        span = max((p.get_height() for p in ax.patches), default=0)
    offset = span * pad

    for p in ax.patches:
        val = p.get_width() if horizontal else p.get_height()
        if val == 0:
            continue

        label = fmt.format(val)
        if pct_of:
            label += f"\n({val / pct_of * 100:.1f}%)"

        if horizontal:
            ax.text(val + offset, p.get_y() + p.get_height() / 2, label,
                    va="center", ha="left", fontsize=fontsize)
        else:
            ax.text(p.get_x() + p.get_width() / 2, val + offset, label,
                    ha="center", va="bottom", fontsize=fontsize)

    # Beri ruang supaya label tidak terpotong tepi gambar.
    ax.margins(x=0.12 if horizontal else 0.02,
               y=0.02 if horizontal else 0.15)
    return ax


def thousands(ax, axis="y"):
    """Pemisah ribuan pada label sumbu (1,234,567). Mengembalikan ax."""
    fmtr = mticker.FuncFormatter(lambda x, _: f"{abs(int(x)):,}")
    if axis in ("y", "both"):
        ax.yaxis.set_major_formatter(fmtr)
    if axis in ("x", "both"):
        ax.xaxis.set_major_formatter(fmtr)
    return ax
