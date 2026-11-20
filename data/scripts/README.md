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

## Reproduction status

Each script is deterministic (it sorts its inputs before writing), so a rerun
reproduces the shipped CSV given the same raw dumps and participant map:

- **`make_proportion_data.py`** reproduces `data/data-proportion.csv` exactly
(10,340 rows).
- **`make_similarity_data.py`** reproduces `data/data-similarity.csv` exactly
(12,416 rows).
- **`make_cloze_data.py`** does not currently complete. It recovers 5,245 of
the expected 5,380 judgments (117 of 120 participants) and halts at its own
completeness check with two lists short of quota: three participants' files
match no list during condition inference. It is a work in progress. Treat
it as documentation of the extraction. The gap appears to lie in condition
inference rather than missing data, but diagnosing it is a separate task.

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

`generate_metadata.py` reads the data in `data/`, the sentence inventory, and
the verbatim experiment text in `materials/experiment_text.json`, and builds
the dataset's `pub.layers.*` ATProto records (the corpus, the stimulus
expressions, the per-sentence annotations, the experiment definitions and
templates, and the trial-level judgments), and `validate_metadata.mjs` checks
every one against the layers lexicons.

The generated records are not tracked. They are a deterministic function of
`data/` plus the scripts, so only the scripts are versioned.
`generate_metadata.py` writes to `data/scripts/records/` (gitignored; override
with `LAYERS_RECORDS_DIR`), and a rebuild reproduces them.

## Run it

```bash
cd data/scripts
python3 generate_metadata.py          # writes records/ (5,844 records)
node    validate_metadata.mjs          # strict validation against the lexicons
```

Configure via `data/scripts/.env` (gitignored; see `.env.example`):

- `LAYERS_LEXICONS`: a local checkout of the layers lexicons, pinned to the
  **0.9.0** release (branch `lexicons-v0.9.0`). It is not vendored here, but validation
needs it. `npm install` once so the validator can resolve `@atproto/lexicon`.
- `SUPERMEREO_STEM` (default `supertelicity.eng`), `SUPERMEREO_DOMAIN` (default
`supermereo.io`), `SUPERMEREO_EPRINT_URL`: the handle/identifier config below.

## Handle and rkey convention

Records publish to the Layers PDS under the finalized handle convention (see
`notes/handle-convention-for-new-datasets.md` in layers-repo):

```
<namespace>.<stem>.repo.<domain>     per-namespace data account
<stem>.repo.<domain>                 the dataset account (no namespace)
```

`<namespace>` is a `pub.layers` lexicon namespace, `<stem>` is
`<dataset>.<lang-iso639-3>` (here `supertelicity.eng`), `repo` marks a data
account, and `<domain>` is `supermereo.io`. Thus, the corpus is at
`corpus.supertelicity.eng.repo.supermereo.io`, its expressions at
`expression.…`, and so on. AT-URIs are `at://<handle>/<collection>/<rkey>`,
where the rkey is the first 24 hex of
`SHA-256("<handle>|<collection>|<local_id>")`, so a rebuild upserts the
existing records. The handle resolves to a minted DID at publish time. Nothing
hardcodes a DID.

## What gets generated (5,844 records, all `pub.layers.*`)

| Group | Records | Count |
|---|---|---:|
| Annotation vocabulary | `ontology` + `typeDef` | 1 + 3 |
| Corpus + paper link | `corpus` + `corpus.membership` + `eprint.eprint` + `eprint.dataLink` | 1 + 498 + 1 + 4 |
| Verb inventory | `resource.collection`/`entry`/`membership` + pair `clusterSet` | 1 + 40 + 40 + 1 |
| PropBank senses | `resource.collection`/`entry`/`membership` | 1 + 62 + 62 |
| Stimuli (166 × 3 variants) | `expression` + variant `clusterSet` | 498 + 1 |
| Per-expression annotations | `annotationLayer` (3 layers × 498) | 1494 |
| Cohort + value pools | `persona` + `resource.collection`/`entry`/`membership` | 1 + 5 + 68 + 68 |
| Experiments + templates | `experimentDef` (3+3+1) + cloze/proportion `template` | 7 + 3 + 3 |
| Exp 2 stimulus chain | pair `template` + pool + entries + memberships + `filling` | 1 + 1 + 272 + 272 + 750 |
| Exp 2 calibration | `template` + pair + child-sentence `expression` + `filling` | 1 + 8 + 16 + 8 |
| Per-stimulus fillings | Exp 1a + Exp 1b `filling` | 498 + 582 |
| Trial-level responses | `judgmentSet` (one per participant × condition) | 572 |

The paper is referenced as an external eprint: the `eprint.eprint` record
carries the paper's URL/DOI (`SUPERMEREO_EPRINT_URL`), and the corpus,
expressions, and fillings point at that record.
