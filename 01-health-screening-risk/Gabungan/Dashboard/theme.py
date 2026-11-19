"""
Tema visual dashboard -- palet, CSS, dan pembangun grafik.

Gaya diambil dari deck presentasi BPJS (navy tua, hijau, oranye, latar biru muda).
Deck dipakai HANYA sebagai acuan visual; seluruh ANGKA pada dashboard berasal dari
models/<wilayah>/metadata.json lewat predictor.py, tidak ada satu pun angka
dari deck.

CATATAN WARNA GRAFIK
--------------------
Warna penanda data di sini sudah diperiksa secara terhitung (bukan dikira-kira)
terhadap: pita lightness OKLCH, lantai chroma, keterpisahan buta warna
(protan/deutan, Machado 2009), lantai penglihatan normal, dan kontras WCAG.

Dua hasil pemeriksaan yang mengubah pilihan warna:

1. Oranye deck `#f08a24` hanya mencapai kontras 2,51:1 terhadap kartu putih --
   di bawah minimum 3:1. Untuk ISIAN BAR dipakai `#c96f0f` (3,64:1) yang masih
   satu keluarga warna. `#f08a24` tetap dipakai untuk aksen di atas latar
   berwarna, bukan untuk penanda data.

2. Rencana awal memakai bar abu-abu sebagai pembanding prevalensi populasi.
   Hijau `#2d8746` vs abu `#6b7280` hanya berjarak dE 14,2 pada penglihatan
   normal -- di bawah lantai 15, jadi sulit dibedakan. Solusinya bukan menukar
   warna melainkan mengganti bentuk: prevalensi populasi digambar sebagai GARIS
   PUTUS-PUTUS, bukan bar kedua. Keduanya kini navy dan dibedakan oleh gaya
   garis + label + posisi, bukan oleh warna saja.

CATATAN WARNA PERMUKAAN (11 Agustus)
------------------------------------
Permukaan bernada diambil dari deck `Progres Model dan Dashboard.pptx` dan
diperiksa terhitung, bukan dicocokkan dengan mata.

ATURAN LINGKUP: hanya permukaan NON-DATA yang diberi nada. Grafik dan `.kartu`
tempat grafik berdiri tetap PUTIH, karena kelima rasio yang sudah divalidasi di
atas dan di analysis.py diukur terhadap putih, dan halo putih pada skala_imt
serta bar_probabilitas hanya terbaca sebagai halo di atas putih.

3. `ABU #6b7280` GUGUR sebagai warna teks di atas nada. Terhadap putih ia
   4,83:1, tetapi terhadap seluruh nada deck hanya 4,19-4,60:1 -- di bawah
   lantai 4,5. DUA kegagalan seperti ini sudah ada SEBELUM perubahan warna ini
   dan ikut diperbaiki: `.kartu-redup` (4,24:1) dan label pita non-aktif
   `skala_imt` di atas TRACK (4,09:1, yang terburuk). Karena itu ABU dipensiunkan
   sebagai warna teks CSS/HTML dan diganti `ABU_TUA #5b6770` (5,03-5,52:1 di atas
   nada, 5,80:1 di atas putih). ABU tersisa pada SATU tempat sah, dinamai ulang
   `ABU_GRAFIK`: teks di dalam figur matplotlib, yang latarnya putih menurut
   definisi (4,83:1).

4. Empat nada dipilih sebagai anggota TERDALAM dari keluarganya di deck, bukan
   yang pertama ditemukan. Nada deck lebih terang daripada `LATAR_TINT #ebf1f4`,
   sehingga memilih anggota tengah justru MENGURANGI keterpisahan permukaan pada
   kartu putih:
     netral     #eceff3  1,153:1 terhadap putih   (LATAR_TINT lama 1,140)
     info       #eff3fa  1,113:1
     aman       #e6f5ee  1,125:1                  (LATAR_HIJAU lama 1,095)
     peringatan #fbf3ec  1,098:1                  (#fdf4e8 lama 1,089)
   Teks di atas nada terdalam (#eceff3, kasus terburuk): TINTA 15,09 · ABU_TUA
   5,03 · NAVY 10,35. Tinta khusus: #7a4408 7,20 · #8a4c08 6,14 · #1d6234 6,55.

5. Garis tepi lembut (#9dabbd, #a8c1e6, #a7cdb1, #e8c39a) berada di 1,51-2,02:1
   terhadap nadanya sendiri. Itu DI BAWAH 3:1, dan disengaja: garis ini batas
   DEKORATIF, bukan pembawa informasi -- setiap makna yang dibawanya juga dibawa
   warna tinta dan posisi bloknya. Bandingkan `GARIS #d7e0eb` yang sudah lama
   dipakai: 1,33:1.

6. Aksen merek BPJS diambil dari seni footer templat deck: hijau `#1fa860` dan
   biru `#45669c`.

   Angka hijau harus dibaca dengan denominator yang tepat: 3,08:1 terhadap PUTIH
   MURNI, tetapi hanya **2,97:1 terhadap LATAR `#f9fbfe`** -- yaitu latar halaman
   yang sebenarnya. Ia MELESET dari lantai 3,0 di sana. `.garis-merek` karena itu
   digolongkan DEKORATIF, sama seperti garis tepi lembut pada catatan 5: ia
   ornamen merek, bukan pembawa informasi dan bukan batas komponen. Tidak ada
   makna yang hilang bila separuh hijaunya tidak terbedakan. Penggolongan ini
   ditulis di sini supaya menjadi keputusan, bukan kelalaian.

   Biru 5,78:1 terhadap putih dan 5,58:1 terhadap LATAR -- aman sebagai teks
   maupun tanda. Hijau TIDAK PERNAH boleh menjadi teks.

   Keduanya tanda MEREK, bukan makna data: tidak satu pun boleh muncul di dalam
   grafik, karena hijau di seluruh dashboard sudah berarti "Tidak Berisiko" dan
   `#316cc3` sudah menjadi garis Hipertensi.

7. Garis merek TIDAK digambar dengan `border-image`. `border-image` mematikan
   `border-radius` menurut spesifikasi, sehingga sudut header menjadi persegi,
   dan `slice 1` memotong gradien menjadi wilayah sudut + tepi sehingga
   pembagian 50/50-nya teregang menjadi bilah yang berat sebelah.

8. Garis merek juga tidak boleh berdiri DI ATAS navy. Terhadap ujung kanan
   gradien header `#2e4c7f`, biru BPJS hanya 1,48:1 dan hijau 2,78:1 -- separuh
   birunya benar-benar lenyap sehingga garisnya terbaca setengah lebar. Garis itu
   kini elemen sendiri (`.garis-merek`) di bawah header, di atas LATAR, tempat
   hijau 3,08:1 dan biru 5,78:1.

   Kedua temuan ini muncul hanya setelah tangkapan layar dilihat. Audit kontras
   sebelumnya LULUS karena mengukur biru BPJS terhadap putih dan nada -- padahal
   elemen itu berdiri di atas navy. Mengukur denominator yang salah tetap
   menghasilkan angka yang meyakinkan. Lihat resep tangkapan layar di 6.
"""

