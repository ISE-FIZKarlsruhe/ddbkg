#!/usr/bin/env python3
"""
match_objecttypes.py
====================
Maps DDB (Deutsche Digitale Bibliothek) document objecttype values to classes
from two bibliographic ontologies: FaBiO and DoCO.

Input
-----
- ddb-search-goethe-all.json : Solr search response (query="goethe", rows=1000)
  Only documents with sector_fct == "sec_02" (library/bibliographic sector) are
  processed.
- fabio.owl : FRBR-aligned Bibliographic Ontology (FaBiO, http://purl.org/spar/fabio/)
  Direct subclasses of fabio:Work, fabio:Expression, fabio:Manifestation, fabio:Item
  are used as matching targets.
- doco.owl : Document Components Ontology (DoCO, http://purl.org/spar/doco/)
  All named classes are used as matching targets.

Output
------
ddb-type2fabio.json with three top-level keys:
  summary       — aggregate statistics and list of unmatched types
  type_to_fabio — per-objecttype matching result (ontology, class, method, confidence)
  details       — per-objecttype list of doc IDs that carry that type

Matching pipeline (4 tiers, applied in order; first match wins)
---------------------------------------------------------------
1. strict
   Case-insensitive exact match of the original objecttype string against all
   ontology class names, CamelCase-split variants, and rdfs:label values.
   Confidence: 1.0

2. strict_translated
   The objecttype is translated from German to English via Google Translate
   (deep-translator, free, no API key). The translated string is then matched
   exactly as in tier 1.
   Confidence: 1.0

3. levenshtein
   Levenshtein edit distance ≤ 2 between the normalised translated string and
   all lookup keys. The closest match is taken; ties broken by first occurrence.
   Confidence: 1 - (distance / max_length)

4. embeddings
   Sentence embeddings (all-MiniLM-L6-v2 via sentence-transformers) are computed
   for the translated objecttype and for each ontology class (name + labels).
   The best cosine similarity above EMBEDDING_THRESHOLD (0.55) is taken.
   Confidence: cosine similarity score

When fabio and doco define a class with the same name (e.g., Index, Chapter,
Table), the fabio class takes priority in the lookup; the doco variant is
accessible under a "doco_<Name>" key.

Dependencies
------------
    pip install deep-translator rapidfuzz sentence-transformers scikit-learn numpy

Usage
-----
    python match_objecttypes.py
"""

import json
import re
from collections import defaultdict
import xml.etree.ElementTree as ET

from deep_translator import GoogleTranslator
from rapidfuzz.distance import Levenshtein
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# ── Configuration ────────────────────────────────────────────────────
from pathlib import Path
PROJECT        = Path(__file__).resolve().parent.parent
JSON_PATH      = PROJECT / "data" / "ddb-search-faust-goethe-all.json"
FABIO_OWL_PATH = PROJECT / "data" / "schemas" / "fabio.owl"
DOCO_OWL_PATH  = PROJECT / "data" / "schemas" / "doco.owl"
OUT_PATH       = PROJECT / "output" / "ddb-type2fabio.json"

FABIO_NS = "http://purl.org/spar/fabio/"
DOCO_NS = "http://purl.org/spar/doco/"
FRBR_PARENTS = {"Work", "Expression", "Manifestation", "Item"}
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
EMBEDDING_THRESHOLD = 0.55
LEVENSHTEIN_MIN_CONF = 0.88  # minimum confidence for Levenshtein matches


# ── Data loading ─────────────────────────────────────────────────────

def load_objecttypes(path):
    """Return (docs, doc_otypes, all_types) for sec_02 docs that have objecttype."""
    with open(path) as f:
        data = json.load(f)
    docs = data["response"]["docs"]
    doc_otypes = {}
    for doc in docs:
        if doc.get("sector_fct") == "sec_02" and "objecttype" in doc:
            doc_otypes[doc["id"]] = doc["objecttype"]
    all_types = set()
    for otypes in doc_otypes.values():
        all_types.update(otypes)
    return docs, doc_otypes, sorted(all_types)


# ── Ontology parsing ─────────────────────────────────────────────────

