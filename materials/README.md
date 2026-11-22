# Materials

Source for the three behavioral experiments reported in White, Grimm, & Glass
(2026), *Aspect is not a fixed property of linguistic expressions* (ELM 2026):

| Experiment           | Paper § | jsPsych entry point             | items file                    |
|----------------------|---------|---------------------------------|-------------------------------|
| 1a (cloze)           | §2      | `src/cloze-experiment.js`       | `src/cloze-items.json`        |
| 1b (proportion)      | §3      | `src/proportion-experiment.js`  | `src/proportion-items.json`   |
| 2 (similarity)       | §5      | `src/similarity-experiment.js`  | `src/similarity-items.json`   |

Experiment 1a ran five conditions: contentful, bleached, and templatic
episodic descriptions, which the paper reports, and contentful and bleached
generic descriptions (e.g. *People push things.*), which it does not. The
generic conditions are part of `cloze-experiment.js` and `cloze-items.json`, so
the materials here are those that were deployed, but their responses are not
released in `data/`.

We collected all three experiments on Prolific via JATOS, and the build
toolchain is [jspsych-builder](https://github.com/bjoluc/jspsych-builder) on
top of jsPsych 7.x.

The `*-items.json` files serve two roles: they are inputs to data collection and
to preprocessing, which reads them to recover per-item structure. Treat them as
stimuli, even though the scripts can regenerate them.

## Directory layout

```
materials/
├── README.md                    this file
├── package.json                 npm dependencies and build scripts
├── package-lock.json            pinned dependency tree
├── experiment_text.json         verbatim participant-facing text (instructions,
│                                response options, slider config, calibration
│                                items), structured from the src/*.js sources
├── src/
│   ├── cloze-experiment.js          Exp 1a entry point
│   ├── cloze-items.json             stimuli for Exp 1a
│   ├── plugin-cloze-dropdown.ts     custom jsPsych plugin (cloze dropdowns)
│   ├── proportion-experiment.js     Exp 1b entry point
│   ├── proportion-items.json        stimuli for Exp 1b
│   ├── similarity-experiment.js     Exp 2 entry point
│   └── similarity-items.json        stimuli for Exp 2
├── styles/
│   ├── main.scss                shared styles
│   ├── proportion.scss          Exp 1b styles
│   └── similarity.scss          Exp 2 styles
├── assets/                      (image assets; unused by these three experiments)
└── scripts/                     stimulus-generation pipeline (see below)
```

## Replicating the live experiments

### 1. Install Node 18+ and the dependencies

```bash
cd materials
npm install
```

### 2. Run an experiment locally (development server)

`package.json` exposes the experiment-name as a single positional argument to
the `jspsych` script. Run any one of:

```bash
npm run jspsych -- run cloze-experiment
npm run jspsych -- run proportion-experiment
npm run jspsych -- run similarity-experiment
```

`jspsych-builder` will open a browser tab at `http://localhost:3000` (or
the next free port if 3000 is in use) running the experiment with the items
from the matching `*-items.json`.

Each experiment file has a top-level `const debugMode = true` that bypasses
the JATOS batch-session machinery for local testing. Set it to `false` before
building for JATOS deployment. A debug-mode build runs without error but assigns
every participant to the same list.

### 3. Build a JATOS-deployable bundle

After setting `debugMode = false` in the experiment file:

```bash
npm run jspsych -- build --jatos cloze-experiment
npm run jspsych -- build --jatos proportion-experiment
npm run jspsych -- build --jatos similarity-experiment
```

Each command writes a `.jzip` (JATOS-import bundle) to `packaged/`. To deploy:

1. In a fresh JATOS installation (we used JATOS 3.x), choose **New Study →
Import** and upload the `.jzip`.
2. JATOS will create the study with one component pointing at
`index.html`. The experiment's batch-session counter (`lists_to_run`, set up
by `initBatchConditions()`) handles list assignment automatically.
3. Set the per-list participant cap in the experiment file's
`numParticipantsPerList` constant before building. The values we used are
documented at the top of each `*-experiment.js`.
4. Link the JATOS study to the Prolific study. The participant ID is
captured from the URL query parameters via `jatos.urlQueryParameters`.

