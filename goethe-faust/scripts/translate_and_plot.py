"""
translate_and_plot.py
=====================
Load items-dataframe.parquet, aggregate all plot data directly from the
DataFrame, translate German labels with the local opus-mt-de-en model, then
regenerate all figures with English labels.

Run:
    HF_HOME=.../goethe-faust/data/hf-cache HF_HUB_DISABLE_XET=1 \\
    python scripts/translate_and_plot.py
"""

import warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from pathlib import Path
from transformers import MarianMTModel, MarianTokenizer

warnings.filterwarnings("ignore")

PROJECT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT / "output"

# ── Load DataFrame ────────────────────────────────────────────────────────────

print("Loading items-dataframe.parquet ...")
df = pd.read_parquet(PROJECT / "output" / "items-dataframe.parquet")
total = len(df)
print(f"  {total:,} records loaded")

# ── Aggregate ─────────────────────────────────────────────────────────────────

# Metadata format  (already English from build_dataframe.py)
fmt_vc     = df["metadata_format"].value_counts()
fmt_labels = fmt_vc.index.tolist()
fmt_counts = fmt_vc.values.tolist()

# Sector totals + digitized split  (labels already English)
sector_dig = (
    df.groupby(["sector", "digitized"])
      .size()
      .unstack(fill_value=0)
      .rename(columns={True: "digitized_true", False: "digitized_false"})
)
sector_dig["total"] = sector_dig["digitized_true"] + sector_dig["digitized_false"]
sector_dig = sector_dig.sort_values("total", ascending=False)

sectors_en = sector_dig.index.tolist()
dig_true   = sector_dig["digitized_true"].tolist()
dig_false  = sector_dig["digitized_false"].tolist()
totals_sec = sector_dig["total"].tolist()

# Providers  (proper names — no translation)
prov_vc     = df["provider_name"].value_counts().head(15)
prov_labels = prov_vc.index.tolist()
prov_counts = prov_vc.values.tolist()

# dc:type  (German — needs translation)
dct_vc         = df["dc_type"].explode().dropna().value_counts().head(20)
dc_types_raw   = dct_vc.index.tolist()
dc_type_counts = dct_vc.values.tolist()

# dc:subject  (German — needs translation)
dcs_vc           = df["dc_subject"].explode().dropna().value_counts().head(30)
dc_subjects_raw  = dcs_vc.index.tolist()
dc_subject_counts = dcs_vc.values.tolist()

# View field names  (German — needs translation)
vf_vc        = df["view_fields"].explode().dropna().value_counts().head(20)
vf_names_raw = vf_vc.index.tolist()
vf_counts    = vf_vc.values.tolist()

# ── Load translation model ────────────────────────────────────────────────────

print("Loading opus-mt-de-en ...")
tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-de-en")
model     = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-de-en")


def translate_batch(texts, batch_size=32):
    results = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True,
                           truncation=True, max_length=128)
        out = model.generate(**inputs, num_beams=4)
        results.extend(tokenizer.decode(t, skip_special_tokens=True) for t in out)
    return results


# ── Translate ─────────────────────────────────────────────────────────────────

all_terms  = list(dict.fromkeys(dc_types_raw + dc_subjects_raw + vf_names_raw))
print(f"Translating {len(all_terms)} unique terms ...")
translated = translate_batch(all_terms)
tr = dict(zip(all_terms, translated))

# Manual overrides for imprecise machine translations
OVERRIDES = {
    "Hochschulschrift":              "Thesis/Dissertation",
    "Druckgraphik":                  "Printmaking",
    "Sachakte":                      "Subject file",
    "Bestand":                       "Holdings",
    "Urheber":                       "Creator",
    "Szenenbild":                    "Stage design",
}
tr.update(OVERRIDES)


def t(term):
    return tr.get(term, term)


dc_types_en    = [t(x) for x in dc_types_raw]
dc_subjects_en = [t(x) for x in dc_subjects_raw]
vf_names_en    = [t(x) for x in vf_names_raw]

# ── Plot helpers ──────────────────────────────────────────────────────────────

plt.rcParams.update({
    "font.family": "sans-serif",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

C = {
    "blue":    "#4C72B0",
    "blue_lt": "#C8D8F0",
    "green":   "#55A868",
    "orange":  "#DD8452",
    "red":     "#C44E52",
    "purple":  "#8172B3",
    "teal":    "#64B5CD",
}


def hbar(ax, labels, values, color, title, xlabel=None, fontsize=9):
    n = len(labels)
    y = range(n)
    bars = ax.barh(y, values, color=color, height=0.65)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=fontsize)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=10, fontweight="bold", pad=6)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="x", alpha=0.35)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    vmax = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + vmax * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", ha="left", fontsize=fontsize - 1)
    ax.set_xlim(0, vmax * 1.18)


