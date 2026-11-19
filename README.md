# BPJS Kesehatan Internship

Code from my data science internship in the Actuarial Valuation division of BPJS Kesehatan
(Indonesia's national health insurance agency), head office in Jakarta, 16 July to
21 August 2026. The internship ran four assignments; three of them are here.

| # | Project | What it does | Stack |
|---|---|---|---|
| 01 | [Health screening risk prediction](01-health-screening-risk/) | Cleans 763,580 health screening records from two regencies, models risk for four chronic diseases, and serves the models in a Streamlit dashboard | pandas, scikit-learn, XGBoost, SHAP, Streamlit |
| 02 | [Priority village healthcare access](02-priority-village-access/) | Measures how 310 priority villages in Maluku and North Maluku reach their nearest primary care facility | geopandas, shapely, OSRM, QGIS |
| 03 | [Industrial dispute court scraper](03-court-case-scraper/) | Collects industrial dispute (PHI) case listings from district court SIPP portals | Selenium, undetected-chromedriver, BeautifulSoup |

## Data

- **Screening records** (project 01) are de-identified: each member carries a dummy ID, with no
  name or national ID number. Only the two raw exports are committed; the cleaned per-disease
  datasets and the trained models are rebuilt by the notebooks and `train_export.py`.
- **Village access** (project 02) is code only. Its inputs are internal BPJS and ministry
  documents, so neither they, the results derived from them, nor the GIS layers are included.
- **Court case lists** (project 03) are public records from the SIPP portals.

## Layout

The folder names inside each project are in Indonesian, as they were during the internship,
because the code resolves paths from them. Notebooks were saved with their outputs cleared.
