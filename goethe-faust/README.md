# DDB Goethe–*Faust* Corpus

Metadata for 115,432 Deutsche Digitale Bibliothek (DDB) objects retrieved via the keywords *Goethe* and *Faust*, prepared for the babel-ddb paper (Appendix B). Hosted at [ISE-FIZKarlsruhe/ddbkg/goethe-faust](https://github.com/ISE-FIZKarlsruhe/ddbkg/tree/main/goethe-faust).

## Corpus overview

| Metric | Value |
|---|---|
| Total records | 115,432 |
| Queries | "goethe" (96,773) + "faust" (25,275), deduplicated |
| Unique providers | 454 |
| Records with date | 102,467 (88.8%) |
| Year range | 1010–2025 |
| Digitized | 73,045 (63.3%) |

For full breakdown by sector, metadata format, and digitization status, see [`summary-final-dataset.md`](summary-final-dataset.md).

## Directory layout

```
data/
  ids-all-goethe-faust.txt      — 115,432 DDB object IDs (one per line)
  items-excerpt-1000.json       — 1,000-record sample for inspection
  items-all-goethe-faust.json   — full JSONL (gitignored; ~large)

output/
  items-dataframe.parquet.zip   — flat DataFrame (115,432 × 10)
  items-dataframe-sample.csv    — first 500 rows
  years-analysis.json           — year extraction results
  items-analysis.json           — 6-dimension aggregation
  ddb-type2fabio.json           — objecttype → FaBiO/DoCO mappings
  view_id_name.json             — unique (id, name) pairs from view.fields
  fig_years.png                 — temporal distribution (25-yr buckets, 1600–present)
  fig1_metadata_format.png      — metadata format pie chart
  fig2_sector.png               — sector × digitization bar chart
  fig4_dc_type_top20.png        — top 20 dc:type values
  fig5_dc_subject_top20.png     — top 20 dc:subject values

scripts/                        — pipeline scripts (see scripts/README.md)
requirements.txt                — Python dependencies
```

## Reproducing the dataset

Run scripts in order. All scripts use project-relative paths and can be run from any working directory.

1. **Fetch search results** — `python scripts/fetch-search-all.py`
   Requires a DDB API key. Outputs `data/ddb-search-goethe-all.json`.

2. **Fetch item records** — `cd data && bash ../scripts/fetch-items.sh ids-all-goethe-faust.txt`
   Saves individual JSON files and appends to `data/items-all-goethe-faust.json`.
   To fill any gaps: `python scripts/find_missing_items.py`, then re-run `fetch-items.sh ids-missing.txt`.

3. **Build parquet** — `python scripts/build_dataframe.py`
   Outputs `output/items-dataframe.parquet` (115,432 × 10) and a 500-row CSV sample.

4. **Analyse** — `python scripts/analyse_items.py` · `python scripts/analyse_years.py` · `python scripts/analyse_bucket.py`

5. **Visualise (German labels)** — `python scripts/visualise_items.py`

6. **Visualise (English, LaTeX)** — `HF_HOME=data/hf-cache HF_HUB_DISABLE_XET=1 python scripts/plot_latex_figs.py`
   Uses Helsinki-NLP/opus-mt-de-en (cached in `data/hf-cache/`); produces the four figures used in the paper.

7. **Map objecttypes to FaBiO** — `python scripts/match_objecttypes.py`
   Outputs `output/ddb-type2fabio.json`.

See [`scripts/README.md`](https://github.com/ISE-FIZKarlsruhe/ddbkg/blob/main/goethe-faust/scripts/README.md) for full per-script documentation.

## Caveats

- The 2000–2024 temporal bucket is dominated by Goethe-Universität Frankfurt institutional records (theses, working papers) rather than cultural-heritage items about Goethe or *Faust*.
- 2,552 pre-1600 records are excluded from `fig_years.png` but retained in `years-analysis.json`.
- 1 ID was permanently unavailable (HTTP 404) and is absent from the JSONL.