from __future__ import annotations

import html

# --------------------------------------------------------------------------
# Palet
# --------------------------------------------------------------------------
NAVY = "#153763"          # utama -- header, judul, angka penting
NAVY_800 = "#1f3559"
NAVY_700 = "#2e4c7f"
BIRU = "#316cc3"          # aksen informasi
HIJAU = "#2d8746"         # "Tidak Berisiko"        kontras 4,50:1
HIJAU_MUDA = "#2fa36b"
ORANYE = "#c96f0f"        # "Berisiko" (isian bar)  kontras 3,64:1
ORANYE_AKSEN = "#f08a24"  # aksen di atas latar berwarna, BUKAN penanda data
ABU = "#6b7280"           # LIHAT catatan 3: TIDAK BOLEH jadi warna teks CSS/HTML
ABU_GRAFIK = ABU          # satu-satunya pemakaian sah -- teks di dalam figur
                          # matplotlib, yang latarnya putih menurut definisi
ABU_TUA = "#5b6770"       # pengganti ABU untuk seluruh teks CSS/HTML
LATAR = "#f9fbfe"
LATAR_TINT = "#ebf1f4"    # tersisa untuk axvspan di analysis.py
LATAR_HIJAU = "#eef7ef"
GARIS = "#d7e0eb"
TRACK = "#e6edf4"
TINTA = "#1a1a1a"

