# Aspect is not a fixed property of linguistic expressions

Companion repository for White, Grimm, & Glass (2026), *Aspect is not
a fixed property of linguistic expressions*, Experiments in Linguistic
Meaning (ELM) 2026.

The paper asks whether fixing a verb's sense also fixes its telicity and
durativity. We argue that aspect varies within a sense and that this
variation predicts how speakers rate two event descriptions for similarity.

This repository contains the LaTeX source, the jsPsych source for three
behavioral experiments, the cleaned trial-level data, and an R Jupyter
notebook that runs the models and writes the figures. The analysis entry point
is
[`analysis/reproduce.ipynb`](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/analysis/reproduce.ipynb),
which the paper cites as the analysis code.

## Contents

| Path | Contents |
|---|---|
| [`paper/`](paper/) | LaTeX source and the built proceedings PDF (`paper/main.pdf`) |
| [`materials/`](materials/) | jsPsych source for the three behavioral experiments, and the scripts that regenerate the stimulus lists from `data/manner-result-sentences.csv` (see [`materials/README.md`](materials/README.md)) |
| [`data/`](data/) | Cleaned trial-level CSVs and the verb/sentence inventory (see [`data/README.md`](data/README.md) for column-by-column documentation) |
| [`data/scripts/`](data/scripts/) | The scripts that build those CSVs from the raw JATOS output, with participant anonymization, and the scripts that generate the dataset's `pub.layers.*` ATProto records for publication (see [`data/scripts/README.md`](data/scripts/README.md)). The generated records are not tracked. |
| [`analysis/reproduce.ipynb`](analysis/reproduce.ipynb) | R Jupyter notebook ordered by paper section. It runs every model, derives every measure, and writes every figure (see [`analysis/README.md`](analysis/README.md)). |
| [`docker/`](docker/) | Docker image used for all analyses: R 4.6 with brms, ordbetareg, cmdstanr, and tidyverse, plus Python and Node so that every script in the repository runs in the one image |
| [`figures/`](figures/) | The four figures cited in the paper (PDF and PNG), written here by the notebook |

## Quick start

### Read the paper

`paper/main.pdf` is built from the LaTeX source in `paper/` and tracked
in the repository for convenience. To rebuild from source:

```bash
cd paper && latexmk -pdf -bibtex main.tex
```

### Reproduce the analyses

All analyses run inside the docker container under
[`docker/`](https://github.com/SuperMereo/aspect-is-not-fixed/tree/main/docker):

```bash
cd docker && docker compose up -d
```

Jupyter is then at http://localhost:8888 with no token.

Open
[`analysis/reproduce.ipynb`](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/analysis/reproduce.ipynb)
in the browser and run the cells top to bottom. The notebook is
organized to match the paper section by section, so the two can be read
side by side:

| Paper section | Notebook section |
|---|---|
| §2 Experiment 1a: A cloze diagnostic for telicity | Fit, then Figure 1 |
| §3 Experiment 1b: A temporal-overlap diagnostic for durativity | Fit, then Figure 2 |
| §4 Deriving per-pair aspectual match | Per-sentence logits, per-pair aspectual match, then Figure 3 |
| §5 Experiment 2: Sense similarity | Same-sense scores, ordered-beta fit, then Figure 4 |
| §6 Discussion: responses with the adverbial held fixed | Agreement among Experiment 1b responses to the same sentence under the same preposition |

`brms` fits cache to `analysis/fits/` and derived measures cache to
`analysis/cache/`. Neither is tracked, so a first run from a clean
checkout refits every model, though subsequent runs skip any cell whose
upstream `.rds` already exists. That first run takes roughly 9 to 11 hours
on an 8-core M-series Mac, of which the similarity fit accounts for about
half.

### Replicate the behavioral experiments

Full instructions, including JATOS deployment and the
stimulus-regeneration pipeline, are in
[`materials/README.md`](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/materials/README.md).

## What is not tracked

Artifacts that can be regenerated from the tracked source are omitted
(see `.gitignore`):

- `paper/main.{aux,bbl,log,...}`: LaTeX build intermediates.
- `materials/node_modules/`, `materials/.jspsych-builder/`,
  `materials/packaged/`: npm and jspsych-builder outputs.
- `materials/src/{cloze,proportion,similarity}-items.json`: generated
  by the scripts in `materials/scripts/`.
- `analysis/fits/`, `analysis/cache/`: brms model caches and derived
  measures.
- `data/scripts/records/`: the generated `pub.layers.*` ATProto records
  (a deterministic function of `data/` plus the scripts).
- `data/raw-jatos/` and the participant re-identification map: the raw
  JATOS dumps carry Prolific IDs and are not published.

`paper/main.pdf` is tracked for readers who want to inspect the
proceedings paper without rebuilding the LaTeX.

## Citation

```bibtex
@inproceedings{white_aspect_2026,
  author    = {White, Aaron Steven and Grimm, Scott and Glass, Lelia},
  title     = {Aspect is not a fixed property of linguistic expressions},
  booktitle = {Proceedings of Experiments in Linguistic Meaning (ELM)},
  year      = {2026}
}
```

`CITATION.cff` carries the same metadata in citation-file format.

## License

- The code (`analysis/`, `materials/`, `docker/`, `paper/`, and the
  scripts in `data/scripts/`) is licensed under MIT (see `LICENSE`).
- The data (the CSVs and inventories in `data/`) are licensed under
  CC-BY-SA-4.0 (see `data/LICENSE`).
