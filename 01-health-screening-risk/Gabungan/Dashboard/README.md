# Dashboard Prediksi Risiko Penyakit Kronis

Antarmuka untuk memakai model hasil notebook pemodelan: pengguna memasukkan data
diri, dashboard menghitung IMT, mengkategorikannya, lalu memprediksi risiko untuk
penyakit yang syarat usianya terpenuhi.

## Tiga kumpulan model, satu dashboard

Pemilih **Wilayah** di panel kiri menentukan model **dan** seluruh angka analisis
yang tampil:

| Pilihan | Dilatih pada | Fitur |
|---|---|---|
| **Bantul** | data Bantul saja | 6 |
| **Sleman** | data Sleman saja | 6 |
| **Gabungan** | kedua kabupaten | **7** -- `wilayah` ikut menjadi fitur |

Pada pilihan Gabungan muncul satu masukan tambahan, **kabupaten tempat
skrining**, karena di sanalah `wilayah` benar-benar dipakai model. Untuk model
satu wilayah masukan itu diabaikan.

Setiap wilayah punya foldernya sendiri di `models/`, dan **seluruh angka di layar
-- prevalensi, metrik, SHAP, catatan keterbatasan -- berganti bersama pemilih
itu.** Tidak ada angka yang dibagi antar wilayah.

## Cara menjalankan

Versi web (Streamlit). **Harus dijalankan dari akar proyek** supaya
`.streamlit/config.toml` terbaca; tanpa itu temanya mengikuti tema sistem dan
tampilannya rusak:

```bash
streamlit run Gabungan/Dashboard/app_streamlit.py
```

Versi desktop (Tkinter, tanpa perlu pemasangan apa pun):

```bash
python Gabungan/Dashboard/app_tkinter.py
```

Keduanya memanggil `predictor.py` yang sama, jadi hasilnya selalu identik.

⚠️ **Pemuatan pertama tiap wilayah butuh sekitar 25 detik** (impor `shap` dan
pemuatan empat `.joblib`). Hasilnya di-cache per wilayah, jadi hanya sekali.

## Isi folder

| Berkas | Fungsi |
|---|---|
| `train_export.py` | Melatih 4 model terbaik **tiap wilayah** lalu menyimpannya. Hyperparameter dibaca dari `hyperparameter_terpilih.json`, tidak diketik ulang. |
| `build_analysis.py` | Menghitung angka tab Analisis **tiap wilayah**. Gerbangnya dua lapis: acuan terbit (Bantul) + identitas internal (semua wilayah). |
| `predictor.py` | Mesin prediksi — seluruh logika, tanpa UI |
| `theme.py` | Palet, CSS, dan pembangun grafik HTML (gaya deck BPJS) |
| `analysis.py` | Grafik tab Analisis — seluruhnya figur matplotlib, tanpa Altair |
| `app_streamlit.py` | Antarmuka web — 4 tab: Hasil Prediksi, Analisis Skrining, Analisis per Penyakit, Informasi |
| `app_tkinter.py` | Antarmuka desktop (tanpa tab Analisis) |
| `verify.py` | 71 pemeriksaan otomatis terhadap data asli, **per wilayah** |
| `models/<wilayah>/` | 4 berkas `.joblib` + `metadata.json` + `analysis.json` per wilayah (`bantul/`, `sleman/`, `gabungan/`) |

## Dua tab analisis

**Analisis Skrining** — lima bagian, lima kendali:

1. **Profil populasi** — empat kartu ringkasan.
2. **Komposisi peserta** — piramida usia/jenis kelamin dan komposisi segmen.
3. **Prevalensi menurut kelompok usia** untuk keempat penyakit.
4. **Telusuri satu penyakit** — pilih penyakit, skala piramida, dan variabel.
   Piramida terpisah risiko (tiap batang usia × jenis kelamin dipecah
   Berisiko/Tidak Berisiko) lalu kurva prevalensi per desil, dengan pilihan
   memisahkan menurut jenis kelamin.

   Kurva desil menawarkan **tiga** variabel, bukan empat: `Usia` sengaja
   dikeluarkan karena piramida tepat di atasnya sudah menjawab pertanyaan yang
   sama — dan menjawabnya lebih baik, per pita *dan* per jenis kelamin. Daftarnya
   disaring dari `num_cols`, jadi variabel numerik baru tetap muncul otomatis.
   Tab per penyakit tetap menawarkan keempatnya: di sana `Usia` menjawab
   pertanyaan lain (bentuk sebaran, bukan tren risiko).
