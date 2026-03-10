# Scripts

All scripts live in `scripts/`. They use project-relative paths via
`pathlib.Path(__file__).resolve().parent.parent`, so they can be run from
any working directory.

---

## Data pipeline (run in order)

### `fetch-search-all.py`
Fetches all DDB search results for the query "goethe" via the DDB Solr API
and merges them into a single JSON file.

- **Input**: DDB Solr API (live network access required)
- **Output**: `data/ddb-search-goethe-all.json`
- **Usage**: `python scripts/fetch-search-all.py`
- **Notes**: `TOTAL` must match the actual result count; update if the
  dataset changes. 0.3 s delay between requests to avoid rate-limiting.

### `build_dataframe.py`
Builds a flat per-object DataFrame from the raw JSONL.

- **Input**: `data/items-all-goethe-faust.json`
- **Output**: `output/items-dataframe.parquet` (115,398 × 10, 8.6 MB),
  `output/items-dataframe-sample.csv` (first 500 rows)
- **Columns**: `object_id`, `sector`, `provider_name`, `timespan_begin`,
  `timespan_end`, `dc_type` (list), `dc_subject` (list), `metadata_format`,
  `view_fields` (list), `digitized` (bool)
- **Usage**: `python scripts/build_dataframe.py`
- **Dependencies**: `pandas`, `pyarrow`
- **Notes**:
  - `YEAR_RE` handles both free-text years and compact YYYYMMDD dates
    (e.g. `18300213`) via two regex alternatives
  - `timespan_begin` priority: `edm.RDF.TimeSpan.begin` →
    `edm.RDF.TimeSpan.end` → `edm.RDF.ProvidedCHO.issued` (fallback)
  - After fixes: 12,958 records (~11.2%) still lack a `timespan_begin` year

---

## Analysis scripts

### `analyse_bucket.py`
Reports top N dc:type and dc:subject values for records within a given
`timespan_begin` year range. Reads from the parquet DataFrame.

- **Input**: `output/items-dataframe.parquet`
- **Output**: printed summary (or JSON with `--json`)
- **Usage**:
  ```
  python scripts/analyse_bucket.py --start 2000 --end 2024
  python scripts/analyse_bucket.py --start 2000 --end 2024 --top 10 --json
  ```
- **Dependencies**: `pandas`, `pyarrow`
- **Notes**: Useful for characterising anomalous buckets in `fig_years.png`
  (e.g. the 2000–2024 spike is dominated by Goethe-Universität Frankfurt
  institutional records — theses and working papers — rather than cultural
  heritage items)

### `analyse_items.py`
Aggregates item-level statistics across 6 dimensions from the raw JSONL.

- **Input**: `data/items-all-goethe-faust.json`
- **Output**: `output/items-analysis.json`
- **Usage**: `python scripts/analyse_items.py`

### `analyse_years.py`
Extracts creation years from `edm.RDF.TimeSpan`, selects an optimal bucket
size, and produces a bar chart. X-range restricted to 1600–present; linear
y-scale.

- **Input**: `data/items-all-goethe-faust.json`
- **Output**: `output/fig_years.png`, `output/years-analysis.json`
- **Usage**: `python scripts/analyse_years.py`
- **Notes**:
  - `YEAR_RE` handles YYYYMMDD dates; 85.8% of records have a usable year
  - Auto-selects bucket size (5 / 10 / 25 / 50 / 100 yr) to keep ≤ 45 bins;
    25-year buckets selected (18 non-empty bins from 1600+)
  - Pre-1600 records (n = 2,551) omitted from chart; included in JSON
  - Goethe era (1749–1832) highlighted in red
  - Bar counts: inside bars (white) for tall bars; above for short bars

### `audit_timespan_coverage.py`
Audits temporal coverage: for records missing a `TimeSpan` year, checks
whether `dc:date`, `dc:issued` (and dcterms equivalents) in `ProvidedCHO`
could provide a fallback year. Also reports all `ProvidedCHO` keys present
in those records, to identify further date-bearing fields.

- **Input**: `data/items-all-goethe-faust.json`
- **Output**: printed summary (no files written)
- **Usage**: `python scripts/audit_timespan_coverage.py`
- **Notes**: Led to discovery that `YEAR_RE` was broken for YYYYMMDD dates
  and that `issued` is a viable fallback; both fixes applied to
  `build_dataframe.py` and `analyse_years.py`

### `match_objecttypes.py`
Maps DDB objecttype strings to FaBiO / DoCO ontology classes using a
4-tier pipeline: exact match → translated exact match → Levenshtein →
sentence embeddings.

- **Input**: `data/ddb-search-goethe-all.json`, `data/schemas/fabio.owl`,
  `data/schemas/doco.owl`
- **Output**: `output/ddb-type2fabio.json`
- **Usage**: `python scripts/match_objecttypes.py`
- **Dependencies**: `deep-translator`, `rapidfuzz`, `sentence-transformers`,
  `rdflib`

