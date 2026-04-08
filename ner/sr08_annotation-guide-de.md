# GeMeA — NER-Annotationsrichtlinien (SR-08)

Begleitdokument zu [sr08_gold-set-composition.md](sr08_gold-set-composition.md).
Für **menschliche Annotatoren** und **LLM-Annotatoren** (SR-11).

---

## 1. Zusammenfassung

Sie annotieren **benannte Entitätsspannen** in deutschen bibliografischen Titelstrings der Deutschen Digitalen Bibliothek (DDB). Jeder Datensatz enthält einen einzelnen Titelstring. Ihre Aufgabe ist es, diejenigen Teilstrings zu markieren, die den Haupttitel, einen Untertitel oder eine verantwortliche Person darstellen — und die genauen Zeichenpositionen jeder Spanne festzuhalten.

Das Korpus umspannt fünf Jahrhunderte deutscher Druckkultur, von frühneuhochdeutschen Titelblättern des 16. Jahrhunderts bis hin zu Bibliothekskatalogeinträgen des 20. Jahrhunderts. Die Annotationsregeln unterscheiden sich deutlich je nach Epoche: Moderne Titel folgen den ISBD-Interpunktionskonventionen; Titel vor 1700 stellen die Amtsbezeichnungen des Autors *vor* dem Titel, ohne Trennzeichen.