5. **Ditandai lebih dari satu penyakit** — sebaran jumlah penanda per catatan.

Seluruh kendali di tab ini memakai kunci berawalan `skrining_`; tab per penyakit
memakai `analisis_`. Keduanya sengaja tidak berbagi kunci.

**Kurva desil adalah peragaan perancu yang paling jelas di proyek ini.** Pilih
Kanker Paru × Tinggibadan: garis gabungan menanjak 3,99% → 25,41%, tetapi begitu
dicentang **Pisahkan menurut jenis kelamin**, kedua garisnya mendatar. Tingginya
menandai jenis kelamin, bukan risikonya.

⚠️ Jumlah desil **belum tentu sepuluh**. Tinggi badan dicatat kelipatan 5 cm
sehingga beberapa batas desil runtuh dan hanya sembilan yang terbentuk pada tiga
dari empat penyakit. Jangan menulis kode yang mengasumsikan 10.

**Kookurensi ditampilkan per strata pertanyaan, bukan per pita usia.** Tiap
penyakit ditanyakan pada rentang usia yang berbeda dan `Tidak Dapat Pertanyaan`
berarti pertanyaannya tidak diajukan — bukan jawaban "tidak" — sehingga tidak ada
satu denominator yang berlaku untuk keempat penyakit sekaligus. Sumbu grafiknya
selalu berbunyi "dari N pertanyaan yang diajukan", dan N dibaca dari data. Kartu
di bawahnya menyatakan denominatornya, siapa yang tidak masuk, dan ke arah mana
angkanya bias. Rinciannya di catatan analisis §3.13.

**Analisis per Penyakit** — tiga dropdown (penyakit · Keduanya/Berisiko/Tidak
Berisiko · variabel) menghasilkan satu histogram kepadatan dengan garis KDE,
lalu peta panas segmen × penyakit, lalu heatmap lengkap semua variabel × semua
penyakit beserta tabel perancunya.

Bila pengguna sudah menekan **Hitung Risiko**, posisinya sendiri ditandai pada
sebaran dan barisan segmennya disorot pada peta panas — **kecuali** pada penyakit
yang syarat usianya tidak terpenuhi, supaya tidak bertentangan dengan gerbang usia
di tab Hasil.

**Tentang garis KDE.** Tinggi badan, berat badan, dan usia dicatat dalam pembulatan
(tinggi umumnya kelipatan 5 cm), sehingga histogramnya berbentuk deretan paku.
Dengan ratusan ribu baris, lebar pita Scott sangat sempit sehingga **KDE ikut
mengikuti paku itu, bukan meratakannya**. Gunanya di sini adalah membandingkan
bentuk kedua kelas sebagai dua garis — jauh lebih terbaca daripada batang
transparan yang saling bertumpuk.

Angkanya dihitung sekali oleh `build_analysis.py` dari `dataset_master.csv` ke
`models/analysis.json` (sekitar 240 KB; ukuran tepatnya dicetak `build_analysis.py`
setiap kali dijalankan). Dashboard yang berjalan **tidak pernah membuka CSV
42 MB itu**, sehingga folder ini tetap hanya bergantung pada `models/` miliknya sendiri.

Sumber: `Analisis Hubungan Antar Variabel.ipynb` (sel 4, 18, 38, 41) dan
`Analisis Data Bersih.ipynb` (sel 13, 14, 22). Fungsi ukuran asosiasi disalin apa
adanya dari notebook, dan `build_analysis.py` berhenti dengan error bila hasil
hitungnya tidak cocok dengan angka yang sudah dilaporkan di catatan analisis §3.10/§3.11.

## Kenapa semua grafik memakai matplotlib, bukan Altair

Audit perataan 10 Agustus menemukan pola yang jelas: setiap kartu HTML dan setiap
gambar matplotlib berhenti **tepat** di tepi kanan kolom teks, sedangkan **setiap**
grafik Altair meleset 47–97 px.

Sebabnya berantai. Grafik Vega yang dipasang di dalam tab yang belum aktif
terpasang saat lebarnya masih 0 lalu tidak pernah mencoba lagi — hasilnya wadah
kosong. Baik `use_container_width=True` maupun `width="container"` sama-sama
gagal (keduanya sudah diuji), sehingga lebar Altair **harus** dipatok dalam
piksel. Padahal kolom teks lebarnya mengikuti layar: 810 px saat panel samping
terbuka pada 1280, 1230 px pada 1700. Lebar tetap tidak akan pernah pas.