# Permukaan bernada + garis tepi lembut, diambil dari deck
# "Progres Model dan Dashboard.pptx". Tiap keluarga diwakili anggota TERDALAM-nya
# (lihat catatan 4): nada deck lebih terang daripada LATAR_TINT, sehingga memilih
# anggota tengah justru mengurangi keterpisahan permukaan pada kartu putih.
TINT_NETRAL = "#eceff3"       # 1,153:1 terhadap putih
TINT_INFO = "#eff3fa"         # 1,113:1
TINT_AMAN = "#e6f5ee"         # 1,125:1
TINT_PERINGATAN = "#fbf3ec"   # 1,098:1

SISI_NETRAL = "#9dabbd"
SISI_INFO = "#a8c1e6"
SISI_AMAN = "#a7cdb1"
SISI_PERINGATAN = "#e8c39a"

TINTA_PERINGATAN = "#7a4408"  # 7,20:1 di atas TINT_PERINGATAN
TINTA_RISIKO = "#8a4c08"      # 6,14:1
TINTA_AMAN = "#1d6234"        # 6,55:1 di atas TINT_AMAN

# Aksen merek BPJS, diambil dari seni footer templat deck. Lihat catatan 6:
# hijau hanya boleh menjadi TANDA di atas putih -- tidak pernah teks, tidak
# pernah di atas nada, tidak pernah di dalam grafik.
BPJS_HIJAU = "#1fa860"    # 3,08:1 terhadap putih
BPJS_BIRU = "#45669c"     # 5,78:1 terhadap putih -- aman sebagai teks

FONT = '"Segoe UI", Arial, Helvetica, sans-serif'


