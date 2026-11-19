# 03 Industrial Dispute Court Scraper

BPJS Kesehatan needed a traceable reference for verifying when a wage-earning member's
employment had been terminated. Industrial dispute (PHI) cases are public on each district
court's SIPP case-tracking portal, but only as web pages opened one at a time. This scraper
turns a court's PHI case list into a table.

## Coverage

The target was the district court in each of Indonesia's 38 provincial capitals
(`PHI_LINKS_IBUKOTA.xlsx`). Checking each portal first:

| Portal status | Courts |
|---|---|
| Reachable with PHI cases | 28 |
| Reachable, but no PHI case list | 6 |
| Not reachable | 4 |

By the end of the internship, 11 courts had been collected in full: 11,150 cases, 89.0% of
them termination disputes.

## How it works

- **Detection.** From a court's home page it finds the PHI case list, identifies the case
  table, and maps its columns by header text, because the portals differ in layout.
- **Pagination.** The portals sit behind Cloudflare and page through results with JavaScript,
  so paging uses a real Chrome session (`undetected-chromedriver`) and waits for the table to
  actually change before reading the next page.
- **Parties.** The parties cell lists plaintiffs and defendants in one block; they are split
  into a consistent `Penggugat: ... | Tergugat: ...` form.
- **Batch runs.** `Automated Scrapper.ipynb` works through the spreadsheet of courts. A failure
  at one court (unreachable site, no PHI menu, a CAPTCHA) is logged to `OUTPUT/batch_log.xlsx`
  and the run moves on to the next court.
- **Politeness.** A fixed delay between requests and a longer one between courts.

| Notebook | Purpose |
|---|---|
| `Manual Scrapper.ipynb` | Scrape a single court by URL |
| `Automated Scrapper.ipynb` | Batch run over every court in the spreadsheet |
| `Perhitungan Ibu Kota.ipynb` | Count cases and parties across the combined output |

Output goes to `OUTPUT/CSV/` and `OUTPUT/EXCEL/`, one file per court. The CSVs for all 11
collected courts are included in `OUTPUT/CSV/`; they are public records from the SIPP portals.
Columns: case number, registration date, case classification, parties, status, duration, and
the link to the case page.

```bash
pip install requests beautifulsoup4 pandas openpyxl undetected-chromedriver selenium jupyter
```

`CHROME_MAJOR_VERSION` at the top of each scraper must match the installed Chrome.