Gambar tidak punya masalah itu — gambar menyesuaikan lebar wadahnya. Karena itu
seluruh grafik kini figur matplotlib, dan perataannya 0 px di semua tab.

### Dua aturan `st.pyplot` yang berbeda, dan itu disengaja

- **Grafik yang lebih kecil dari 1460 px → `use_container_width=True`** (piramida,
  segmen, prevalensi usia, kedua peta panas, heatmap lengkap). Gambar melar
  mengisi kolom sehingga tepinya rata.
- **Histogram + KDE → `use_container_width=False`.** Figurnya sudah menyentuh
  batas `MAXIMUM_CONTENT_WIDTH = 2 × 730 = 1460 px` milik Streamlit; bila
  dibiarkan melar, gambar 1460 px itu **diregangkan** pada layar yang lebih lebar
  dan tampak pecah. Menaikkan dpi tidak menolong — batas itu keras.

Konsekuensi yang perlu diketahui: pada jendela yang sangat lebar (kolom teks di
atas 1460 px, kira-kira mulai lebar jendela 1930 px) grafik selebar penuh akan
mulai diregangkan lagi. Itu batas Streamlit, bukan batas berkas gambarnya.

Setelah mengubah `analysis.py` atau `theme.py`, **server Streamlit harus dimatikan
dan dijalankan ulang**; modul yang diimpor tidak selalu ikut dimuat ulang oleh
pengawas berkas.

Tema Streamlit dikunci ke mode terang lewat `../.streamlit/config.toml` di akar
proyek. Tanpa berkas itu, Streamlit mengikuti tema sistem: pada mode gelap panel
samping menjadi hitam dan tombol utama merah, bentrok dengan rancangan navy.
**Jalankan perintah dari akar proyek** agar berkas tema terbaca.

## Catatan desain

Gaya visual mengacu pada deck presentasi BPJS **hanya untuk warna, tipografi, dan
tata letak**. Seluruh ANGKA berasal dari `models/metadata.json` — tidak ada satu
pun angka yang diambil dari deck, karena isi deck sudah tidak sesuai dengan
analisis terkini.

Keputusan warna diambil dari perhitungan, bukan perkiraan (rinciannya ada di
docstring `theme.py`):

- Oranye deck `#f08a24` hanya mencapai kontras 2,51:1 terhadap kartu putih, di
  bawah minimum 3:1. Isian bar memakai `#c96f0f` (3,64:1).
- Prevalensi populasi digambar sebagai **garis putus-putus**, bukan bar kedua,
  karena hijau vs abu-abu terlalu berdekatan (ΔE 14,2, di bawah lantai 15) untuk
  dibedakan dengan andal.
- **Permukaan bernada (11 Agustus)** mengambil sistem kartu deck: tiap kartu
  non-data diberi nada semantik dengan garis tepi lembut sewarna. **Grafik dan
  `.kartu` tempatnya berdiri tetap putih** — kelima rasio yang sudah divalidasi
  diukur terhadap putih, dan menodainya akan membatalkan semuanya sekaligus.
- **`ABU #6b7280` dipensiunkan sebagai warna teks.** Di atas nada ia hanya
  4,19–4,60:1, di bawah lantai 4,5. Dua kegagalan seperti ini ternyata sudah ada
  sebelum perubahan warna dan ikut diperbaiki: `.kartu-redup` (4,24:1) dan label
  pita non-aktif skala IMT (4,09:1). Penggantinya `ABU_TUA #5b6770`. Yang tersisa
  dinamai `ABU_GRAFIK`, khusus teks di dalam figur matplotlib yang latarnya putih.
- Nada yang dipakai adalah anggota **terdalam** tiap keluarga deck: nada deck
  lebih terang daripada `LATAR_TINT` lama, sehingga memilih anggota tengah justru
  membuat permukaan makin sulit dibedakan dari kartu putih (netral baru 1,153:1
  vs 1,140:1 yang lama).
- Aksen BPJS hijau `#1fa860` hanya 3,08:1 terhadap putih, jadi ia **tanda saja,
  tidak pernah teks**, dan tidak pernah di dalam grafik — hijau di sana sudah
  berarti "Tidak Berisiko". Biru `#45669c` (5,78:1) aman sebagai teks.

## Masukan

Lima isian: **jenis kelamin, usia, tinggi badan, berat badan, dan segmen kepesertaan BPJS.**