def warna_status(berisiko: bool) -> str:
    return ORANYE if berisiko else HIJAU


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
def css() -> str:
    return f"""
<style>
  .stApp {{ background: {LATAR}; }}
  html, body, [class*="css"] {{ font-family: {FONT}; }}

  .blok-main {{ padding-top: 0.5rem; }}

  /* ---------- header ---------- */
  /* Garis merek BPJS (hijau|biru dari seni footer templat deck) digambar
     sebagai LAPISAN LATAR, bukan border-image.
     border-image mematikan border-radius menurut spesifikasi, sehingga sudut
     header menjadi persegi; dan `slice 1` memotong gradien menjadi wilayah
     sudut + tepi, sehingga pembagian 50/50-nya teregang dan terbaca seperti
     bilah kemajuan. Sebagai lapisan latar, garis ini ikut terpotong rapi oleh
     border-radius dan pembagiannya tepat separuh.
     Lapisan pertama digambar PALING ATAS. */
  .bpjs-header {{
    background: linear-gradient(135deg, {NAVY} 0%, {NAVY_700} 100%);
    color: #fff; padding: 22px 28px; border-radius: 10px 10px 0 0;
  }}
  /* Garis merek berdiri DI BAWAH header, di atas latar halaman -- bukan di
     atas navy. Terhadap navy, biru BPJS #45669c hanya 1,48:1 sehingga separuh
     birunya lenyap dan garisnya terbaca setengah lebar; hijau pun hanya 2,78:1.
     Di atas LATAR keduanya lolos: hijau 3,08:1 dan biru 5,78:1.
     Ditemukan dengan MELIHAT hasil render -- audit kontras sebelumnya mengukur
     terhadap putih dan nada, denominator yang salah untuk elemen ini. */
  .garis-merek {{
    height: 4px; border-radius: 0 0 10px 10px; margin-bottom: 18px;
    background: linear-gradient(90deg, {BPJS_HIJAU} 0 50%, {BPJS_BIRU} 50% 100%);
  }}
  .bpjs-header h1 {{
    margin: 0; font-size: 1.55rem; font-weight: 700; letter-spacing: .2px; color: #fff;
  }}
  .bpjs-header p {{ margin: 6px 0 0; font-size: .92rem; opacity: .85; }}

  /* ---------- kartu ---------- */
  /* .kartu TETAP PUTIH dan tidak boleh diberi nada: seluruh grafik berdiri di
     atasnya, dan kelima rasio yang sudah divalidasi diukur terhadap putih. */
  .kartu {{
    background: #fff; border: 1px solid {GARIS}; border-radius: 10px;
    padding: 18px 20px; margin-bottom: 14px;
  }}
  .kartu-redup {{
    background: {TINT_NETRAL}; border-style: dashed; border-color: {SISI_NETRAL};
  }}

  .label-kecil {{
    font-size: .68rem; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: {ABU_TUA}; margin-bottom: 6px;
  }}
  /* Strip kartu statistik: grid yang menyesuaikan lebar layar. st.columns
     TIDAK ikut mengecil dengan rapi -- pada layar sempit kolomnya jadi ~75px
     sehingga angka "22.0" pun terpotong menjadi dua baris. */
  .strip-statistik {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(155px, 1fr));
    gap: 12px; margin-bottom: 4px;
  }}
  .strip-statistik .kartu {{ margin-bottom: 0; }}

  .angka-besar {{
    font-size: 1.95rem; font-weight: 700; color: {NAVY}; line-height: 1.1;
    white-space: nowrap;   /* angka tidak boleh pernah terpotong antar baris */
  }}
  /* Nilai berupa TEKS (mis. "Anak_At risk of overweight") tidak boleh memakai
     gaya angka besar -- pada kolom sempit kata panjang akan pecah menjadi
     "Ove/rwei/ght". Teks memakai ukuran sendiri yang aman untuk dibungkus. */
  .nilai-teks {{
    font-size: 1.02rem; font-weight: 700; color: {NAVY}; line-height: 1.3;
    overflow-wrap: break-word; hyphens: none;
  }}
  .deskripsi {{ font-size: .78rem; color: {ABU_TUA}; margin-top: 4px; }}

  .judul-bagian {{
    font-size: 1.05rem; font-weight: 700; color: {NAVY}; margin: 22px 0 2px;
  }}
  .sub-bagian {{ font-size: .85rem; color: {ABU_TUA}; margin-bottom: 12px; }}

  /* ---------- catatan (pola permukaan bernada dari deck) ---------- */
  /* .catatan tampil di DUA induk: di dalam .kartu putih dan langsung di atas
     LATAR. Satu nada tidak bisa disetel untuk keduanya, jadi garis tepi dan
     padding-lah yang memikul pemisahan pada latar halaman. Itu memang perangkat
     deck-nya sendiri. */
  .catatan {{
    font-size: .8rem; color: {ABU_TUA}; background: {TINT_NETRAL};
    border-left: 3px solid {SISI_NETRAL}; padding: 8px 12px;
    margin-top: 10px; border-radius: 0 6px 6px 0; line-height: 1.5;
  }}
  .catatan-penting {{
    font-size: .82rem; color: {TINTA_PERINGATAN}; background: {TINT_PERINGATAN};
    border-left: 3px solid {SISI_PERINGATAN}; padding: 10px 12px;
    margin-top: 10px; border-radius: 0 6px 6px 0; line-height: 1.5;
  }}

  /* ---------- pil status ---------- */
  .pil {{
    display: inline-block; padding: 5px 14px; border-radius: 999px;
    font-size: .82rem; font-weight: 700; letter-spacing: .02em;
  }}
  .pil-risiko {{
    background: {TINT_PERINGATAN}; color: {TINTA_RISIKO};
    border: 1px solid {SISI_PERINGATAN};
  }}
  .pil-aman {{
    background: {TINT_AMAN}; color: {TINTA_AMAN}; border: 1px solid {SISI_AMAN};
  }}

  .nama-penyakit {{ font-size: 1.12rem; font-weight: 700; color: {NAVY}; }}
  .meta-model {{ font-size: .76rem; color: {ABU_TUA}; margin-top: 2px; }}
  .baris-metrik {{
    font-size: .74rem; color: {ABU_TUA}; margin-top: 10px;
    border-top: 1px solid {GARIS}; padding-top: 8px;
  }}

  /* ---------- tabel informasi ---------- */
  table.tabel-info {{ width: 100%; border-collapse: collapse; font-size: .84rem; margin-top: 8px; }}
  table.tabel-info th {{
    background: {TINT_NETRAL}; color: {NAVY}; text-align: left;
    padding: 8px 10px; font-size: .7rem; text-transform: uppercase; letter-spacing: .06em;
    border-bottom: 2px solid {BPJS_BIRU};
  }}
  table.tabel-info td {{ padding: 7px 10px; border-bottom: 1px solid {GARIS}; color: {TINTA}; }}
  table.tabel-info tr:last-child td {{ border-bottom: none; }}
  table.tabel-info td.angka {{ font-variant-numeric: tabular-nums; color: {NAVY}; font-weight: 600; }}

  .rumus {{
    background: {TINT_INFO}; border: 1px solid {SISI_INFO}; border-radius: 8px;
    padding: 14px 16px; font-size: 1.02rem; color: {NAVY}; font-weight: 600;
    text-align: center; margin: 10px 0;
  }}

  /* Streamlit 1.61 memakai data-testid="stTab"; selector data-baseweb lama
     tidak cocok lagi, jadi keduanya ditulis agar aman lintas versi. */
  .stTabs [role="tablist"], .stTabs [data-baseweb="tab-list"] {{ gap: 4px; }}
  .stTabs [role="tab"], .stTabs [data-testid="stTab"] {{
    font-weight: 600; color: {ABU_TUA}; padding: 10px 18px;
  }}
  .stTabs [role="tab"][aria-selected="true"],
  .stTabs [data-testid="stTab"][aria-selected="true"] {{
    color: {NAVY}; border-bottom-color: {NAVY};
  }}
</style>
"""