def _owl_ns():
    return {
        "owl": "http://www.w3.org/2002/07/owl#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }


def parse_fabio_subclasses(path):
    """Return dict of class_name -> {parent, uri, labels, ontology} for direct
    subclasses of the four FRBR top classes (Work/Expression/Manifestation/Item).
    The four top classes themselves are included as self-referential entries.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    ns = _owl_ns()
    subclasses = {}
    for cls in root.findall(".//owl:Class", ns):
        about = cls.get(f"{{{ns['rdf']}}}about", "")
        if not about.startswith(FABIO_NS):
            continue
        class_name = about[len(FABIO_NS):]
        for sub in cls.findall("rdfs:subClassOf", ns):
            res = sub.get(f"{{{ns['rdf']}}}resource", "")
            if res.startswith(FABIO_NS):
                parent = res[len(FABIO_NS):]
                if parent in FRBR_PARENTS:
                    labels = [lbl.text.strip()
                              for lbl in cls.findall("rdfs:label", ns)
                              if lbl.text]
                    subclasses[class_name] = {
                        "parent": parent,
                        "uri": about,
                        "labels": labels,
                        "ontology": "fabio",
                    }
    for p in FRBR_PARENTS:
        subclasses[p] = {"parent": p, "uri": FABIO_NS + p,
                         "labels": [p.lower()], "ontology": "fabio"}
    return subclasses


def parse_doco_classes(path):
    """Return dict of class_name -> {parent, uri, labels, ontology} for all
    named DoCO classes. parent is the nearest doco superclass if present.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    ns = _owl_ns()
    classes = {}
    for cls in root.findall(".//owl:Class", ns):
        about = cls.get(f"{{{ns['rdf']}}}about", "")
        if not about.startswith(DOCO_NS):
            continue
        class_name = about[len(DOCO_NS):]
        if not class_name:
            continue
        labels = [lbl.text.strip()
                  for lbl in cls.findall("rdfs:label", ns)
                  if lbl.text]
        parent = None
        for sub in cls.findall("rdfs:subClassOf", ns):
            res = sub.get(f"{{{ns['rdf']}}}resource", "")
            if res.startswith(DOCO_NS):
                parent = res[len(DOCO_NS):]
        classes[class_name] = {
            "parent": parent,
            "uri": about,
            "labels": labels,
            "ontology": "doco",
        }
    return classes


# ── Lookup construction ──────────────────────────────────────────────

def normalize(s):
    """Strip spaces/hyphens/underscores and lowercase."""
    return re.sub(r"[\s\-_]", "", s).lower()


def camel_to_words(name):
    """'JournalArticle' -> 'journal article'"""
    return re.sub(r"([A-Z])", r" \1", name).strip().lower()


def build_lookup(classes_dict):
    """Build a normalized-string -> class-info lookup over all ontology classes.

    Keys are derived from: the class name, its CamelCase-split form, and any
    rdfs:label values. When fabio and doco share a class name (e.g., Index),
    fabio takes priority for the bare normalized key.
    """
    lookup = {}
    for name, info in classes_dict.items():
        # Internal dedup keys like "doco_Chapter" -> display as "Chapter"
        clean_name = name.split("_", 1)[1] if name.startswith("doco_") else name
        entry = {"class": clean_name, **info}
        for key in [normalize(clean_name), normalize(camel_to_words(clean_name))]:
            if key not in lookup or info.get("ontology") == "fabio":
                lookup[key] = entry
        for lbl in info.get("labels", []):
            key = normalize(lbl)
            if key not in lookup or info.get("ontology") == "fabio":
                lookup[key] = entry
    return lookup


def merge_ontologies(fabio_classes, doco_classes):
    """Merge fabio and doco into one dict; prefix colliding doco keys."""
    merged = {}
    merged.update(fabio_classes)
    for name, info in doco_classes.items():
        if name in merged:
            merged[f"doco_{name}"] = info  # doco variant accessible separately
        else:
            merged[name] = info
    return merged


# ── Matching tiers ────────────────────────────────────────────────────

def match_strict(objecttypes, lookup):
    """Tier 1: exact case-insensitive match on original term."""
    matched, remaining = {}, []
    for otype in objecttypes:
        info = lookup.get(normalize(otype))
        if info:
            matched[otype] = _entry(info, otype, None, "strict", 1.0)
        else:
            remaining.append(otype)
    return matched, remaining


def translate_terms(terms, src="de", dest="en", batch_size=100):
    """Translate a list of terms via Google Translate (free, no key required)."""
    translator = GoogleTranslator(source=src, target=dest)
    translations = {}
    batches = [terms[i:i + batch_size] for i in range(0, len(terms), batch_size)]
    for i, batch in enumerate(batches):
        print(f"  Translating batch {i+1}/{len(batches)} ({len(batch)} terms)...")
        try:
            result = translator.translate_batch(batch)
            for orig, trans in zip(batch, result):
                translations[orig] = trans if trans else orig
        except Exception as e:
            print(f"  Warning: batch failed ({e}), falling back to per-term")
            for orig in batch:
                try:
                    translations[orig] = translator.translate(orig)
                except Exception:
                    translations[orig] = orig
    return translations


def match_translated_strict(remaining, translations, lookup):
    """Tier 2: exact match on Google-translated term."""
    matched, still_remaining = {}, []
    for otype in remaining:
        translated = translations.get(otype, otype)
        info = lookup.get(normalize(translated))
        if info:
            matched[otype] = _entry(info, otype, translated, "strict_translated", 1.0)
        else:
            still_remaining.append(otype)
    return matched, still_remaining


def match_levenshtein(remaining, translations, lookup, max_dist=2,
                      min_conf=LEVENSHTEIN_MIN_CONF):
    """Tier 3: nearest match within Levenshtein distance ≤ max_dist AND
    confidence ≥ min_conf (default 0.88). Candidates that pass the distance
    filter but fall below the confidence threshold are passed to tier 4.
    """
    matched, still_remaining = {}, []
    targets = list(lookup.keys())
    for otype in remaining:
        translated = translations.get(otype, otype)
        norm = normalize(translated)
        best_dist, best_key = max_dist + 1, None
        for target in targets:
            if abs(len(norm) - len(target)) > max_dist:
                continue
            dist = Levenshtein.distance(norm, target, score_cutoff=max_dist)
            if dist <= max_dist and dist < best_dist:
                best_dist, best_key = dist, target
        if best_key is not None:
            info = lookup[best_key]
            max_len = max(len(norm), len(best_key))
            conf = round(1.0 - best_dist / max_len, 3) if max_len else 0.0
            if conf >= min_conf:
                entry = _entry(info, otype, translated, "levenshtein", conf)
                entry["levenshtein_distance"] = best_dist
                matched[otype] = entry
            else:
                still_remaining.append(otype)
        else:
            still_remaining.append(otype)
    return matched, still_remaining


def match_embeddings(remaining, translations, onto_classes,
                     threshold=EMBEDDING_THRESHOLD):
    """Tier 4: sentence-embedding cosine similarity ≥ threshold."""
    if not remaining:
        return {}, []

    print(f"  Loading embedding model '{EMBEDDING_MODEL}'...")
    model = SentenceTransformer(EMBEDDING_MODEL)

    onto_names = list(onto_classes.keys())
    onto_descs = []
    for name in onto_names:
        info = onto_classes[name]
        desc = camel_to_words(name)
        if info.get("labels"):
            desc += " " + " ".join(info["labels"])
        onto_descs.append(desc)

    print(f"  Encoding {len(onto_descs)} ontology classes...")
    onto_emb = model.encode(onto_descs, show_progress_bar=False)

    query_texts = [translations.get(t, t) for t in remaining]
    print(f"  Encoding {len(query_texts)} objecttype terms...")
    query_emb = model.encode(query_texts, show_progress_bar=False)

    sims = cosine_similarity(query_emb, onto_emb)

    matched, still_remaining = {}, []
    for i, otype in enumerate(remaining):
        best_idx = int(np.argmax(sims[i]))
        best_score = float(sims[i][best_idx])
        if best_score >= threshold:
            name = onto_names[best_idx]
            info = onto_classes[name]
            # Use clean display name for colliding doco entries
            clean = name.split("_", 1)[1] if name.startswith("doco_") else name
            entry = _entry(
                {**info, "class": clean},
                otype,
                translations.get(otype, otype),
                "embeddings",
                round(best_score, 3),
            )
            matched[otype] = entry
        else:
            still_remaining.append(otype)
    return matched, still_remaining


def _entry(info, original_term, translated_term, method, confidence):
    """Build a standard match-result dict."""
    return {
        "ontology": info.get("ontology", "fabio"),
        "ontology_class": info["class"],
        "ontology_parent": info.get("parent"),
        "ontology_uri": info.get("uri"),
        "original_term": original_term,
        "translated_term": translated_term,
        "match_method": method,
        "confidence": confidence,
    }


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    docs, doc_otypes, all_types = load_objecttypes(JSON_PATH)
    fabio_classes = parse_fabio_subclasses(FABIO_OWL_PATH)
    doco_classes = parse_doco_classes(DOCO_OWL_PATH)
    all_onto_classes = merge_ontologies(fabio_classes, doco_classes)
    lookup = build_lookup(all_onto_classes)

    print(f"  {len(docs)} docs | {len(doc_otypes)} sec_02 with objecttype "
          f"| {len(all_types)} unique types")
    print(f"  {len(fabio_classes)} fabio + {len(doco_classes)} doco = "
          f"{len(all_onto_classes)} ontology classes")

    print("\n[Tier 1] Strict matching...")
    matched_strict, remaining = match_strict(all_types, lookup)
    print(f"  Matched: {len(matched_strict)}, Remaining: {len(remaining)}")

    print("\n[Translation] Translating remaining terms DE→EN...")
    translations = translate_terms(remaining)

    print("\n[Tier 2] Strict matching on translated terms...")
    matched_translated, remaining = match_translated_strict(remaining, translations, lookup)
    print(f"  Matched: {len(matched_translated)}, Remaining: {len(remaining)}")

    print("\n[Tier 3] Levenshtein matching (max distance=2)...")
    matched_lev, remaining = match_levenshtein(remaining, translations, lookup, max_dist=2)
    print(f"  Matched: {len(matched_lev)}, Remaining: {len(remaining)}")

    print("\n[Tier 4] Embedding similarity matching...")
    matched_emb, remaining = match_embeddings(
        remaining, translations, all_onto_classes, threshold=EMBEDDING_THRESHOLD)
    print(f"  Matched: {len(matched_emb)}, Remaining: {len(remaining)}")

    all_matches = {**matched_strict, **matched_translated, **matched_lev, **matched_emb}
    total_matched = len(all_matches)
    total_unmatched = len(remaining)

    print(f"\n{'='*60}")
    print(f"TOTAL: {total_matched} matched, {total_unmatched} unmatched / {len(all_types)}")
    for label, group in [("strict", matched_strict),
                         ("strict_translated", matched_translated),
                         ("levenshtein", matched_lev),
                         ("embeddings", matched_emb)]:
        print(f"  {label:<20} {len(group)}")
    print(f"  {'unmatched':<20} {total_unmatched}")

    # Build objecttype -> doc IDs index
    otype_to_ids = defaultdict(list)
    for doc_id, otypes in doc_otypes.items():
        for otype in otypes:
            otype_to_ids[otype].append(doc_id)

    # Build type_to_fabio (match info, no doc IDs)
    type_to_fabio = {}
    for otype in sorted(set(list(all_matches.keys()) + remaining)):
        if otype in all_matches:
            type_to_fabio[otype] = {**all_matches[otype]}
        else:
            type_to_fabio[otype] = {
                "ontology": None,
                "ontology_class": None,
                "ontology_parent": None,
                "ontology_uri": None,
                "original_term": otype,
                "translated_term": translations.get(otype, otype),
                "match_method": "unmatched",
                "confidence": 0.0,
            }

    # details: objecttype -> list of doc IDs
    details = {otype: otype_to_ids.get(otype, [])
               for otype in sorted(otype_to_ids.keys())}

    output = {
        "summary": {
            "total_docs": len(docs),
            "docs_with_objecttype": len(doc_otypes),
            "unique_objecttypes": len(all_types),
            "total_matched": total_matched,
            "total_unmatched": total_unmatched,
            "by_method": {
                "strict": len(matched_strict),
                "strict_translated": len(matched_translated),
                "levenshtein": len(matched_lev),
                "embeddings": len(matched_emb),
                "unmatched": total_unmatched,
            },
            "unmatched_types": sorted(remaining),
        },
        "type_to_fabio": type_to_fabio,
        "details": details,
    }

    with open(OUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {OUT_PATH}")


if __name__ == "__main__":
    main()
