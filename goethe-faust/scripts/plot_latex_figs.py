#!/usr/bin/env python3
"""
plot_latex_figs.py
==================
Regenerate 4 figures as square PNGs for a LaTeX 2 × 2 subfigure layout.

  fig1_metadata_format.png  — metadata format distribution (pie chart)
  fig2_sector.png           — records by sector, split by digitized (stacked bar)
  fig4_dc_type_top20.png    — top 20 dc:type values (horizontal bar)
  fig5_dc_subject_top20.png — top 20 dc:subject values (horizontal bar)

All figures: 7 × 7 in at 150 dpi (1 050 × 1 050 px).

Run:
    HF_HOME=<project>/data/hf-cache HF_HUB_DISABLE_XET=1 \\
    python scripts/plot_latex_figs.py
"""

import warnings
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from pathlib import Path
from transformers import MarianMTModel, MarianTokenizer

warnings.filterwarnings("ignore")

PROJECT = Path(__file__).resolve().parent.parent
OUT_DIR = PROJECT / "output"

SQ  = 7    # square side in inches
DPI = 150  # → 1 050 × 1 050 px

# ── Load DataFrame ────────────────────────────────────────────────────────────

print("Loading items-dataframe.parquet ...")
df    = pd.read_parquet(PROJECT / "output" / "items-dataframe.parquet")
total = len(df)
print(f"  {total:,} records loaded")

# ── Aggregate ─────────────────────────────────────────────────────────────────

# Metadata format (already English)
fmt_vc     = df["metadata_format"].value_counts()
fmt_labels = fmt_vc.index.tolist()
fmt_counts = fmt_vc.values.tolist()

# Sector × digitized (sector labels already English)
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

# dc:type top 20 (German — needs translation)
dct_vc         = df["dc_type"].explode().dropna().value_counts().head(20)
dc_types_raw   = dct_vc.index.tolist()
dc_type_counts = dct_vc.values.tolist()

# dc:subject top 20 (German — needs translation)
dcs_vc            = df["dc_subject"].explode().dropna().value_counts().head(20)
dc_subjects_raw   = dcs_vc.index.tolist()
dc_subject_counts = dcs_vc.values.tolist()

# ── Translation ───────────────────────────────────────────────────────────────

print("Loading opus-mt-de-en ...")
tokenizer = MarianTokenizer.from_pretrained("Helsinki-NLP/opus-mt-de-en")
model     = MarianMTModel.from_pretrained("Helsinki-NLP/opus-mt-de-en")


def translate_batch(texts, batch_size=32):
    results = []
    for i in range(0, len(texts), batch_size):
        batch  = texts[i : i + batch_size]
        inputs = tokenizer(batch, return_tensors="pt", padding=True,
                           truncation=True, max_length=128)
        out    = model.generate(**inputs, num_beams=4)
        results.extend(tokenizer.decode(t, skip_special_tokens=True) for t in out)
    return results


all_terms  = list(dict.fromkeys(dc_types_raw + dc_subjects_raw))
print(f"Translating {len(all_terms)} unique terms ...")
translated = translate_batch(all_terms)
tr = dict(zip(all_terms, translated))

OVERRIDES = {
    "Hochschulschrift": "Thesis/Dissertation",
    "Druckgraphik":     "Printmaking",
    "Sachakte":         "Subject file",
    "Bestand":          "Holdings",
    "Urheber":          "Creator",
    "Szenenbild":       "Stage design",
}
tr.update(OVERRIDES)


def t(term):
    return tr.get(term, term)


dc_types_en    = [t(x) for x in dc_types_raw]
dc_subjects_en = [t(x) for x in dc_subjects_raw]

# ── Style ─────────────────────────────────────────────────────────────────────

plt.rcParams.update({
    "font.family":       "sans-serif",
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "figure.dpi":        DPI,
})

C = {
    "blue":    "#4C72B0",
    "blue_lt": "#C8D8F0",
    "green":   "#55A868",
    "red":     "#C44E52",
    "purple":  "#8172B3",
}