# --------------------------------------------------------------------------
# Komponen kecil
# --------------------------------------------------------------------------
def header(judul: str, subjudul: str) -> str:
    return (f'<div class="bpjs-header"><h1>{html.escape(judul)}</h1>'
            f'<p>{html.escape(subjudul)}</p></div>'
            f'<div class="garis-merek"></div>')


def kartu_statistik(label: str, nilai: str, deskripsi: str = "",
                    teks: bool = False) -> str:
    """
    Kartu statistik gaya deck: label kecil -> nilai -> keterangan.

    `teks=True` untuk nilai berupa kata (kategori BMI), bukan angka; kata
    panjang akan dibungkus dengan rapi alih-alih dipecah per suku kata.
    """
    kelas = "nilai-teks" if teks else "angka-besar"
    d = f'<div class="deskripsi">{html.escape(deskripsi)}</div>' if deskripsi else ""
    return (f'<div class="kartu"><div class="label-kecil">{html.escape(label)}</div>'
            f'<div class="{kelas}">{html.escape(nilai)}</div>{d}</div>')


def judul_bagian(judul: str, sub: str = "") -> str:
    s = f'<div class="sub-bagian">{html.escape(sub)}</div>' if sub else ""
    return f'<div class="judul-bagian">{html.escape(judul)}</div>{s}'


def pil(teks: str, berisiko: bool) -> str:
    kelas = "pil-risiko" if berisiko else "pil-aman"
    return f'<span class="pil {kelas}">{html.escape(teks)}</span>'


