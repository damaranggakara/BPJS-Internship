"""
Dashboard Prediksi Risiko Penyakit Kronis -- antarmuka desktop (Tkinter).

Seluruh logika ada di predictor.py; berkas ini hanya menampilkan.

Cara pakai:
    python Dashboard/app_tkinter.py
"""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import predictor as P  # noqa: E402

# Warna
# Palet disamakan dengan theme.py (gaya deck BPJS) supaya kedua antarmuka
# terlihat sekeluarga. Tata letak sengaja TIDAK diubah -- versi desktop ini
# adalah cadangan tanpa pemasangan apa pun.
BG = "#f9fbfe"
KARTU = "#ffffff"
GARIS = "#d7e0eb"
TEKS = "#1a1a1a"
REDUP = "#6b7280"
RISIKO = "#c96f0f"   # oranye, dipakai untuk "Berisiko" dan pesan galat
HIJAU = "#2d8746"    # "Tidak Berisiko"
BIRU = "#153763"     # navy utama
KUNING = "#7a4408"   # teks catatan penting

F_JUDUL = ("Segoe UI", 16, "bold")
F_SUB = ("Segoe UI", 10)
F_LABEL = ("Segoe UI", 10)
F_KARTU = ("Segoe UI", 11, "bold")
F_KECIL = ("Segoe UI", 9)
F_ANGKA = ("Segoe UI", 20, "bold")