### `summarise_results.py`
Prints a human-readable summary of `ddb-type2fabio.json`.

- **Input**: `output/ddb-type2fabio.json`
- **Output**: printed summary (no files written)
- **Usage**: `python scripts/summarise_results.py`

---

## Visualisation scripts

### `visualise_items.py`
Generates figures from `items-analysis.json` (German labels, pre-translation).

- **Input**: `output/items-analysis.json`
- **Output**: `output/fig1_metadata_format.png`, `output/fig2_sparte.png`,
  `output/fig3_providers_top20.png`, `output/fig4_dc_type_top20.png`,
  `output/fig5_dc_subject_top30.png`, `output/fig6_view_fields_top20.png`
- **Usage**: `python scripts/visualise_items.py`
- **Notes**: Labels remain in German. Use `translate_and_plot.py` or
  `plot_latex_figs.py` for English-translated versions.

### `translate_and_plot.py`
Translates German labels with Helsinki-NLP/opus-mt-de-en and regenerates
all figures with English labels. Reads from the parquet DataFrame.

- **Input**: `output/items-dataframe.parquet`
- **Output**: `output/fig2_sector.png`, `output/fig4_dc_type_top20.png`,
  `output/fig5_dc_subject_top30.png`, `output/fig6_view_fields_top20.png`,
  `output/dataset-summary.png`
- **Usage**:
  ```
  HF_HOME=data/hf-cache HF_HUB_DISABLE_XET=1 python scripts/translate_and_plot.py
  ```
- **Dependencies**: `transformers`, `pandas`, `pyarrow`, `matplotlib`
- **Notes**: Model cached in `data/hf-cache/`. Manual overrides in `OVERRIDES`
  dict for domain-specific terms (Hochschulschrift, Druckgraphik, etc.)

### `plot_latex_figs.py`
Regenerates 4 figures as square 7×7 in PNGs (1050×1050 px) for a LaTeX
2×2 subfigure layout. Translates German labels via opus-mt-de-en.

- **Input**: `output/items-dataframe.parquet`
- **Output**: `output/fig1_metadata_format.png`, `output/fig2_sector.png`,
  `output/fig4_dc_type_top20.png`, `output/fig5_dc_subject_top20.png`
- **Usage**:
  ```
  HF_HOME=data/hf-cache HF_HUB_DISABLE_XET=1 python scripts/plot_latex_figs.py
  ```
- **Dependencies**: `transformers`, `pandas`, `pyarrow`, `matplotlib`
- **Notes**: `fig5` is top-20 subjects (not top-30). `fig1` uses explicit
  subplot margins (not `bbox_inches="tight"`) to preserve square aspect ratio.

### `extract_view_id_name.py`
Extracts unique `(id, name)` pairs from `view.fields` across all items in a
JSON or NDJSON file.

- **Input**: any JSON array or NDJSON file of item objects
- **Output**: JSON array of `[id, name]` tuples, one per line, sorted by id
- **Usage**: `python scripts/extract_view_id_name.py <input> <output>`
- **Example**:
  ```
  python scripts/extract_view_id_name.py data/items-all-goethe-faust.json output/view_id_name.json
  ```

### `extract_view_fields.py`
Extracts and pretty-prints `view.fields` for a single item by ID.

- **Input**: `data/items/<item-id>.json`
- **Output**: `view-<item-id>.json` (project root)
- **Usage**: `python scripts/extract_view_fields.py <item-id>`
- **Example**:
  ```
  python scripts/extract_view_fields.py 222SF6AM6ZCXSJTNREHJUCX5SRTJDBK7
  ```

---

## Data-collection scripts

### `fetch-items.sh`
Fetches DDB item records by ID from the DDB API, saves each as an individual
JSON file, and appends compact single-line JSON to the JSONL file. Skips IDs
already present in the JSONL. Must be run from the `data/` directory.

- **Input**: `<ids-file>` (one ID per line), optional `[limit]` count
- **Output**: `data/items/<uuid>.json` per record; appends to
  `data/items-all-goethe-faust.json`
- **Usage**:
  ```
  cd data && bash ../scripts/fetch-items.sh ids-all-goethe-faust.txt
  cd data && bash ../scripts/fetch-items.sh ids-missing.txt   # re-fetch gap
  ```
- **Notes**: 0.2 s delay between requests. HTTP failures are logged but do not
  abort the run; failed IDs can be re-fetched by running again.

### `find_missing_items.py`
Compares `ids-all-goethe-faust.txt` against `items-all-goethe-faust.json` and
writes the gap — IDs present in the list but absent from the JSONL — to
`ids-missing.txt` for targeted re-fetching.

- **Input**: `data/ids-all-goethe-faust.txt`, `data/items-all-goethe-faust.json`
- **Output**: `data/ids-missing.txt`
- **Usage**:
  ```
  python scripts/find_missing_items.py
  cd data && bash ../scripts/fetch-items.sh ids-missing.txt
  ```

### `fetch-progress.sh`
Shell script to monitor fetch progress.