# --------------------------------------------------------------------------
# Grafik 1 -- posisi IMT pada skala kategori
# --------------------------------------------------------------------------
def skala_imt(imt: float, pita: list[tuple[float, float, str]]) -> str:
    """
    Pita kategori dengan penanda pada posisi IMT pengguna.

    `pita` = daftar (batas_bawah, batas_atas, nama). Tiap kategori digambar
    SAMA LEBAR (skala ordinal, bukan linear) supaya label batas tidak saling
    bertumpuk -- nilai batasnya tetap dicetak sehingga sifat non-linear ini
    terlihat jelas, bukan disembunyikan. Posisi penanda diinterpolasi di dalam
    pita tempat IMT berada.

    Pita aktif ditentukan dari NILAI IMT, bukan dari nama kategori, sehingga
    tidak mungkin bertentangan dengan bmi_standards.classify_bmi().
    """
    n = len(pita)
    lebar = 100.0 / n

    # posisi penanda (persen dari kiri) + indeks pita aktif
    posisi = None
    idx_aktif = -1
    for i, (lo, hi, _nama) in enumerate(pita):
        if lo <= imt < hi or (i == n - 1 and imt >= lo):
            rentang = (hi - lo) if hi != float("inf") else max(6.0, imt - lo + 3.0)
            frac = min(1.0, max(0.0, (imt - lo) / rentang)) if rentang > 0 else 0.5
            posisi = (i + frac) * lebar
            idx_aktif = i
            break
    if posisi is None:
        below = imt < pita[0][0]
        posisi = 0.0 if below else 100.0
        idx_aktif = 0 if below else n - 1
    posisi = min(98.5, max(1.5, posisi))

    segmen = []
    for i, (lo, hi, nama) in enumerate(pita):
        aktif = i == idx_aktif
        bg = NAVY if aktif else TRACK
        # ABU_TUA, bukan ABU: label pita non-aktif berdiri di atas TRACK
        # #e6edf4, dan ABU hanya mencapai 4,09:1 di sana -- di bawah lantai 4,5.
        # Cacat ini sudah ada sebelum perombakan warna; lihat catatan 3.
        fg = "#fff" if aktif else ABU_TUA
        bobot = "700" if aktif else "500"
        segmen.append(
            f'<div style="flex:1;background:{bg};color:{fg};font-size:.6rem;'
            f'font-weight:{bobot};text-align:center;padding:7px 2px;'
            f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">'
            f'{html.escape(nama)}</div>')

    # label batas di bawah (batas bawah tiap pita, kecuali yang pertama)
    ticks = []
    for i, (lo, _hi, _n) in enumerate(pita):
        if i == 0:
            ticks.append('<div style="flex:1;"></div>')
        else:
            ticks.append(
                f'<div style="flex:1;position:relative;">'
                f'<span style="position:absolute;left:0;transform:translateX(-50%);'
                f'font-size:.62rem;color:{ABU_TUA};font-variant-numeric:tabular-nums;">'
                f'{lo:g}</span></div>')

    return f"""
<div style="margin:6px 0 22px;">
  <div style="position:relative;height:22px;">
    <div style="position:absolute;left:{posisi}%;transform:translateX(-50%);
                white-space:nowrap;font-size:.76rem;font-weight:700;color:{NAVY};">
      IMT {imt:.1f}
    </div>
  </div>
  <div style="position:relative;">
    <div style="display:flex;border-radius:6px;overflow:hidden;border:1px solid {GARIS};">
      {''.join(segmen)}
    </div>
    <div style="position:absolute;top:-4px;bottom:-4px;left:{posisi}%;width:3px;
                background:{NAVY};transform:translateX(-50%);
                box-shadow:0 0 0 2px #fff;border-radius:2px;"></div>
  </div>
  <div style="display:flex;margin-top:4px;">{''.join(ticks)}</div>
</div>
"""


# --------------------------------------------------------------------------
# Grafik 2 -- bar probabilitas dengan dua garis acuan
# --------------------------------------------------------------------------
def bar_probabilitas(prob: float, prevalensi: float, berisiko: bool) -> str:
    """
    Satu bar polos = skor risiko pengguna.

    Garis acuan ambang 50% dan prevalensi populasi SENGAJA tidak digambar lagi.
    Keduanya menambah dua angka pembanding pada satu baris yang sudah memuat
    persentase dan label, dan justru mengundang pembacaan "peluang saya sekian
    dibanding rata-rata" -- padahal skor ini dihasilkan model berbobot kelas,
    sehingga tidak terkalibrasi sebagai peluang. Label Berisiko/Tidak Berisiko di
    sebelah kanan sudah menyatakan hasil pengambangan itu sendiri.

    `prevalensi` tetap menjadi parameter supaya pemanggil tidak perlu diubah dan
    acuan ini gampang dikembalikan bila memang diinginkan.
    """
    p = min(100.0, max(0.0, prob * 100))
    warna = warna_status(berisiko)

    return f"""
<div style="margin:10px 0 6px;">
  <div style="position:relative;height:26px;background:{TRACK};
              border-radius:6px;overflow:hidden;">
    <div style="position:absolute;left:0;top:0;bottom:0;width:{p}%;
                background:{warna};border-radius:6px 4px 4px 6px;"></div>
  </div>
</div>
"""