class Dashboard(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Dashboard Prediksi Risiko Penyakit Kronis - Skrining Bantul & Sleman 2025")
        self.geometry("1060x760")
        self.minsize(940, 640)
        self.configure(bg=BG)

        self.wilayah_list = P.wilayah_tersedia()
        if not self.wilayah_list:
            self._layar_error("Belum ada model yang diekspor. Jalankan: python Gabungan/Dashboard/train_export.py")
            return
        # Wilayah terakhir = Gabungan bila sudah ada.
        self.v_wilayah = tk.StringVar(value=self.wilayah_list[-1])
        self.v_asal = tk.StringVar(value="Bantul")
        try:
            self.segmen_list = P.segmen_tersedia(self.v_wilayah.get())
        except FileNotFoundError as e:
            self._layar_error(str(e))
            return

        self._bangun_kepala()
        badan = tk.Frame(self, bg=BG)
        badan.pack(fill="both", expand=True, padx=16, pady=(0, 12))
        self._bangun_form(badan)
        self._bangun_hasil(badan)
        self._pesan_awal()

    # ------------------------------------------------------------------ #
    def _layar_error(self, pesan: str) -> None:
        f = tk.Frame(self, bg=BG)
        f.pack(fill="both", expand=True, padx=40, pady=40)
        tk.Label(f, text="Model belum tersedia", font=F_JUDUL, bg=BG,
                 fg=RISIKO).pack(anchor="w")
        tk.Label(f, text=pesan, font=F_SUB, bg=BG, fg=TEKS, justify="left",
                 wraplength=800).pack(anchor="w", pady=12)

    def _bangun_kepala(self) -> None:
        kepala = tk.Frame(self, bg=BG)
        kepala.pack(fill="x", padx=16, pady=(14, 8))
        tk.Label(kepala, text="Dashboard Prediksi Risiko Penyakit Kronis",
                 font=F_JUDUL, bg=BG, fg=TEKS).pack(anchor="w")
        self.lbl_wilayah = tk.Label(
            kepala, text=f"Skrining {self.v_wilayah.get()} 2025",
            font=F_SUB, bg=BG, fg=REDUP)
        self.lbl_wilayah.pack(anchor="w")

        kotak = tk.Frame(self, bg="#fdf4e8", highlightbackground="#f0c99a",
                         highlightthickness=1)
        kotak.pack(fill="x", padx=16, pady=(6, 10))
        tk.Label(kotak, text=P.DISCLAIMER, font=F_KECIL, bg="#fdf4e8",
                 fg=KUNING, justify="left", wraplength=1000).pack(
            anchor="w", padx=10, pady=8)

    # ------------------------------------------------------------------ #
    def _bangun_form(self, induk: tk.Frame) -> None:
        kartu = tk.Frame(induk, bg=KARTU, highlightbackground=GARIS,
                         highlightthickness=1)
        kartu.pack(side="left", fill="y", padx=(0, 12))
        dalam = tk.Frame(kartu, bg=KARTU)
        dalam.pack(fill="both", expand=True, padx=18, pady=16)

        # Pemilih wilayah: menentukan model DAN daftar segmen.
        tk.Label(dalam, text="Wilayah", font=F_KARTU, bg=KARTU,
                 fg=TEKS).pack(anchor="w", pady=(0, 6))
        ttk.Combobox(dalam, textvariable=self.v_wilayah,
                     values=self.wilayah_list, state="readonly",
                     width=24, font=F_LABEL).pack(anchor="w", pady=(2, 4))
        tk.Label(dalam, text="Kabupaten skrining (hanya untuk model Gabungan)",
                 font=F_KECIL, bg=KARTU, fg=REDUP).pack(anchor="w")
        ttk.Combobox(dalam, textvariable=self.v_asal,
                     values=["Bantul", "Sleman"], state="readonly",
                     width=24, font=F_LABEL).pack(anchor="w", pady=(2, 10))

        tk.Label(dalam, text="Data Diri", font=F_KARTU, bg=KARTU,
                 fg=TEKS).pack(anchor="w", pady=(0, 12))

        # Jenis kelamin
        tk.Label(dalam, text="Jenis kelamin", font=F_LABEL, bg=KARTU,
                 fg=TEKS).pack(anchor="w")
        self.v_jk = tk.StringVar(value="L")
        baris_jk = tk.Frame(dalam, bg=KARTU)
        baris_jk.pack(anchor="w", pady=(2, 12))
        for nilai, teks in (("L", "Laki-laki"), ("P", "Perempuan")):
            tk.Radiobutton(baris_jk, text=teks, value=nilai, variable=self.v_jk,
                           font=F_LABEL, bg=KARTU, fg=TEKS,
                           activebackground=KARTU,
                           selectcolor=KARTU).pack(side="left", padx=(0, 14))

        self.v_usia = self._entri(dalam, "Usia (tahun)", "30")
        self.v_tinggi = self._entri(dalam, "Tinggi badan (cm)", "170")
        self.v_berat = self._entri(dalam, "Berat badan (kg)", "65")

        # Segmen
        tk.Label(dalam, text="Segmen kepesertaan BPJS", font=F_LABEL,
                 bg=KARTU, fg=TEKS).pack(anchor="w")
        self.v_segmen = tk.StringVar(value=self.segmen_list[0])
        ttk.Combobox(dalam, textvariable=self.v_segmen, values=self.segmen_list,
                     state="readonly", width=24, font=F_LABEL).pack(
            anchor="w", pady=(2, 4))
        tk.Label(dalam, text="Dibutuhkan model -- termasuk penentu risiko TBC.",
                 font=F_KECIL, bg=KARTU, fg=REDUP, justify="left",
                 wraplength=230).pack(anchor="w", pady=(0, 16))

        tk.Button(dalam, text="Hitung Risiko", font=("Segoe UI", 11, "bold"),
                  bg=BIRU, fg="white", activebackground="#15405f",
                  activeforeground="white", relief="flat", cursor="hand2",
                  command=self.hitung).pack(fill="x", ipady=7)

        self.lbl_error = tk.Label(dalam, text="", font=F_KECIL, bg=KARTU,
                                  fg=RISIKO, justify="left", wraplength=230)
        self.lbl_error.pack(anchor="w", pady=(10, 0))

        for w in (self.v_usia, self.v_tinggi, self.v_berat):
            w.bind("<Return>", lambda _e: self.hitung())

    def _entri(self, induk: tk.Frame, label: str, awal: str) -> tk.Entry:
        tk.Label(induk, text=label, font=F_LABEL, bg=KARTU,
                 fg=TEKS).pack(anchor="w")
        e = tk.Entry(induk, font=F_LABEL, width=26, relief="solid", bd=1)
        e.insert(0, awal)
        e.pack(anchor="w", pady=(2, 12), ipady=3)
        return e

    # ------------------------------------------------------------------ #
    def _bangun_hasil(self, induk: tk.Frame) -> None:
        bungkus = tk.Frame(induk, bg=BG)
        bungkus.pack(side="left", fill="both", expand=True)

        self.kanvas = tk.Canvas(bungkus, bg=BG, highlightthickness=0)
        bar = ttk.Scrollbar(bungkus, orient="vertical",
                            command=self.kanvas.yview)
        self.isi = tk.Frame(self.kanvas, bg=BG)

        self.isi.bind("<Configure>", lambda _e: self.kanvas.configure(
            scrollregion=self.kanvas.bbox("all")))
        self.jendela = self.kanvas.create_window((0, 0), window=self.isi,
                                                 anchor="nw")
        self.kanvas.bind("<Configure>", lambda e: self.kanvas.itemconfig(
            self.jendela, width=e.width))
        self.kanvas.configure(yscrollcommand=bar.set)

        self.kanvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.kanvas.bind_all("<MouseWheel>", self._gulir)

    def _gulir(self, event) -> None:
        self.kanvas.yview_scroll(int(-event.delta / 120), "units")

    def _bersihkan(self) -> None:
        for w in self.isi.winfo_children():
            w.destroy()

    def _pesan_awal(self) -> None:
        self._bersihkan()
        k = self._kartu()
        tk.Label(k, text="Isi data diri di sebelah kiri, lalu tekan "
                         "\"Hitung Risiko\".", font=F_SUB, bg=KARTU, fg=REDUP,
                 justify="left", wraplength=640).pack(anchor="w", padx=16,
                                                      pady=16)

    def _kartu(self) -> tk.Frame:
        k = tk.Frame(self.isi, bg=KARTU, highlightbackground=GARIS,
                     highlightthickness=1)
        k.pack(fill="x", pady=(0, 10))
        return k

    # ------------------------------------------------------------------ #
    def hitung(self) -> None:
        self.lbl_error.config(text="")
        try:
            usia = int(float(self.v_usia.get().strip().replace(",", ".")))
            tinggi = float(self.v_tinggi.get().strip().replace(",", "."))
            berat = float(self.v_berat.get().strip().replace(",", "."))
        except ValueError:
            self.lbl_error.config(
                text="Usia, tinggi, dan berat harus berupa angka.")
            return

        wilayah = self.v_wilayah.get()
        self.lbl_wilayah.config(text=f"Skrining {wilayah} 2025")
        hasil = P.prediksi(usia, self.v_jk.get(), tinggi, berat,
                           self.v_segmen.get(), wilayah=wilayah,
                           asal=self.v_asal.get())

        if not hasil.valid:
            self.lbl_error.config(text=hasil.error)
            self._bersihkan()
            k = self._kartu()
            tk.Label(k, text="Masukan belum dapat diproses", font=F_KARTU,
                     bg=KARTU, fg=RISIKO).pack(anchor="w", padx=16, pady=(14, 4))
            tk.Label(k, text=hasil.error, font=F_SUB, bg=KARTU, fg=TEKS,
                     justify="left", wraplength=640).pack(
                anchor="w", padx=16, pady=(0, 14))
            return

        self._tampilkan(hasil)

    def _tampilkan(self, hasil: P.HasilPrediksi) -> None:
        self._bersihkan()

        # --- kartu IMT ---
        k = self._kartu()
        d = tk.Frame(k, bg=KARTU)
        d.pack(fill="x", padx=16, pady=14)
        tk.Label(d, text="Indeks Massa Tubuh (IMT)", font=F_KARTU, bg=KARTU,
                 fg=TEKS).pack(anchor="w")
        tk.Label(d, text=f"{hasil.imt:.1f}", font=F_ANGKA, bg=KARTU,
                 fg=BIRU).pack(anchor="w", pady=(4, 0))
        tk.Label(d, text=f"Kategori: {hasil.kategori_who8}", font=F_SUB,
                 bg=KARTU, fg=TEKS).pack(anchor="w")
        if hasil.kategori_who4 != hasil.kategori_who8:
            tk.Label(d, text=f"Ringkas: {hasil.kategori_who4}", font=F_KECIL,
                     bg=KARTU, fg=REDUP).pack(anchor="w")
        if hasil.kategori_who8 == P.bs.LABEL_BALITA:
            tk.Label(d, text="IMT-menurut-usia tidak berlaku secara medis di "
                             "bawah 2 tahun, sehingga kategori tidak diberikan.",
                     font=F_KECIL, bg=KARTU, fg=REDUP, justify="left",
                     wraplength=620).pack(anchor="w", pady=(4, 0))

        # --- hasil per penyakit ---
        for p in hasil.penyakit:
            self._kartu_penyakit(p)

    def _kartu_penyakit(self, p: P.HasilPenyakit) -> None:
        k = self._kartu()
        d = tk.Frame(k, bg=KARTU)
        d.pack(fill="x", padx=16, pady=13)

        atas = tk.Frame(d, bg=KARTU)
        atas.pack(fill="x")
        tk.Label(atas, text=p.nama, font=F_KARTU, bg=KARTU,
                 fg=TEKS).pack(side="left")

        if not p.layak:
            tk.Label(atas, text="TIDAK BERLAKU", font=F_KECIL, bg=KARTU,
                     fg=REDUP).pack(side="right")
            tk.Label(d, text=p.alasan, font=F_KECIL, bg=KARTU, fg=REDUP,
                     justify="left", wraplength=620).pack(anchor="w",
                                                          pady=(6, 0))
            return

        warna = RISIKO if p.label == "Berisiko" else HIJAU
        tk.Label(atas, text=p.label.upper(), font=("Segoe UI", 11, "bold"),
                 bg=KARTU, fg=warna).pack(side="right")

        tk.Label(d, text=f"Probabilitas: {p.probabilitas * 100:.1f}%",
                 font=("Segoe UI", 13, "bold"), bg=KARTU, fg=warna).pack(
            anchor="w", pady=(6, 4))

        # bar probabilitas
        bar_luar = tk.Frame(d, bg="#e6ebf0", height=8)
        bar_luar.pack(fill="x", pady=(0, 8))
        bar_luar.pack_propagate(False)
        isi = tk.Frame(bar_luar, bg=warna, height=8)
        isi.place(relwidth=max(0.005, min(1.0, p.probabilitas)), relheight=1)

        m = p.metrik
        tk.Label(d, text=(f"Model: {p.model}  |  berlaku usia {p.usia_label}  |  "
                          f"Akurasi {m['Accuracy']:.3f}  ROC-AUC {m['ROC-AUC']:.3f}"),
                 font=F_KECIL, bg=KARTU, fg=REDUP).pack(anchor="w")

        for c in p.catatan:
            tk.Label(d, text="- " + c, font=F_KECIL, bg=KARTU,
                     fg=KUNING if c.startswith("PENTING") else REDUP,
                     justify="left", wraplength=620).pack(anchor="w",
                                                          pady=(6, 0))


if __name__ == "__main__":
    Dashboard().mainloop()
