# Data scripts

This directory contains two families of scripts. The first builds the trial-level CSVs in
`data/` from the raw JATOS output. The second (further down, under *Layers
metadata records*) turns those CSVs and the sentence inventory into
`pub.layers.*` ATProto records for publication. Only the scripts are tracked.
The records they generate are not.

## Building the trial-level CSVs from raw JATOS output

Each script builds one CSV in `data/` from the raw JATOS result files, joining
responses to the sentence inventory and deployed stimulus lists. This records
the path from a participant session to a row in `data-cloze.csv`.

| script | writes | reads |
|---|---|---|
| `make_cloze_data.py` | `data/data-cloze.csv` | raw JATOS + `manner-result-sentences.csv` + `materials/src/cloze-items.json` |
| `make_proportion_data.py` | `data/data-proportion.csv` | raw JATOS + `manner-result-sentences.csv` + `materials/src/proportion-items.json` |
| `make_similarity_data.py` | `data/data-similarity.csv` | raw JATOS + `manner-result-sentences.csv` + `materials/src/similarity-items.json` |
| `anonymize.py` | n/a | the participant map (see below) |

Each script reads its raw JATOS dumps, recovers the condition and list a
participant saw by matching against the deployed stimulus lists, joins the
responses to the sentence inventory, and pseudonymizes the participant ids
before writing its CSV. Paths resolve from the repository root, so a script
can be run from anywhere.

## Experiment 1a conditions

Experiment 1a ran five conditions, and `materials/src/cloze-items.json` holds the
deployed lists of all five. The paper reports the three episodic ones
(`contentful_episodic`, `bleached_episodic`, `templatic_episodic`), and
`make_cloze_data.py` writes only those: the tuple `REPORTED_CONDITIONS` at the
top of the script lists them, the script recovers every session's condition and
list from the five conditions' lists, and it leaves out sessions in a condition
not in the tuple. The two generic conditions (`contentful_generic`,
`bleached_generic`) were run but are not reported or released here.

To add the generic data, add `"contentful_generic"` and `"bleached_generic"` to
`REPORTED_CONDITIONS` and rerun `make_cloze_data.py`. Nothing else in the build
changes: the inventory already has the generic sentences and their lists, the
script strips the generic items' two blanks, leaves `numeral` empty (generic
trials did not ask for one), and checks that every generic sentence has 10
(contentful) or 20 (bleached) responses. The episodic rows of `data-cloze.csv`
come out unchanged. On a generic row, `clause_type` is `generic`, and the noun
columns, including `*_plural` and `*_mass`, are those of the episodic sentence
of the same inventory row; the generic sentence uses the same head nouns as
bare plurals or mass nouns.

Downstream of `data-cloze.csv`, the analyses (`analysis/reproduce.ipynb`) and
`materials/scripts/make_proportion_items.ipynb` keep only
`clause_type == "episodic"`, so generic rows leave their results unchanged.
The Layers metadata do not yet cover generic rows:
`metadata/scripts/generate_metadata.py` builds sentence records and Experiment
1a condition records from the three episodic conditions only (`SENTENCES`,
`CLOZE_COND`), and `check_metadata.py` compares the records against the
episodic sentences of the inventory. Both need generic sentences and conditions
added before they will run on a `data-cloze.csv` that includes generic rows.

## Raw dumps

The raw JATOS files carry participants' Prolific IDs and are not published.
The scripts thus document how `data/` was produced. Rebuilding requires a
local copy. Point `RAW_JATOS_DIR` at that copy:

```bash
export RAW_JATOS_DIR=~/path/to/jatos-dumps    # holds jatos_results_data_*/
export PARTICIPANT_ID_MAP=~/private/participant-id-map.json
python data/scripts/make_proportion_data.py
```

Each script globs the date range matching its own collection window: July 2024
for cloze, `20240803*` for proportion, and `20240807*` for similarity. Thus,
all three can point at a single directory of dumps, with each selecting its
own files.

## Participant anonymization

Every participant identifier in `data/` is a UUID with no relationship to the
underlying Prolific ID. Prolific IDs are stable across studies, so
publishing one lets anyone holding data from a different study link a
participant between the two. The scripts route every `PROLIFIC_PID` through
`anonymize.ParticipantAnonymizer.pseudonym()`, and a raw ID never reaches a
CSV.

Pseudonyms have to be stable (the same person needs the same UUID on every
rerun, and across all three experiments), so we keep the mapping in a JSON
file whose location is set with `PARTICIPANT_ID_MAP`. That file is the one
artifact that can re-identify a participant, which is why `.gitignore`
excludes it.

We use one map across all three experiments. A handful of people took part
in more than one study, and one UUID preserves that cross-study identity.

## Who can run these scripts

The raw JATOS results contain participants' Prolific IDs, so they are not
distributed, and these three scripts can be run only by the authors. They
are included to document how each file in `data/` was derived from the raw
results. Where a list collected more sessions than its quota, the first
sessions read were kept, so the exact set of sessions in a list depends on the
order in which the raw files are read. Everything downstream of `data/` (the analyses, figures,
reported numbers, and the Layers metadata in `metadata/`) can be regenerated
by anyone from the released files.

## The PropBank sense distribution

`make_propbank_sense_distribution.py` builds
`data/propbank-sense-distribution.csv`, the per-verb PropBank-roleset counts that
weight the multi-membership terms, from OntoNotes 5.0.

Unlike the trial-level scripts, which read the JATOS dumps, this one reads
OntoNotes. OntoNotes is LDC-licensed and not shipped here, so running it requires a
local copy of the release tarball. The script streams the tarball in place (it
never extracts it), so point `ONTONOTES_ARCHIVE` at the `.tgz` and run:

```bash
export ONTONOTES_ARCHIVE=~/path/to/ontonotes-release-5.0_LDC2013T19.tgz
python3 data/scripts/make_propbank_sense_distribution.py
```

This writes `data/propbank-sense-distribution.csv` and reproduces the shipped
file exactly. `--verb open` prints a single verb's distribution without writing
anything. `--help` lists the language, part-of-speech, and output options.

---

# Layers metadata records

The Layers (and chive) records for this dataset are built and validated in
[`metadata/`](../../metadata/), with the `lairs` client and the current
`pub.layers.*` lexicons; see `metadata/README.md`.