# --------------------------------------------------------------------------
# Grafik 3 -- kontribusi SHAP per fitur (penjelasan lokal)
# --------------------------------------------------------------------------
def bar_kontribusi(kontribusi: list[tuple[str, float]],
                   label_fitur: dict[str, str]) -> str:
    """
    Bar menyebar dua arah dari garis nol: kenapa peserta ini diprediksi begitu.

    Warnanya sengaja SAMA dengan warna kelas di seluruh dasbor -- oranye
    mendorong ke arah "Berisiko", hijau menjauhinya. Memakai pasangan warna lain
    di sini akan membuat pembaca mengira ia sedang melihat besaran yang berbeda.
    Keduanya sudah lolos uji kontras di atas kartu putih (3,64:1 dan 4,50:1).

    Arah juga ditandai oleh POSISI (kiri/kanan garis nol) dan oleh tanda pada
    angkanya, jadi grafik tetap terbaca tanpa membedakan warna sama sekali.

    Angka yang ditulis adalah **pangsa** tiap fitur terhadap total pergerakan,
    bukan nilai SHAP mentahnya. Alasannya: pohon sklearn mengeluarkan SHAP pada
    skala probabilitas sedangkan XGBoost pada skala log-odds, sehingga angka
    mentah tidak sebanding antar penyakit dan "+9,24" tidak berarti apa pun bagi
    pembaca. Pangsa bebas satuan dan sama tafsirnya di keempat model. Nilai
    mentahnya tetap ada di Stacked Revisi.ipynb Bagian 7b.
    """
    if not kontribusi:
        return ""

    maks = max(abs(v) for _, v in kontribusi) or 1.0
    total = sum(abs(v) for _, v in kontribusi) or 1.0
    baris = []

    for fitur, nilai in kontribusi:
        lebar = abs(nilai) / maks * 50.0
        naik = nilai >= 0
        warna = ORANYE if naik else HIJAU
        kiri = 50.0 if naik else 50.0 - lebar
        nama = label_fitur.get(fitur, fitur)
        pangsa = abs(nilai) / total * 100
        angka = f"{'+' if naik else '−'}{pangsa:.0f}%"

        baris.append(f"""
  <div style="display:grid;grid-template-columns:minmax(88px,26%) 1fr 52px;
              align-items:center;gap:8px;margin:5px 0;">
    <div style="font-size:.78rem;color:{NAVY};text-align:right;">{nama}</div>
    <div style="position:relative;height:15px;background:{TRACK};border-radius:3px;">
      <div style="position:absolute;left:50%;top:-2px;bottom:-2px;width:1px;
                  background:{GARIS};"></div>
      <div style="position:absolute;top:0;bottom:0;left:{kiri}%;width:{lebar}%;
                  background:{warna};border-radius:2px;"></div>
    </div>
    <div style="font-size:.72rem;color:{ABU_TUA};font-variant-numeric:tabular-nums;">
      {angka}</div>
  </div>""")

    return f"""
<div style="margin:12px 0 4px;">
  <div style="display:grid;grid-template-columns:minmax(88px,26%) 1fr 52px;gap:8px;
              font-size:.66rem;color:{ABU_TUA};margin-bottom:2px;">
    <div></div>
    <div style="display:flex;justify-content:space-between;">
      <span>&#9664; menurunkan risiko</span><span>menaikkan risiko &#9654;</span>
    </div>
    <div></div>
  </div>
  {''.join(baris)}
</div>
"""