### 4. Deployed stimulus files

The experiments load the `*-items.json` files used in data collection directly.
These files are not tracked: `.gitignore` excludes them because the generators
in `scripts/` reproduce them from `data/`. A fresh clone must regenerate them
before running an experiment.

## Regenerating the stimulus JSON from source

The `scripts/` directory contains the three generators that produced the
`*-items.json` files from `data/manner-result-sentences.csv` (the
verb/sentence inventory) and `data/data-cloze.csv` (cloze norming, used to pick
plausible duration units for the proportion stimuli).

| script                                       | output                          | requires                                         |
|----------------------------------------------|---------------------------------|--------------------------------------------------|
| `scripts/make_items_json.py`                 | `src/cloze-items.json`          | `data/manner-result-sentences.csv` (sentences and their `cloze_list_*`, `cloze_position_*` columns) |
| `scripts/make_proportion_items.ipynb`        | `src/proportion-items.json`     | `data/data-cloze.csv` + `manner-result-sentences.csv` |
| `scripts/make_similarity_judgment_materials.ipynb` | `src/similarity-items.json` | `data/manner-result-sentences.csv`               |

The notebooks require `pandas` and `scipy`. Everything else is the Python
standard library. From the repository root:

```bash
pip install pandas scipy jupyter

# cloze items
python materials/scripts/make_items_json.py

# proportion items
jupyter nbconvert --to notebook --execute \
  materials/scripts/make_proportion_items.ipynb \
  --output /tmp/_run.ipynb && rm /tmp/_run.ipynb

# similarity items
jupyter nbconvert --to notebook --execute \
  materials/scripts/make_similarity_judgment_materials.ipynb \
  --output /tmp/_run.ipynb && rm /tmp/_run.ipynb
```

Each script overwrites the corresponding file in `src/`. All three are
deterministic: each fixes its ordering before writing, so regeneration is
independent of `PYTHONHASHSEED`.

Regeneration reproduces the deployed item files exactly. The cloze generator
places each sentence in the list and at the position the inventory records for
it (`cloze_list_<condition>`, `cloze_position_<condition>`), so it writes the
five conditions' deployed lists, with the items of each list in their deployed
order.

Run order matters in one place. `make_proportion_items.ipynb` derives each
sentence's fixed temporal modifier from the Experiment 1a responses in
`data/data-cloze.csv`, so it depends on the collected data. It does not
depend on the cloze items file or on `make_items_json.py` having been run
first. The three generators are independent of one another.

## Notes

- Each experiment maintains a server-side counter
(`jatos.batchSession`) of how many participants per list have completed the
study, so list assignment is balanced across the population. The
initialization logic in `initBatchConditions()` is idempotent: it sets the
counter the first time the study runs, and reads from it thereafter.
- Calibration trials in Experiment 2 are defined inline in
`similarity-experiment.js` (the `calibration_items` array, 8 items spanning
  *very_similar*, *somewhat_similar*, *somewhat_different*, and
  *very_different* pairs) and prepended to every participant's timeline. They
appear in `data/data-similarity.csv` with `verb_type = "calibration"`.
- The `debugMode = true` flag at the top of each experiment
file makes the study run against `list_num = 0` and skips the JATOS
batch-session machinery, so the experiment runs end-to-end locally with no
JATOS server. Set it back to `false` before building for deployment.
- `experiment_text.json` is a structured, condition-keyed copy of the
verbatim participant-facing text (the per-condition instructions, the dropdown
and Likert response options, the similarity slider config, and the calibration
items). The `src/*-experiment.js` sources are canonical: they carry this text
and are what ran. The JSON exists only so the metadata generator in
`data/scripts/` can read the text without parsing the JavaScript. Nothing in
the live experiments depends on it. Because it is a copy, it can drift from
the `.js`. Run `scripts/check_experiment_text.py` to confirm every instruction
and calibration sentence in the JSON still appears in the corresponding `.js`,
and update the JSON if the source text changes.