Segmen wajib ada karena model memang dilatih dengan kolom tersebut, dan ia salah satu
penentu terbesar risiko TBC. Menghilangkannya berarti melatih ulang seluruh model dan
mengubah semua angka yang sudah dilaporkan.

## Gerbang usia

Tiap model hanya dijalankan pada rentang usia yang dilatihkan:

| Penyakit | Berlaku |
|---|---|
| Diabetes Melitus | usia 15+ |
| Hipertensi | usia 15+ |
| Kanker Paru | usia 45+ |
| TBC | semua usia |

Model mana yang dipakai per penyakit **tidak ditulis di sini** — ia dipilih ulang setiap
kali `Stacked Revisi.ipynb` dijalankan, dari tiga kandidat sungguhan (`logistic`,
`decision_tree`, `xgboost`) ditambah `dummy` sebagai garis dasar. Nilai yang berlaku ada
di `models/metadata.json`.

⚠️ `verify.py` memastikan model yang diekspor adalah F1 tertinggi **di antara model
sungguhan**. `dummy` wajib dikecualikan: pada Hipertensi F1-nya 0,7552 melawan xgboost
0,7448, sehingga tanpa pengecualian itu pemeriksaannya justru menuntut `dummy` yang
diekspor.

Di luar rentangnya, model **tidak dijalankan sama sekali** dan dashboard menjelaskan
alasannya. Anak usia 10 tahun hanya menerima hasil TBC.

## Penjelasan per peserta (SHAP)

Tiap hasil disertai grafik kontribusi: seberapa jauh tiap ciri peserta menggeser
prediksi dari rata-rata populasi, dan ke arah mana. Dihitung dengan
`shap.TreeExplainer` pada model yang sama yang menghasilkan angka prediksinya
(Tinjauan Pustaka §2.1.6).

Tiga hal yang mudah salah di sini:

1. **Nilai SHAP dijumlahkan per fitur asli lebih dulu.** Setelah one-hot encoding
   `segmen` pecah menjadi 6 kolom; tanpa penjumlahan ia tampak jauh lebih kecil
   daripada pengaruh sebenarnya — kesalahan yang sama dengan `feature_importances_`
   (catatan analisis §3.9).
2. **Skalanya berbeda antar jenis model.** Pohon sklearn mengeluarkan SHAP pada skala
   **probabilitas**, XGBoost pada skala **log-odds**. Sifat aditif hanya berlaku pada
   skala masing-masing; menerapkan sigmoid pada keduanya membuat Kanker Paru meleset
   0,12. Skala dibaca dari `explainer.model.tree_output`, bukan ditebak, dan disimpan
   di `HasilPenyakit.skala`.
3. **Yang ditampilkan adalah pangsa, bukan nilai mentah.** Karena skalanya berbeda,
   angka mentah tidak sebanding antar penyakit dan "+9,24" tidak berarti apa pun bagi
   pembaca. Nilai mentahnya ada di `Stacked Revisi.ipynb` Bagian 7b.

`app_tkinter.py` belum menampilkan grafik ini — ia tetap berjalan normal, hanya tanpa
penjelasan per peserta.

## Menjalankan ulang ekspor model

Bila `Stacked Revisi.ipynb` dijalankan ulang dan angkanya berubah:

```bash
python Dashboard/train_export.py
python Dashboard/verify.py
```

`train_export.py` membandingkan metrik model hasil latihnya dengan `ringkasan_model.csv`
dan **berhenti dengan error bila ada satu saja yang menyimpang** (toleransi 1e-4). Jadi
model yang tersimpan dijamin identik dengan model yang dilaporkan.

## Catatan penting

Dashboard ini sengaja menampilkan keterbatasan tiap model, bukan hanya labelnya:

- **Diabetes** — model merekonstruksi aturan kuesioner `IMT > 25` (P = 0,9990). Bukan
  prediksi penyakit.
- **Kanker Paru (presisi 0,224) dan TBC (presisi 0,103)** — sebagian besar orang yang
  ditandai berisiko sebenarnya tidak berisiko menurut kuesioner. Dashboard menyatakan ini
  dalam kalimat biasa saat hasilnya "Berisiko".
- Faktor risiko terpenting (riwayat keluarga, merokok, tekanan darah, lingkar perut,
  aktivitas fisik) tidak tersedia dalam data.

Menghapus catatan-catatan itu akan membuat dashboard menyesatkan.
