# GeMeA — NER Annotation Guide (SR-08)

Companion to [sr08_gold-set-composition.md](sr08_gold-set-composition.md).
Used by **human annotators** and **LLM annotators** (SR-11).

---

## 1. Summary

You are labeling **named entity spans** in German bibliographic title strings from the Deutsche Digitale Bibliothek (DDB). Each record contains a single title string. Your job is to mark which substrings are the main title, a subtitle, or a responsible person — and to record the exact character positions of each span.

The corpus spans five centuries of German print culture, from 16th-century Early Modern German title pages to 20th-century library catalog entries. The annotation rules differ significantly by era: modern titles follow ISBD punctuation conventions; pre-1700 titles place the author's credentials *before* the title with no separator.

| Section | What it covers |
|---|---|
| [§2 Workflow](#2-workflow) | Files, annotation status, suggested order — **start here** |
| [§3 Label definitions](#3-label-definitions) | What TITLE, OTHER_TITLE, PERSON and Phase 2 labels mark |
| [§4 Decision flowchart](#4-decision-flowchart) | Step-by-step logic for choosing labels |
| [§5 Examples](#5-examples-by-title-structure) | 10 worked examples with DDB links, grouped by title structure |
| [§6 What NOT to label](#6-what-not-to-label) | Frequent false-positive patterns and why they are not entities |
| [§7 Span boundary rules](#7-span-boundary-rules) | Technical rules for character offsets |
| [§8 Output format](#8-output-format-jsonl) | JSONL record schema |
| [§9 Verification](#9-verification) | Script to check offset integrity after each batch |
| [§10 LLM annotator instructions](#10-instructions-for-llm-annotators) | Input/output format and self-check for LLM-assisted annotation |

**Quick start for human annotators:** read §2 to understand the files and suggested order, then use §3–§5 as reference while annotating. When in doubt about a boundary, check §6 first, then §5.

**Quick start for LLM annotators:** read §3, §4, and §6 fully; then follow the task format in §10.

---

## 2. Workflow

### 2.1 Files

Annotation is done in **doccano**. The files below are inputs and references.

| File | Contents | Action |
|---|---|---|
| `data/annotation/sr08_manual_queue.csv` | 212 records flagged `manual`, sorted pre-1700 first | Open first — determines which records to annotate and in what order |
| `data/annotation/sr08_gold_prefilled.jsonl` | All 395 records; spans pre-filled where possible | Source import for doccano |
| `data/annotation/export_245867_pretty.json` | Doccano export | Authoritative annotation output |
| `data/annotation/sr08_gold_sample.csv` | Original stratified sample with metadata | Reference only |

### 2.2 Annotation status

Each record in the JSONL has an `annotation_status` field indicating how much work it needs:

| Status | Count | Meaning |
|---|---|---|
| `pre-filled` | 47 | Tier-2 structural (`. -`), non-pre-1700 — high confidence; review and accept or correct |
| `partial` | 136 | Tier-1 heuristic, non-pre-1700 — spans are auto-extracted; verify each boundary |
| `manual` | 212 | Pre-1700 or tier-0 — no pre-filled spans; annotate from scratch |

### 2.3 Suggested order

Work through records in this order — harder strata first, so guideline questions surface early:

1. **Pre-1700 tier-0** (~130 records) — the hardest stratum; the evaluation rests on these; follow §5.8–§5.10 carefully; use the DDB link to view the full catalog record when the title string is unclear
2. **1700–1800 tier-0** (~37 records) — transitional register; may follow either pre-1700 or modern structure
3. **Modern / 19th-c tier-0** (~45 records) — no ISBD markers but modern structure; usually short
4. **Partial tier-1** (136 records) — review auto-extracted spans; correct boundaries where needed
5. **Pre-filled tier-2** (47 records) — spot-check only; most are correct

Change `annotation_status` to `reviewed` when you have verified and accepted a record.

---

## 3. Label definitions

### 3.1 Phase 1 — required for every record

| Label | What to mark | Typical cue |
|---|---|---|
| `TITLE` | The main work title — the primary intellectual content identifier. Exactly one per record. If no subtitle separator is present, the TITLE span may extend through what would otherwise be a subtitle. | Opening substantive noun phrase; before ` :` or ` /` in modern records; **after** the PERSON span in pre-1700 records |
| `OTHER_TITLE` | A subtitle or alternative title elaborating or qualifying the TITLE | After ` : `, `Das ist:`, `oder`, `nämlich`, `welches handelt von`, `, enthaltend` |
| `PERSON` | Named responsible person (author, editor) — full name **plus** all credentials, degree abbreviations, and role phrases that form a single naming unit with the name | After ` / ` in modern records; **before** the work title in pre-1700 records (no ` /` separator) |

**One TITLE per record.** A record almost always has exactly one TITLE span. If the string is a fragment or a bare description, annotate the most title-like phrase as TITLE.

**Why PERSON and not AUTHOR or CREATOR (design note):** The SoR position (` /`) in ISBD contains not just authors but also editors (`hrsg. von`), compilers, corporate bodies, and contributors. `AUTHOR` would be semantically wrong for `Jahrbuch / Deutsche Shakespeare-Gesellschaft` or `Statistische Berichte / Hessisches Statistisches Landesamt` — neither is an author. `CREATOR` is closer but still excludes editors and corporate agents. `PERSON` is the neutral term that marks *where the responsible agent appears in the string* without asserting a role. SR-04 confirmed this: only 35% of SoR entries are true author statements; 19% are corporate bodies, 5% editors, 41% non-SoR false positives. Role disambiguation (`f_resp_person`, `f_resp_org`, `f_resp_editor`) is a Phase 2 concern. This is also consistent with historical NER benchmarks (HIPE-2022, GermEval), which use `PER` rather than role-bearing labels for the same reason. If role-specific labels are needed downstream, they can be added as a sub-classification layer using the SR-04 `f_resp_*` flags without re-annotating spans.

### 3.2 Phase 2 — annotate when present; not evaluated in Phase 1

Annotate these in the same pass to avoid re-annotation when Phase 2 evaluation is due:

| Label | What to mark | Trigger |
|---|---|---|
| `TRANSLATOR` | Named translator | Only when a translation keyword is present: `übersetzt`, `Übers.`, `transl.`, `traduit par`, `ins Deutsche übertragen` |
| `PARALLEL_TITLE` | Title restated in a second language | After ` = ` or after ` / ` followed by a non-German title string |
| `MEDIUM` | Performance instrumentation (music only) | `für Klavier`, `für gemischten Chor und Orchester`, `op. 12` |

---

## 4. Decision flowchart

```
For each title string:

1. Is era == "pre-1700"?
   ├── YES → Does the string open with a credential sequence (degree + name + role phrase)?
   │         ├── YES → Mark credential+name+role as PERSON; remainder is TITLE (§5.8–§5.10)
   │         └── NO  → Mark full string as TITLE; no PERSON detectable from string alone
   └── NO  → Does the string contain ' / '?
             ├── YES → Is the text after ' / ' a single letter, date, or region name?
             │         ├── YES → TITLE only (series suffix or date — not a person)
             │         └── NO  → text before ' / ' → TITLE (and OTHER_TITLE if ' : ' present)
             │                   text after  ' / ' → PERSON (or PARALLEL_TITLE if non-German)
             └── NO  → Does the string contain ' : '?
                       ├── YES → Does ' : ' immediately precede a date range (dddd–dddd or d. Month dddd)?
                       │         ├── YES → TITLE only (life-date colon — not a subtitle separator)
                       │         └── NO  → text before ' : ' → TITLE
                       │                   text after  ' : ' → OTHER_TITLE
                       └── NO  → Full string → TITLE
```

---

## 5. Examples by title structure

Each example shows the input string, the correct annotation, and a link to the DDB source record.
Offsets are for the exact strings shown — verify with `title[start:end] == text`.

---

### 5.1 Subtitle only — ` :` present, no ` /`

**Input**
```
Jeversches Wochenblatt : Friesisches Tageblatt ; gegr. 1791
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/AGZJAK7XYRNH3IWXEWFVELM4OFBJARLL

**Annotation**
```json
[
  {"label": "TITLE",       "start":  0, "end": 22, "text": "Jeversches Wochenblatt"},
  {"label": "OTHER_TITLE", "start": 25, "end": 46, "text": "Friesisches Tageblatt"}
]
```
> `gegr. 1791` is a **founding year note** — do not label. Numbers following `gegr.`, `gestiftet`, `gegründet` are never YEAR entities.

---

### 5.2 SoR only — ` /` present, no ` :`; corporate body as responsible agent

**Input**
```
Jahrbuch / Deutsche Shakespeare-Gesellschaft ; 3
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/BDMEHSHZCBPUG6NL3OKG4FMKKGL4VHMH

**Annotation**
```json
[
  {"label": "TITLE",  "start":  0, "end":  8, "text": "Jahrbuch"},
  {"label": "PERSON", "start": 11, "end": 44, "text": "Deutsche Shakespeare-Gesellschaft"}
]
```
> `; 3` is a **volume number** — not a second PERSON. Stop the PERSON span at the semicolon.
> A corporate body (Gesellschaft, Landesamt, Institut, Universität) in SoR position is labeled `PERSON` — it is the responsible agent.

---

### 5.3 SoR with topic sub-series — stop PERSON at period or semicolon

**Input**
```
Statistische Berichte / Hessisches Statistisches Landesamt. B … ; Ergebnisse nach Verwaltungsbezirken …
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/GKSDCS5H4ERC4ZTPNRBOBMH5ZDU6WQN2

**Annotation**
```json
[
  {"label": "TITLE",  "start":  0, "end": 21, "text": "Statistische Berichte"},
  {"label": "PERSON", "start": 24, "end": 58, "text": "Hessisches Statistisches Landesamt"}
]
```
> `. B …` and `; Ergebnisse nach Verwaltungsbezirken …` are sub-series and topic designators — not additional PERSON spans. The PERSON span ends at the first `.` or `;` that introduces a topic qualifier.

---

### 5.4 Series letter suffix — ` /` followed by single letter; do NOT label as PERSON

**Input**
```
1988: Statistische Berichte der Freien und Hansestadt Hamburg / K
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/5VJBG7E7EIOY5VARC2MWNZTKHRKYPPYR

**Annotation**
```json
[
  {"label": "TITLE", "start": 6, "end": 63, "text": "Statistische Berichte der Freien und Hansestadt Hamburg"}
]
```
> `/ K` is a **series letter suffix** — never a PERSON. A single letter (or two-letter code) after ` / ` is always a series designator.
> The leading `1988:` is a date designator added by the cataloger — not part of the TITLE. Start the TITLE span after the colon and space.

---

### 5.5 Parallel title — ` /` followed by non-German title; DDB `::` separator

**Input**
```
Transnationales Strafrecht / Transnational Criminal Law :: gesammelte Beiträge ; collected publications
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/XDNVRXBWWZMMHHFOPZBUEVOOJYL6TGDH

**Annotation**
```json
[
  {"label": "TITLE",          "start":  0, "end": 26, "text": "Transnationales Strafrecht"},
  {"label": "PARALLEL_TITLE", "start": 29, "end": 55, "text": "Transnational Criminal Law"}
]
```
> `Transnational Criminal Law` after ` / ` is the title in a second language → `PARALLEL_TITLE` (Phase 2).
> `::` is a **DDB catalog-field separator**, not an ISBD area separator. Do not treat `gesammelte Beiträge` as OTHER_TITLE.

---

### 5.6 Life dates after colon — not a subtitle

**Input**
```
Johann Ludwig Böhner :7. Januar 1787 - 28. März 1860 ; [Katalog]
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/THF6HTNRUTSYTYBY377JLKXHCWVHNYQP

**Annotation**
```json
[
  {"label": "TITLE", "start": 0, "end": 20, "text": "Johann Ludwig Böhner"}
]
```
> `:7. Januar 1787 - 28. März 1860` are **life dates** — not a subtitle. When ` :` follows a person's name and is immediately followed by a date or date range, it is a life-date delimiter, not an ISBD subtitle separator.
> `[Katalog]` in brackets is a cataloger's note — not an OTHER_TITLE.

---

### 5.7 Life dates in parentheses — include in TITLE; `:` after them introduces OTHER_TITLE

**Input**
```
Porträt Georg Philipp Wucherer (1734 - 1805) :Kupferstich ; Radierung
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/7EG6MNM55XRFKT63ZIUZN35OZAZMMY2B

**Annotation**
```json
[
  {"label": "TITLE",       "start":  0, "end": 44, "text": "Porträt Georg Philipp Wucherer (1734 - 1805)"},
  {"label": "OTHER_TITLE", "start": 46, "end": 57, "text": "Kupferstich"}
]
```
> Life dates `(1734 - 1805)` are inside the TITLE span — they identify the depicted person and are part of the title phrase.
> Here ` :` follows a fully described subject (not a standalone person name), so `Kupferstich` is a genuine OTHER_TITLE indicating format.
> `Kupferstich` is a print medium note, not musical instrumentation — label OTHER_TITLE, not MEDIUM. MEDIUM is reserved for musical performance forces.

---

### 5.8 Pre-1700 — author-before-title; alchemical treatise

**Input**
```
David Beuthers, Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti, Zwey rare Chymische Tractate
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/KQCJ7APICPYVGBUZ544FKAICNU73FVKH

**Annotation**
```json
[
  {"label": "PERSON", "start":   0, "end": 102, "text": "David Beuthers, Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti"},
  {"label": "TITLE",  "start": 104, "end": 132, "text": "Zwey rare Chymische Tractate"}
]
```
> The full credential phrase `Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti` is part of the PERSON span. It identifies and qualifies the named person.
> TITLE begins at the first substantive noun phrase that names the work (`Zwey rare Chymische Tractate`). The separating `, ` (comma-space) between PERSON and TITLE is not included in either span.
> If a ` :` follows, label any subtitle content after it as OTHER_TITLE.
>
> **Why credential and name are merged into one PERSON span (design note):** A `PERSON_DESIGNATION` label splitting the bare name (`David Beuthers`) from the credential phrase was considered and deferred to Phase 2. Three reasons: (1) the pre-name degree abbreviations (`D.`, `M.`, `Lic.`) are fused with the name by German academic convention and the boundary is genuinely ambiguous; (2) standard BIO sequence labeling handles two adjacent spans at an uncertain boundary worse than one merged span; (3) for GND linking, name extraction from a merged PERSON span can be done in post-processing by stripping known degree prefixes and cutting at the first role-noun (`Professoris`, `Pfarrers`, `Pastoris`, `Meisters`). When Phase 2 annotation is scheduled, `PERSON_DESIGNATION` should cover both pre-name degrees and post-name role/location phrases, with the bare first-name + surname as the PERSON core.

---

### 5.9 Pre-1700 — Leichenpredigt; named deceased and husband embedded mid-title

**Input**
```
Leich-Sermon … Bey … Sepultur Der … Magdalenen Heidewig Stissers/ Deß … Johan Julii Herings … HaußFrawen …
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/7GZQOGDUS4AXD2LYGSHUWJPY6BDC3KMS

**Annotation**
```json
[
  {"label": "TITLE", "start": 0, "end": 107, "text": "Leich-Sermon … Bey … Sepultur Der … Magdalenen Heidewig Stissers/ Deß … Johan Julii Herings … HaußFrawen …"}
]
```
> `Magdalenen Heidewig Stissers` is the deceased; `Johan Julii Herings` is her husband. Both are named within the title description — **they are not the author**. Do not label them as PERSON.
> In a Leichenpredigt title, only label PERSON if the preacher (author) is explicitly identified by `verfasset von`, `gehalten von`, or ` /`.
> The `/` in `Stissers/` is an early modern orthographic slash inside the title string, not an ISBD SoR separator.

---

### 5.10 Pre-1700 — author identified by `Von` mid-string

**Input**
```
Handbuch des römischen Privatrechts … Von Theodor Schmalz, D. Königl. Preuss. Consistorialrathe und Professor …
```
**DDB:** https://www.deutsche-digitale-bibliothek.de/item/T6YL7Z2YEIEFTKDTG4GFDBIIZIFYHIBB

**Annotation**
```json
[
  {"label": "TITLE",  "start":  0, "end": 36, "text": "Handbuch des römischen Privatrechts"},
  {"label": "PERSON", "start": 41, "end": 111, "text": "Theodor Schmalz, D. Königl. Preuss. Consistorialrathe und Professor"}
]
```
> `Von` is an attribution keyword — the named person following it is the PERSON even when mid-string. The PERSON span starts after `Von `.
> Include the credential phrase (`D. Königl. Preuss. Consistorialrathe und Professor`) in the PERSON span.
> The ` …` at the end is a truncation marker — not part of any span.

---

## 6. What NOT to label

These patterns appear frequently and must not receive any label:

| Pattern | Example | Reason |
|---|---|---|
| Founding year | `gegr. 1791`, `gestiftet 1840` | Not a publication year; not a YEAR entity |
| Life dates in parentheses | `(1734 - 1805)` | Include in the enclosing TITLE span when they identify the subject |
| Life dates after colon | `:7. Januar 1787 - 28. März 1860` | Life-date delimiter, not a subtitle separator |
| Series letter suffix | `/ K`, `/ M`, `/ A1` | Single letter after ` / ` is always a series designator, never a PERSON |
| Volume number after `;` | `; 3`, `; Bd. 2` | Sub-series enumeration, not a second PERSON |
| Newspaper issue label | `Ausgabe vom Dienstag, den 18. Mai 1937` | Daily issue date, not an edition statement |
| DDB catalog separator | `::` | Not an ISBD area separator; what follows is not OTHER_TITLE |
| Cataloger's note | `[Katalog]`, `[Notizen]`, `[Entwurf]` | Bracketed additions by the cataloger, not part of the title |
| Generic dedicatee | `Herrn N.N. gewidmet` | Not the author; do not label PERSON |
| Embedded Latin phrases | `Anno MDXLVI`, `In nomine Dei` | Part of the enclosing TITLE or PERSON span |
| `durch` / `von` without translation keyword | `durch Johann Schmidt` | Label PERSON (author/editor), not TRANSLATOR |
| Leichenpredigt deceased | `Bey der Begräbnis … Maria Dorothea Müllers` | Subject of the sermon, not the author |

---

## 7. Span boundary rules

> For the full set of TITLE boundary curation decisions (leading articles, parentheticals, truncation markers, pre-1700 separator rules, etc.), see [sr08_title-boundary-curation.md](sr08_title-boundary-curation.md). The rules below state the general principles; that note is the authoritative reference for case-by-case decisions.

1. **Offsets are character positions** into the raw `title` string, 0-indexed, end-exclusive. `title[start:end]` must equal the `text` field exactly — this is checked by `sr08_verify_spans.py`.
2. **Trim leading and trailing whitespace** from span boundaries. `start` points to the first non-space character of the entity; `end` points one past the last non-space character.
3. **No overlapping spans.** If a credential and name could each be labeled separately, merge them into one PERSON span.
4. **No nested spans.** If a PERSON span would contain an embedded title fragment, stop the PERSON span before that fragment begins.
5. **Contiguous substrings only.** No gap spans — `start` to `end` must cover a single uninterrupted substring.
6. **Include the full naming unit in PERSON.** Degree abbreviation + first name + surname + role phrase + location phrase form one span: `D. Johann Gerhard, Professoris zu Jena` → one PERSON span, not three.
7. **Separating punctuation between spans is not included in either span.** The ` / `, ` : `, `, ` between TITLE and PERSON or OTHER_TITLE belongs to neither.

---

## 8. Output format (JSONL)

Each annotated record in `data/annotation/sr08_gold_prefilled.jsonl`:

```json
{
  "obj_id":            "ABCDE12345FGHIJ",
  "title":             "D. Johann Gerhard, Professoris zu Jena, Erklärung der Historien des Leidens",
  "dates":             "1662",
  "dc_type":           "Leichenpredigt|Monografie",
  "silver_tier":       "0",
  "era":               "pre-1700",
  "ddb_link":          "https://www.deutsche-digitale-bibliothek.de/item/ABCDE12345FGHIJ",
  "spans": [
    {"start":  0, "end": 38, "label": "PERSON", "text": "D. Johann Gerhard, Professoris zu Jena"},
    {"start": 40, "end": 75, "label": "TITLE",  "text": "Erklärung der Historien des Leidens"}
  ],
  "annotation_status": "manual",
  "annotator":         "your-name",
  "annotation_date":   "2026-XX-XX",
  "notes":             ""
}
```

- `annotation_status`: change to `reviewed` when you have checked and accepted the record; leave `pre-filled` / `partial` / `manual` until then.
- `annotator`: your name or `llm-claude` / `llm-gpt4` for LLM-produced annotations.
- `notes`: record ambiguous cases, boundary questions, or flagged records here.

---

## 9. Verification

After annotating a batch, run:

```bash
python3 scripts/sr08_verify_spans.py
```

This checks `title[start:end] == text` for all spans and prints three sample records per annotation status for human spot-check.

---

## 10. Instructions for LLM annotators

This section specifies the exact task format for LLM-assisted annotation (SR-11 batch).

### 10.1 Input format

You will receive a JSON object:

```json
{
  "obj_id":      "KQCJ7APICPYVGBUZ544FKAICNU73FVKH",
  "title":       "David Beuthers, Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti, Zwey rare Chymische Tractate",
  "era":         "pre-1700",
  "silver_tier": "0",
  "dc_type":     "Monografie",
  "ddb_link":    "https://www.deutsche-digitale-bibliothek.de/item/KQCJ7APICPYVGBUZ544FKAICNU73FVKH"
}
```

### 10.2 Reasoning steps (chain-of-thought)

Before producing the span list, work through these steps explicitly:

1. **Era check** — Is `era == "pre-1700"`? If yes, look for an opening credential sequence (degree + name + role). The ` /` SoR pattern does not apply.
2. **Structure identification** — Which pattern does this title follow? (author-before-title / ISBD SoR ` /` / subtitle only ` :` / no markers)
3. **PERSON boundary** — Where exactly does the credential/name/role sequence end and the work title begin? Name the boundary token.
4. **OTHER_TITLE check** — Is there a genuine subtitle introduced by ` : `, `Das ist:`, `oder`, or similar? Distinguish from life-date colons (followed by a date) and DDB separators (`::`) .
5. **Phase 2 check** — Is there a translation keyword, a ` = ` parallel title, or a musical medium statement?
6. **Verify** — For each span: does `title[start:end] == text`? Do any spans overlap?

### 10.3 Output format

Return a JSON object with only a `spans` array:

```json
{
  "spans": [
    {"start": 0,   "end": 102, "label": "PERSON", "text": "David Beuthers, Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti"},
    {"start": 104, "end": 132, "label": "TITLE",  "text": "Zwey rare Chymische Tractate"}
  ]
}
```

- Return no other fields in the output object.
- If no span of a given type exists, omit it — do not return empty spans.
- If the title cannot be parsed (a fragment, a catalog note, non-German text), return a single TITLE span covering the full string and add a `notes` field with a brief explanation.
- Compute `start` and `end` by finding the exact substring position in `title` — do not estimate.

### 10.4 Self-check before submitting

```
For each span in the output:
  assert title[span["start"]:span["end"]] == span["text"]

For each pair of spans (i, j) where i != j:
  assert not (span_i["start"] < span_j["end"] and span_j["start"] < span_i["end"])

assert any(s["label"] == "TITLE" for s in spans)
```

If any check fails, revise the offsets before returning.