| Abschnitt | Inhalt |
|---|---|
| [§2 Arbeitsablauf](#2-arbeitsablauf) | Dateien, Annotationsstatus, empfohlene Reihenfolge — **hier beginnen** |
| [§3 Label-Definitionen](#3-label-definitionen) | Was TITLE, OTHER_TITLE, PERSON und Phase-2-Labels kennzeichnen |
| [§4 Entscheidungsdiagramm](#4-entscheidungsdiagramm) | Schritt-für-Schritt-Logik zur Label-Auswahl |
| [§5 Beispiele](#5-beispiele-nach-titelstruktur) | 10 Arbeitsbeispiele mit DDB-Links, nach Titelstruktur gruppiert |
| [§6 Was NICHT zu annotieren ist](#6-was-nicht-zu-annotieren-ist) | Häufige False-Positive-Muster und warum sie keine Entitäten sind |
| [§7 Spannengrenzen](#7-spannengrenzen) | Technische Regeln für Zeichenpositionen |
| [§8 Ausgabeformat](#8-ausgabeformat-jsonl) | JSONL-Datensatzschema |
| [§9 Verifizierung](#9-verifizierung) | Skript zur Überprüfung der Offset-Integrität nach jedem Batch |
| [§10 Anweisungen für LLM-Annotatoren](#10-anweisungen-für-llm-annotatoren) | Eingabe-/Ausgabeformat und Selbstprüfung für LLM-gestützte Annotation |

**Schnellstart für menschliche Annotatoren:** Lesen Sie §2, um die Dateien und die empfohlene Reihenfolge zu verstehen; nutzen Sie §3–§5 als Nachschlagewerk während der Annotation. Im Zweifelsfall prüfen Sie zuerst §6, dann §5.

**Schnellstart für LLM-Annotatoren:** Lesen Sie §3, §4 und §6 vollständig; folgen Sie dann dem Aufgabenformat in §10.

---

## 2. Arbeitsablauf

### 2.1 Dateien

Die Annotation erfolgt in **doccano**. Die nachstehenden Dateien sind Eingaben und Referenzen.

| Datei | Inhalt | Aktion |
|---|---|---|
| `data/annotation/sr08_manual_queue.csv` | 212 als `manual` markierte Datensätze, sortiert nach vor-1700 zuerst | Zuerst öffnen — bestimmt, welche Datensätze in welcher Reihenfolge zu annotieren sind |
| `data/annotation/sr08_gold_prefilled.jsonl` | Alle 395 Datensätze; Spannen soweit möglich vorbefüllt | Quell-Import für doccano |
| `data/annotation/export_245867_pretty.json` | doccano-Export | Maßgebliche Annotationsausgabe |
| `data/annotation/sr08_gold_sample.csv` | Ursprüngliche stratifizierte Stichprobe mit Metadaten | Nur zur Referenz |

### 2.2 Annotationsstatus

Jeder Datensatz im JSONL enthält ein Feld `annotation_status`, das angibt, wie viel Arbeit noch erforderlich ist:

| Status | Anzahl | Bedeutung |
|---|---|---|
| `pre-filled` | 47 | Tier-2-Strukturdatensätze (`. -`), nicht vor 1700 — hohe Konfidenz; überprüfen und akzeptieren oder korrigieren |
| `partial` | 136 | Tier-1-Heuristik, nicht vor 1700 — Spannen sind automatisch extrahiert; jede Grenze überprüfen |
| `manual` | 212 | Vor 1700 oder Tier-0 — keine vorbefüllten Spannen; von Grund auf annotieren |

### 2.3 Empfohlene Reihenfolge

Arbeiten Sie die Datensätze in dieser Reihenfolge durch — schwierigere Strata zuerst, damit Fragen zu den Richtlinien früh auftauchen:

1. **Vor-1700 Tier-0** (~130 Datensätze) — das schwierigste Stratum; die Evaluation hängt davon ab; folgen Sie §5.8–§5.10 sorgfältig; nutzen Sie den DDB-Link, um den vollständigen Katalogeintrag aufzurufen, wenn der Titelstring unklar ist
2. **1700–1800 Tier-0** (~37 Datensätze) — Übergangsregister; kann entweder der Vor-1700- oder der modernen Struktur folgen
3. **Modern / 19. Jh. Tier-0** (~45 Datensätze) — keine ISBD-Marker, aber moderne Struktur; meist kurz
4. **Partiell Tier-1** (136 Datensätze) — automatisch extrahierte Spannen überprüfen; Grenzen bei Bedarf korrigieren
5. **Vorbefüllt Tier-2** (47 Datensätze) — nur Stichprobenprüfung; die meisten sind korrekt

Ändern Sie `annotation_status` auf `reviewed`, wenn Sie einen Datensatz überprüft und akzeptiert haben.

---

## 3. Label-Definitionen

### 3.1 Phase 1 — für jeden Datensatz erforderlich

| Label | Was zu markieren ist | Typischer Hinweis |
|---|---|---|
| `TITLE` | Der Hauptwerktitel — der primäre intellektuelle Inhaltsbezeichner. Genau einer pro Datensatz. Wenn kein Untertiteltrennzeichen vorhanden ist, kann die TITLE-Spanne auch das umfassen, was andernfalls ein Untertitel wäre. | Eröffnende substantivische Nominalphrase; vor ` :` oder ` /` in modernen Datensätzen; **nach** der PERSON-Spanne in Vor-1700-Datensätzen |
| `OTHER_TITLE` | Ein Untertitel oder alternativer Titel, der TITLE präzisiert oder ergänzt | Nach ` : `, `Das ist:`, `oder`, `nämlich`, `welches handelt von`, `, enthaltend` |
| `PERSON` | Benannte verantwortliche Person (Autor, Herausgeber) — vollständiger Name **plus** alle Amtsbezeichnungen, Graduierungsabkürzungen und Rollenformulierungen, die mit dem Namen eine Einheit bilden | Nach ` / ` in modernen Datensätzen; **vor** dem Werktitel in Vor-1700-Datensätzen (kein ` /`-Trennzeichen) |

**Ein TITLE pro Datensatz.** Ein Datensatz hat fast immer genau eine TITLE-Spanne. Wenn der String ein Fragment oder eine bloße Beschreibung ist, annotieren Sie die titelähnlichste Phrase als TITLE.

**Warum PERSON und nicht AUTHOR oder CREATOR (Designanmerkung):** Die SoR-Position (` /`) in ISBD enthält nicht nur Autoren, sondern auch Herausgeber (`hrsg. von`), Kompilatoren, Körperschaften und Mitwirkende. `AUTHOR` wäre semantisch falsch für `Jahrbuch / Deutsche Shakespeare-Gesellschaft` oder `Statistische Berichte / Hessisches Statistisches Landesamt` — keines davon ist ein Autor. `CREATOR` ist näher, schließt aber Herausgeber und Körperschaften aus. `PERSON` ist der neutrale Begriff, der markiert, *wo der verantwortliche Agent im String erscheint*, ohne eine Rolle zuzuschreiben. SR-04 hat dies bestätigt: nur 35 % der SoR-Einträge sind echte Autorenangaben; 19 % sind Körperschaften, 5 % Herausgeber, 41 % Nicht-SoR-False-Positives. Die Rollenunterscheidung (`f_resp_person`, `f_resp_org`, `f_resp_editor`) ist ein Phase-2-Anliegen. Dies ist auch konsistent mit historischen NER-Benchmarks (HIPE-2022, GermEval), die aus demselben Grund `PER` statt rollenspezifischer Labels verwenden. Wenn rollenbezogene Labels downstream benötigt werden, können sie als Unterklassifizierungsschicht mithilfe der SR-04-Flags `f_resp_*` hinzugefügt werden, ohne Spannen neu annotieren zu müssen.

### 3.2 Phase 2 — annotieren, wenn vorhanden; wird in Phase 1 nicht ausgewertet

Diese Labels im gleichen Durchgang annotieren, um eine erneute Annotation zu vermeiden, wenn Phase 2 zur Auswertung ansteht:

| Label | Was zu markieren ist | Auslöser |
|---|---|---|
| `TRANSLATOR` | Benannter Übersetzer | Nur wenn ein Übersetzungsstichwort vorhanden ist: `übersetzt`, `Übers.`, `transl.`, `traduit par`, `ins Deutsche übertragen` |
| `PARALLEL_TITLE` | Titel in einer zweiten Sprache wiederholt | Nach ` = ` oder nach ` / ` gefolgt von einem nicht-deutschen Titelstring |
| `MEDIUM` | Besetzungsangabe (nur Musik) | `für Klavier`, `für gemischten Chor und Orchester`, `op. 12` |

---

## 4. Entscheidungsdiagramm

```
Für jeden Titelstring:

1. Ist era == "pre-1700"?
   ├── JA  → Beginnt der String mit einer Amtsbezeichnungssequenz (Grad + Name + Rollenformel)?
   │         ├── JA  → Amtsbezeichnung+Name+Rolle als PERSON markieren; Rest ist TITLE (§5.8–§5.10)
   │         └── NEIN → Gesamten String als TITLE markieren; keine PERSON aus dem String allein erkennbar
   └── NEIN → Enthält der String ' / '?
             ├── JA  → Ist der Text nach ' / ' ein einzelner Buchstabe, ein Datum oder ein Regionsname?
             │         ├── JA  → Nur TITLE (Reihenkürzel oder Datum — keine Person)
             │         └── NEIN → Text vor ' / ' → TITLE (und OTHER_TITLE, falls ' : ' vorhanden)
             │                    Text nach  ' / ' → PERSON (oder PARALLEL_TITLE, falls nicht-deutsch)
             └── NEIN → Enthält der String ' : '?
                       ├── JA  → Folgt ' : ' unmittelbar einem Datumsbereich (jjjj–jjjj oder d. Monat jjjj)?
                       │         ├── JA  → Nur TITLE (Lebensdaten-Doppelpunkt — kein Untertiteltrennzeichen)
                       │         └── NEIN → Text vor ' : ' → TITLE
                       │                    Text nach  ' : ' → OTHER_TITLE
                       └── NEIN → Gesamter String → TITLE
```

---

## 5. Beispiele nach Titelstruktur

Jedes Beispiel zeigt den Eingabestring, die korrekte Annotation und einen Link zum DDB-Quelldatensatz.
Die Offsets gelten für die exakt gezeigten Strings — prüfen Sie mit `title[start:end] == text`.

---

### 5.1 Nur Untertitel — ` :` vorhanden, kein ` /`

**Eingabe**
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
> `gegr. 1791` ist ein **Gründungsjahrvermerk** — nicht annotieren. Zahlen nach `gegr.`, `gestiftet`, `gegründet` sind niemals YEAR-Entitäten.

---

### 5.2 Nur SoR — ` /` vorhanden, kein ` :`; Körperschaft als verantwortlicher Agent

**Eingabe**
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
> `; 3` ist eine **Bandnummer** — keine zweite PERSON. Die PERSON-Spanne beim Semikolon beenden.
> Eine Körperschaft (Gesellschaft, Landesamt, Institut, Universität) in SoR-Position wird als `PERSON` annotiert — sie ist der verantwortliche Agent.

---

### 5.3 SoR mit thematischer Unterreihe — PERSON bei Punkt oder Semikolon beenden

**Eingabe**
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
> `. B …` und `; Ergebnisse nach Verwaltungsbezirken …` sind Unterreihen- und Themabezeichner — keine weiteren PERSON-Spannen. Die PERSON-Spanne endet beim ersten `.` oder `;`, das einen Themaqualifikator einleitet.

---

### 5.4 Reihenbuchstaben-Suffix — ` /` gefolgt von einem einzelnen Buchstaben; NICHT als PERSON annotieren

**Eingabe**
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
> `/ K` ist ein **Reihenbuchstaben-Suffix** — niemals eine PERSON. Ein einzelner Buchstabe (oder zweistelliger Code) nach ` / ` ist immer ein Reihenbezeichner.
> Das führende `1988:` ist ein vom Katalogisierer hinzugefügter Datumsbezeichner — nicht Teil des TITLE. Die TITLE-Spanne beginnt nach dem Doppelpunkt und dem Leerzeichen.

---

### 5.5 Paralleltitel — ` /` gefolgt von einem nicht-deutschen Titel; DDB-`::` Trennzeichen

**Eingabe**
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
> `Transnational Criminal Law` nach ` / ` ist der Titel in einer zweiten Sprache → `PARALLEL_TITLE` (Phase 2).
> `::` ist ein **DDB-Katalogfeld-Trennzeichen**, kein ISBD-Bereichstrennzeichen. `gesammelte Beiträge` nicht als OTHER_TITLE behandeln.

---

### 5.6 Lebensdaten nach Doppelpunkt — kein Untertitel

**Eingabe**
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
> `:7. Januar 1787 - 28. März 1860` sind **Lebensdaten** — kein Untertitel. Wenn ` :` auf einen Personennamen folgt und unmittelbar von einem Datum oder Datumsbereich gefolgt wird, ist es ein Lebensdaten-Trennzeichen, kein ISBD-Untertiteltrennzeichen.
> `[Katalog]` in eckigen Klammern ist ein Katalogisierervermerk — kein OTHER_TITLE.

---

### 5.7 Lebensdaten in Klammern — in TITLE einschließen; `:` danach leitet OTHER_TITLE ein

**Eingabe**
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
> Lebensdaten `(1734 - 1805)` liegen innerhalb der TITLE-Spanne — sie identifizieren die dargestellte Person und sind Teil der Titelphrase.
> Hier folgt ` :` einem vollständig beschriebenen Gegenstand (nicht einem alleinstehenden Personennamen), sodass `Kupferstich` ein echter OTHER_TITLE ist, der das Format angibt.
> `Kupferstich` ist eine Drucktechnikangabe, keine Musikbesetzung — als OTHER_TITLE annotieren, nicht als MEDIUM. MEDIUM ist ausschließlich für musikalische Besetzungsangaben reserviert.

---

### 5.8 Vor 1700 — Autor vor dem Titel; alchemistischer Traktat

**Eingabe**
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
> Die vollständige Amtsbezeichnungsphrase `Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti` ist Teil der PERSON-Spanne. Sie identifiziert und qualifiziert die genannte Person.
> TITLE beginnt bei der ersten substantivischen Nominalphrase, die das Werk benennt (`Zwey rare Chymische Tractate`). Das Trennzeichen `, ` (Komma-Leerzeichen) zwischen PERSON und TITLE gehört zu keiner der beiden Spannen.
> Falls ein ` :` folgt, jeden Untertitelinhalt danach als OTHER_TITLE annotieren.
>
> **Warum Amtsbezeichnung und Name zu einer PERSON-Spanne zusammengefasst werden (Designanmerkung):** Ein Label `PERSON_DESIGNATION`, das den Klarnamen (`David Beuthers`) von der Amtsbezeichnungsphrase trennt, wurde erwogen und auf Phase 2 verschoben. Drei Gründe: (1) Die vorangestellten Graduierungsabkürzungen (`D.`, `M.`, `Lic.`) sind nach deutschem akademischem Konvent mit dem Namen verschmolzen, und die Grenze ist genuinen ambig; (2) Standard-BIO-Sequenz-Labeling verarbeitet zwei angrenzende Spannen an einer unsicheren Grenze schlechter als eine zusammengefasste Spanne; (3) Für die GND-Verlinkung kann die Namensextraktion aus einer zusammengefassten PERSON-Spanne in der Nachverarbeitung durch Abschneiden bekannter Gradpräfixe und Kürzen am ersten Rollensubstantiv (`Professoris`, `Pfarrers`, `Pastoris`, `Meisters`) erfolgen. Bei der Planung der Phase-2-Annotation sollte `PERSON_DESIGNATION` sowohl vorangestellte Gradbezeichnungen als auch nachgestellte Rollen-/Ortsformulierungen abdecken, mit dem bloßen Vor- und Zunamen als PERSON-Kern.

---

### 5.9 Vor 1700 — Leichenpredigt; benannte Verstorbene und Ehemann im Titel eingebettet

**Eingabe**
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
> `Magdalenen Heidewig Stissers` ist die Verstorbene; `Johan Julii Herings` ist ihr Ehemann. Beide sind namentlich in der Titelbeschreibung genannt — **sie sind nicht der Autor**. Nicht als PERSON annotieren.
> In einem Leichenpredigt-Titel nur PERSON annotieren, wenn der Prediger (Autor) ausdrücklich durch `verfasset von`, `gehalten von` oder ` /` identifiziert ist.
> Das `/` in `Stissers/` ist ein frühneuzeitlicher orthografischer Schrägstrich innerhalb des Titelstrings, kein ISBD-SoR-Trennzeichen.

---

### 5.10 Vor 1700 — Autor durch `Von` mitten im String identifiziert

**Eingabe**
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
> `Von` ist ein Zuschreibungsstichwort — die danach genannte Person ist die PERSON, auch wenn `Von` mitten im String steht. Die PERSON-Spanne beginnt nach `Von `.
> Die Amtsbezeichnungsphrase (`D. Königl. Preuss. Consistorialrathe und Professor`) in die PERSON-Spanne einschließen.
> Das ` …` am Ende ist ein Kürzungsmarker — gehört zu keiner Spanne.

---

## 6. Was NICHT zu annotieren ist

Diese Muster treten häufig auf und dürfen kein Label erhalten:

| Muster | Beispiel | Grund |
|---|---|---|
| Gründungsjahr | `gegr. 1791`, `gestiftet 1840` | Kein Erscheinungsjahr; keine YEAR-Entität |
| Lebensdaten in Klammern | `(1734 - 1805)` | In die umschließende TITLE-Spanne einschließen, wenn sie den Gegenstand identifizieren |
| Lebensdaten nach Doppelpunkt | `:7. Januar 1787 - 28. März 1860` | Lebensdaten-Trennzeichen, kein Untertiteltrennzeichen |
| Reihenbuchstaben-Suffix | `/ K`, `/ M`, `/ A1` | Einzelner Buchstabe nach ` / ` ist immer ein Reihenbezeichner, nie eine PERSON |
| Bandnummer nach `;` | `; 3`, `; Bd. 2` | Unterreihen-Zählung, keine zweite PERSON |
| Zeitungsausgabenbezeichnung | `Ausgabe vom Dienstag, den 18. Mai 1937` | Tagesausgabedatum, keine Ausgabenangabe |
| DDB-Katalogtrennzeichen | `::` | Kein ISBD-Bereichstrennzeichen; was folgt, ist kein OTHER_TITLE |
| Katalogisierervermerk | `[Katalog]`, `[Notizen]`, `[Entwurf]` | Vom Katalogisierer hinzugefügte Ergänzungen, nicht Teil des Titels |
| Generischer Widmungsempfänger | `Herrn N.N. gewidmet` | Nicht der Autor; PERSON nicht annotieren |
| Eingebettete lateinische Phrasen | `Anno MDXLVI`, `In nomine Dei` | Teil der umschließenden TITLE- oder PERSON-Spanne |
| `durch` / `von` ohne Übersetzungsstichwort | `durch Johann Schmidt` | PERSON annotieren (Autor/Herausgeber), nicht TRANSLATOR |
| Verstorbene in Leichenpredigten | `Bey der Begräbnis … Maria Dorothea Müllers` | Gegenstand der Predigt, nicht der Autor |

---

## 7. Spannengrenzen

> Für den vollständigen Satz der TITLE-Grenzentscheidungen (führende Artikel, Klammerausdrücke, Kürzungsmarker, Vor-1700-Trennzeichenregeln usw.) siehe [sr08_title-boundary-curation.md](sr08_title-boundary-curation.md). Die nachstehenden Regeln formulieren die allgemeinen Grundsätze; jene Notiz ist die maßgebliche Referenz für Einzelfallentscheidungen.

1. **Offsets sind Zeichenpositionen** im rohen `title`-String, 0-indiziert, Ende-exklusiv. `title[start:end]` muss dem Feld `text` exakt entsprechen — dies wird von `sr08_verify_spans.py` geprüft.
2. **Führende und abschließende Leerzeichen trimmen.** `start` zeigt auf das erste Nicht-Leerzeichen der Entität; `end` zeigt eine Position nach dem letzten Nicht-Leerzeichen.
3. **Keine überlappenden Spannen.** Wenn Amtsbezeichnung und Name jeweils separat annotiert werden könnten, zu einer PERSON-Spanne zusammenführen.
4. **Keine verschachtelten Spannen.** Falls eine PERSON-Spanne ein eingebettetes Titelfragment enthalten würde, die PERSON-Spanne vor diesem Fragment beenden.
5. **Nur zusammenhängende Teilstrings.** Keine Lückspannen — `start` bis `end` muss einen einzelnen ununterbrochenen Teilstring abdecken.
6. **Die vollständige Benennungseinheit in PERSON einschließen.** Graduierungsabkürzung + Vorname + Nachname + Rollenformel + Ortsformel bilden eine Spanne: `D. Johann Gerhard, Professoris zu Jena` → eine PERSON-Spanne, nicht drei.
7. **Trennzeichen zwischen Spannen gehören zu keiner der beiden Spannen.** ` / `, ` : `, `, ` zwischen TITLE und PERSON oder OTHER_TITLE gehört zu keiner Seite.

---

## 8. Ausgabeformat (JSONL)

Jeder annotierte Datensatz in `data/annotation/sr08_gold_prefilled.jsonl`:

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
  "annotator":         "Ihr-Name",
  "annotation_date":   "2026-XX-XX",
  "notes":             ""
}
```

- `annotation_status`: auf `reviewed` setzen, wenn Sie den Datensatz geprüft und akzeptiert haben; `pre-filled` / `partial` / `manual` bis dahin beibehalten.
- `annotator`: Ihr Name oder `llm-claude` / `llm-gpt4` für LLM-erzeugte Annotationen.
- `notes`: Ambige Fälle, Grenzfragen oder markierte Datensätze hier vermerken.

---

## 9. Verifizierung

Nach der Annotation eines Batches ausführen:

```bash
python3 scripts/sr08_verify_spans.py
```

Dies prüft `title[start:end] == text` für alle Spannen und gibt drei Musterdatensätze pro Annotationsstatus zur menschlichen Stichprobenprüfung aus.

---

## 10. Anweisungen für LLM-Annotatoren

Dieser Abschnitt legt das genaue Aufgabenformat für LLM-gestützte Annotation fest (SR-11-Batch).

### 10.1 Eingabeformat

Sie erhalten ein JSON-Objekt:

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

### 10.2 Denkschritte (Chain-of-Thought)

Bevor Sie die Spannenliste erstellen, arbeiten Sie diese Schritte explizit durch:

1. **Epochenprüfung** — Ist `era == "pre-1700"`? Falls ja, nach einer einleitenden Amtsbezeichnungssequenz (Grad + Name + Rolle) suchen. Das ` /`-SoR-Muster gilt nicht.
2. **Strukturidentifikation** — Welchem Muster folgt dieser Titel? (Autor-vor-Titel / ISBD-SoR ` /` / nur Untertitel ` :` / keine Marker)
3. **PERSON-Grenze** — Wo genau endet die Amtsbezeichnungs-/Namen-/Rollensequenz und beginnt der Werktitel? Das Grenztoken benennen.
4. **OTHER_TITLE-Prüfung** — Gibt es einen echten Untertitel, eingeleitet durch ` : `, `Das ist:`, `oder` oder Ähnliches? Von Lebensdaten-Doppelpunkten (gefolgt von einem Datum) und DDB-Trennzeichen (`::`) abgrenzen.
5. **Phase-2-Prüfung** — Gibt es ein Übersetzungsstichwort, einen ` = `-Paralleltitel oder eine Musikbesetzungsangabe?
6. **Verifizierung** — Für jede Spanne: gilt `title[start:end] == text`? Überlappen sich Spannen?

### 10.3 Ausgabeformat

Ein JSON-Objekt mit ausschließlich einem `spans`-Array zurückgeben:

```json
{
  "spans": [
    {"start": 0,   "end": 102, "label": "PERSON", "text": "David Beuthers, Gewesenen Churfürstl. Sächsischen Probation-Meisters zu Dreßden, und Philosophi Adepti"},
    {"start": 104, "end": 132, "label": "TITLE",  "text": "Zwey rare Chymische Tractate"}
  ]
}
```

- Keine weiteren Felder im Ausgabeobjekt zurückgeben.
- Falls kein Span eines bestimmten Typs existiert, weglassen — keine leeren Spannen zurückgeben.
- Falls der Titel nicht geparst werden kann (ein Fragment, ein Katalogvermerk, nicht-deutschsprachiger Text), eine einzelne TITLE-Spanne zurückgeben, die den gesamten String abdeckt, und ein `notes`-Feld mit einer kurzen Erläuterung hinzufügen.
- `start` und `end` durch Suche nach der exakten Teilstringposition in `title` berechnen — nicht schätzen.

### 10.4 Selbstprüfung vor der Abgabe

```
Für jede Spanne in der Ausgabe:
  assert title[span["start"]:span["end"]] == span["text"]

Für jedes Spannenpaar (i, j) mit i != j:
  assert not (span_i["start"] < span_j["end"] and span_j["start"] < span_i["end"])

assert any(s["label"] == "TITLE" for s in spans)
```

Falls eine Prüfung fehlschlägt, Offsets vor der Abgabe korrigieren.