def hbar_sq(ax, labels, values, color, title, xlabel=None):
    """Horizontal bar chart sized for a square figure."""
    n    = len(labels)
    y    = range(n)
    bars = ax.barh(y, values, color=color, height=0.62)
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.set_title(title, fontsize=10, fontweight="bold", pad=6)
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=8)
    ax.grid(axis="x", alpha=0.35)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
    vmax = max(values) if values else 1
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + vmax * 0.015,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", ha="left", fontsize=7,
        )
    ax.set_xlim(0, vmax * 1.24)


def save(fig, name, tight=True):
    path = OUT_DIR / name
    kw = {"bbox_inches": "tight"} if tight else {"dpi": DPI}
    fig.savefig(path, **kw)
    plt.close(fig)
    print(f"  Saved: {name}")


# ── fig1: metadata format pie ─────────────────────────────────────────────────
# Use explicit subplot margins (no tight bbox) to keep the figure square.

fig, ax = plt.subplots(figsize=(SQ, SQ))
_, _, autotexts = ax.pie(
    fmt_counts, labels=None, autopct="%1.1f%%",
    pctdistance=0.75, startangle=90,
    wedgeprops={"linewidth": 0.5, "edgecolor": "white"},
)
for at in autotexts:
    at.set_fontsize(8)
ax.legend(
    fmt_labels, loc="upper center", bbox_to_anchor=(0.5, -0.04),
    fontsize=8, ncol=3, frameon=False,
)
ax.set_title("Metadata Format Distribution",
             fontsize=11, fontweight="bold", pad=10)
# Reserve bottom margin for legend; axes centred in the square canvas.
fig.subplots_adjust(top=0.92, bottom=0.18, left=0.05, right=0.95)
save(fig, "fig1_metadata_format.png", tight=False)

# ── fig2: sector × digitized stacked bar ─────────────────────────────────────

n      = len(sectors_en)
y      = np.arange(n)
tmax   = max(totals_sec)

fig, ax = plt.subplots(figsize=(SQ, SQ))
bars_t = ax.barh(y, dig_true,  height=0.55, color=C["blue"],    label="Digitized")
bars_f = ax.barh(y, dig_false, height=0.55, left=dig_true,
                 color=C["blue_lt"], label="Not digitized")
ax.set_yticks(y)
ax.set_yticklabels(sectors_en, fontsize=9)
ax.invert_yaxis()
ax.set_xlabel("Number of records", fontsize=9)
ax.set_title("Records by Sector  ·  Digitized vs. Not",
             fontsize=11, fontweight="bold", pad=8)
ax.grid(axis="x", alpha=0.35)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))
ax.set_xlim(0, tmax * 1.22)
for i, tot in enumerate(totals_sec):
    ax.text(tot + tmax * 0.012, y[i], f"{tot:,}",
            va="center", ha="left", fontsize=8.5)
for bar, val in zip(bars_t, dig_true):
    if val > tmax * 0.05:
        ax.text(val / 2, bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", ha="center",
                fontsize=8, color="white", fontweight="bold")
ax.legend(loc="lower right", frameon=False, fontsize=9)
fig.tight_layout()
save(fig, "fig2_sector.png")

# ── fig4: dc:type top 20 ─────────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(SQ, SQ))
hbar_sq(ax, dc_types_en, dc_type_counts, C["red"],
        "Top 20 dc:Type Values", "records")
fig.tight_layout()
save(fig, "fig4_dc_type_top20.png")

# ── fig5: dc:subject top 20 ──────────────────────────────────────────────────

fig, ax = plt.subplots(figsize=(SQ, SQ))
hbar_sq(ax, dc_subjects_en, dc_subject_counts, C["purple"],
        "Top 20 dc:Subject Values", "records")
fig.tight_layout()
save(fig, "fig5_dc_subject_top20.png")

print("\nAll 4 square figures saved.")