def pie_chart(ax, labels, values, title):
    _, _, autotexts = ax.pie(
        values, labels=None, autopct="%1.1f%%",
        pctdistance=0.75, startangle=90,
        wedgeprops={"linewidth": 0.5, "edgecolor": "white"},
    )
    for at in autotexts:
        at.set_fontsize(7.5)
    ax.legend(labels, loc="lower center", bbox_to_anchor=(0.5, -0.25),
              fontsize=7.5, ncol=2, frameon=False)
    ax.set_title(title, fontsize=10, fontweight="bold", pad=6)


def save(fig, name):
    path = OUT_DIR / name
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved: {name}")


# ── fig2: sector split by digitized ──────────────────────────────────────────

n = len(sectors_en)
y = np.arange(n)
fig, ax = plt.subplots(figsize=(10, 5))
bars_t = ax.barh(y, dig_true,  height=0.55, color=C["blue"],    label="Digitized = true")
bars_f = ax.barh(y, dig_false, height=0.55, left=dig_true,
                 color=C["blue_lt"], label="Digitized = false")
ax.set_yticks(y)
ax.set_yticklabels(sectors_en, fontsize=10)
ax.invert_yaxis()
ax.set_xlabel("Number of records", fontsize=10)
ax.set_title("Records by Sector  ·  split by Digitized",
             fontsize=12, fontweight="bold", pad=10)
ax.grid(axis="x", alpha=0.35)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.set_xlim(0, max(totals_sec) * 1.18)
for i, tot in enumerate(totals_sec):
    ax.text(tot + max(totals_sec) * 0.01, y[i], f"{tot:,}",
            va="center", ha="left", fontsize=9)
for bar, val in zip(bars_t, dig_true):
    if val > max(totals_sec) * 0.05:
        ax.text(val / 2, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", ha="center", fontsize=8,
                color="white", fontweight="bold")
ax.legend(loc="lower right", frameon=False, fontsize=9)
fig.tight_layout()
save(fig, "fig2_sector.png")

# ── fig4: dc_type ─────────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(9, 5.5))
hbar(ax, dc_types_en, dc_type_counts, C["red"], "Top 20 dc:Type Values", "records")
fig.tight_layout()
save(fig, "fig4_dc_type_top20.png")

# ── fig5: dc_subject ──────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(11, 8))
hbar(ax, dc_subjects_en, dc_subject_counts, C["purple"],
     "Top 30 dc:Subject Values", "records", fontsize=9)
fig.tight_layout()
save(fig, "fig5_dc_subject_top30.png")

# ── fig6: view fields ─────────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(11, 5.5))
hbar(ax, vf_names_en, vf_counts, C["teal"],
     "Top 20 Display Field Names (by occurrence)",
     "Total occurrences across all records", fontsize=9)
fig.tight_layout()
save(fig, "fig6_view_fields_top20.png")

# ── dataset-summary dashboard ─────────────────────────────────────────────────

fig = plt.figure(figsize=(18, 20))
fig.suptitle(
    f"DDB Goethe-Faust Item Dataset  ·  {total:,} records",
    fontsize=14, fontweight="bold", y=0.995,
)
gs = gridspec.GridSpec(3, 2, figure=fig,
                       hspace=0.52, wspace=0.38,
                       left=0.06, right=0.97, top=0.97, bottom=0.03)

ax0 = fig.add_subplot(gs[0, 0])
pie_chart(ax0, fmt_labels, fmt_counts, "Metadata Format")

ax1 = fig.add_subplot(gs[0, 1])
hbar(ax1, sectors_en, totals_sec, C["green"], "Records by Sector", "records")

ax2 = fig.add_subplot(gs[1, :])
hbar(ax2, prov_labels, prov_counts, C["orange"],
     "Top 15 Providers by Record Count", "records", fontsize=9)

ax3 = fig.add_subplot(gs[2, 0])
hbar(ax3, dc_types_en, dc_type_counts, C["red"], "Top 20 dc:Type Values", "records")

ax4 = fig.add_subplot(gs[2, 1])
hbar(ax4, dc_subjects_en[:20], dc_subject_counts[:20], C["purple"],
     "Top 20 dc:Subject Values", "records")

save(fig, "dataset-summary.png")

print("\nAll figures regenerated.")
