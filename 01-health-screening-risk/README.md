# 01 Health Screening Risk Prediction

BPJS Kesehatan runs a self-screening questionnaire that flags members as at risk of diabetes,
hypertension, lung cancer and tuberculosis. This project cleans the 2025 exports for two
regencies in Yogyakarta, Bantul and Sleman, studies what drives each flag, trains a model per
disease, and puts the models behind a dashboard.

## Findings that shaped the work

- **The two exports are not the same format.** Bantul is UTF-16 and tab-separated, Sleman is
  UTF-8 and comma-separated. Reading one with the other's settings gives a single-column table
  rather than an error, so all reading goes through `Bersama/konfigurasi.py`, which checks the
  column count and fails loudly.
- **A label typo in the source.** `Tidah Berisiko` appears on 167,680 Bantul and 196,385 Sleman
  records and has to be merged into `Tidak Berisiko` before anything is counted.
- **"Not asked" is not "no".** Each disease question is only put to an age band (diabetes and
  hypertension 15+, lung cancer 45+). `Tidak Dapat Pertanyaan` marks someone who was never
  asked, so each disease is modelled on its own eligible subpopulation rather than on one shared
  table.
- **The diabetes flag is almost entirely a BMI rule.** Adults with a BMI above 25 are flagged in
  99.9% of cases (231 exceptions among 181,002). A model can only rediscover that rule, so its
  0.95 ROC-AUC describes the questionnaire's scoring, not clinical risk.
- **Height confounds with sex.** Lung cancer risk appears to rise with height until the curve is
  split by sex, at which point both lines go flat.

## Results

Test set ROC-AUC for the combined model (both regencies, `wilayah` as a seventh feature). Each
model was compared against a stratified baseline, whose ROC-AUC is 0.50.

| Disease | Asked of | Prevalence | Model | Test records | ROC-AUC |
|---|---|---|---|---|---|
| Diabetes | age 15+ | 40.7% | XGBoost | 122,764 | 0.951 |
| Hypertension | age 15+ | 61.6% | XGBoost | 119,451 | 0.777 |
| Lung cancer | age 45+ | 10.3% | XGBoost | 62,968 | 0.785 |
| Tuberculosis | all ages | 6.3% | XGBoost | 152,716 | 0.689 |

Bantul and Sleman each have their own models as well; their scores sit within 0.02 of these.

## Dashboard

A member enters age, sex, height, weight and membership segment and picks a model set
(Bantul, Sleman or combined). For each disease whose age gate they pass, the dashboard shows a
risk score and a SHAP breakdown of what moved it, then turns that breakdown into plain
language: which factors raised or lowered the score and by how much, with practical advice
and a closing line on whether to see a doctor and which test to ask for. The score is shown as
a bare bar, with no 50% line and no population average beside it, because the class-weighted
models are not calibrated and those markers invited reading the score as a probability.

The analysis tabs profile the screened population: age and sex pyramids, class balance per
disease, adult (WHO) and child (CDC) BMI classes kept on separate axes, prevalence by age band,
and a per-disease explorer.

## Layout

```
Bersama/            shared code: paths and file reading, BMI standards, plot style
Bantul/  Sleman/    per regency, run in this order:
  Persiapan Data/     cleaning and per-disease datasets
  Analisis Data/      raw and clean profiling, variable relationships, BMI classes
                      (Bantul also has Bersih Lengkap, a full per-disease profile)
  Script penyakitan/  model comparison and tuning (logistic regression, decision tree, XGBoost)
Gabungan/
  Notebook/           combining the regencies, replicating findings, combined model, transfer tests
  Dashboard/          Streamlit and Tkinter apps, training export, verification
```

## Running it

The two raw exports are included, de-identified with dummy IDs, where `Bersama/konfigurasi.py`
expects them:

```
Bantul/Skrining_Bantul_2025.csv     UTF-16, tab-separated
Sleman/Skrining_Sleman_2025.csv     UTF-8, comma-separated
```

Run the notebooks in the order above (they write the cleaned datasets to each region's
`Data Setiap Target/`), then build and check the dashboard from this folder:

```bash
pip install -r requirements.txt
python Gabungan/Dashboard/train_export.py
python Gabungan/Dashboard/build_analysis.py
python Gabungan/Dashboard/verify.py
streamlit run Gabungan/Dashboard/app_streamlit.py
```

`verify.py` runs 81 checks for each region, 243 in all, and every one passed on the original
data. It tests the prediction engine: predictions match the trained models on real records, BMI
categories match the cleaned data, age gates and invalid inputs behave, every exported metric
matches the modelling notebooks, and the plain-language explanation gives one point per factor,
never repeats advice, never gives a child the adult BMI target, and always ends with the doctor
recommendation. The dashboard reads only the exported
models and summary JSON, never the raw CSVs. Design notes for the dashboard, in Indonesian, are
in [Gabungan/Dashboard/README.md](Gabungan/Dashboard/README.md).
