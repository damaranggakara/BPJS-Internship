# 02 Priority Village Healthcare Access

Which of 310 government priority villages in Maluku and North Maluku can actually reach a
primary care facility (FKTP), and which qualify for compensation because they cannot? The
villages span 22 regencies and were matched against 508 candidate facilities.

## Method

1. **Locate every village.** Village centroids come from the national 1:10,000 village boundary
   polygons (BIG). The priority list and the polygons spell names differently, so matching runs
   on official village codes first and falls back to normalised names with a similarity score.
2. **Straight-line distance.** Haversine distance from each village to its nearest facility.
3. **Road routing.** Each village to facility pair is routed over the road network with the
   public OSRM API, which returns whether a road connection exists, plus distance and time.
4. **Decision rule.** Routing alone is not the answer: in an archipelago, ferries are often the
   main way in. A village counts as unreachable only if all three hold at once: no road
   connection, no facility inside its own boundary, and no land, sea or air transport. The
   transport layers (ferry terminals, airports, roads) were assessed in QGIS.

## Result

| | Maluku | North Maluku | Total |
|---|---|---|---|
| Priority villages | 155 | 155 | 310 |
| Not connected by road | 43 | 50 | 93 |
| Eligible for compensation | 12 | 5 | 17 |

Of the 93 villages with no road connection, 74 are still reachable by another mode and 2 have a
facility inside their own boundary. Reading "no road" as "no access" would have overstated the
problem more than fivefold.

## Scripts

Run in order from inside `Script/`; each reads the previous step's output from `../Output/`.

| Script | Step |
|---|---|
| 01 | Filter the facility list to the two provinces |
| 02 | Village centroids from the boundary shapefile |
| 03 | Join the priority list to the centroids by village code |
| 04 | Haversine distance to the nearest facility |
| 05, 06 | Split and inspect results by province |
| 08 | Match priority villages to boundary polygons, by code then by name |
| 09 | OSRM road routing for every village to facility pair |
| 10 | Split routing results by province |
| 11 | Repair village name matches that failed on spelling |
| 12 | Haversine distances rerun on the repaired village list |
| 13 | Route the newly matched villages and assemble the final tables |

## Data (not included)

This project is code only. The facility list and the priority village lists are internal
documents from BPJS and a coordinating ministry, so neither they nor anything derived from
them are in this repository. The scripts expect them here:

```
Data Kementrian Koordinator dan FKTP/
  Data_FKTP_Selindo_Magang.xlsx - Sheet1.csv          facility list (BPJS)
  DesaPrioritas1_MALUKU_filter_faskes_2026-07-18.xlsx priority villages (coordinating ministry)
  DesaPrioritas1_MALUKU_UTARA_filter_faskes_2026-07-18.xlsx
BATAS WILAYAH KELURAHAN-DESA 10K.zip                  village boundaries (BIG geoportal)
Output/                                               created by the scripts
```

The QGIS transport layers used for the land, sea and air check are not included either. The
figures under Result are aggregate counts from the internship report.

```bash
pip install pandas geopandas shapely requests openpyxl jupyter
```
