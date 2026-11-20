# Analysis pipeline

The models, measures, and figures in White, Grimm, & Glass (2026) can be
reproduced from a single R Jupyter notebook,
[`reproduce.ipynb`](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/analysis/reproduce.ipynb).
Open it inside the docker container described in
[`docker/`](https://github.com/SuperMereo/aspect-is-not-fixed/tree/main/docker)
and run the cells top to bottom.

The pipeline remains in one notebook because each step depends on the ones
before it: the §3 fit takes its prior on the sense weights from the §2 fit, the
§4 match scores are computed from the output of both, and the §5 model depends
on those scores and on the sense weights estimated in the §3 fit. This
ordering keeps the dependencies explicit. One supporting file,
`src/latent_senses.R`, contains (i) the edits that turn each regression's
sense weights into parameters; (ii) the per-sentence logits; and (iii) the
per-pair match.

## Running the notebook

From the repository root:

```bash
cd docker && docker compose up -d
```

Jupyter is then at http://localhost:8888 with no token (see
[`docker/README.md`](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/docker/README.md)
for full docker instructions, including build, security, and
write-access semantics).

The notebook sets its working directory to the repository root by calling
`setwd("..")` when launched from `analysis/`. Relative paths thus resolve the
same way whether Jupyter starts from the root or from `analysis/`.

## Notebook structure

The notebook is organized section by section, in the order the paper
presents them, and each group of cells produces the fits, derived measures, and figure(s)
reported in the corresponding paper section. The table below pairs each
group of cells with its paper section and its outputs.

| Notebook cell group | Paper section | Outputs |
|---|---|---|
| Setup | (none) | Loads packages, sets seed, prepares output dirs |
| Load and prepare data | (none) | `data_cloze_episodic`, the sense tables for the multi-membership effect |
| §2 Experiment 1a: A cloze diagnostic for telicity | [§2.4 Analysis](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/experiment1a.tex), [§2.5 Results](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/experiment1a.tex) | `analysis/fits/cloze-latent.rds`, `figures/cloze_proportions_by_verb.{pdf,png}` (Fig 1) |
| §3 Experiment 1b: A temporal-overlap diagnostic for durativity | [§3.4 Analysis](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/experiment1b.tex), [§3.5 Results](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/experiment1b.tex) | `analysis/fits/proportion-latent.rds`, `figures/nonoverlap_by_verb.{pdf,png}` (Fig 2) |
| §4 Aspectual match | [§4](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/measures.tex) | `analysis/cache/sentence_measures.rds`, `analysis/cache/pair_measures.rds`, `figures/aspect_plane.{pdf,png}` (Fig 3) |
| §5 Experiment 2: Sense similarity | [§5.4 Analysis](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/experiment2.tex), [§5.5 Results](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/experiment2.tex) | `analysis/fits/similarity.rds`, `figures/similarity_by_match.{pdf,png}` (Fig 4) |
| §6 Discussion: responses with the adverbial held fixed | [§6](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/paper/sections/discussion.tex) | Prints how often Experiment 1b responses to the same sentence under the same preposition agree |

## Inputs

The notebook reads from these tracked files only:

| File | Purpose |
|---|---|
| `data/data-cloze.csv` | Experiment 1a raw trial data |
| `data/data-proportion.csv` | Experiment 1b raw trial data |
| `data/data-similarity.csv` | Experiment 2 raw trial data |
| `data/manner-result-sentences.csv` | Verb/sense/sentence inventory, including which contentful sentences each bleached sentence was constructed from. A bleached sentence's weights favor the senses of those sentences. |
| `data/propbank-sense-distribution.csv` | Per-verb PropBank-roleset counts derived from the English portion of OntoNotes 5.0 (Weischedel et al. 2013, LDC2013T19). The counts are modeled as multinomial given each verb's sense proportions, which weight the multi-membership effect. OntoNotes itself is LDC-licensed and not redistributed here. `data/scripts/make_propbank_sense_distribution.py` rebuilds this file from your own copy of the release tarball (see `data/scripts/README.md`). |

Per-column documentation for the data files is in
[`data/README.md`](https://github.com/SuperMereo/aspect-is-not-fixed/blob/main/data/README.md).

## Outputs

| Path | Contents | Tracked? |
|---|---|---|
| `analysis/fits/cloze-latent.rds` | cloze fit with latent sense weights (§2) | no |
| `analysis/fits/proportion-latent.rds` | proportion fit (§3) | no |
| `analysis/fits/similarity.rds` | ordered-beta similarity fit (§5) | no |
| `analysis/fits/*.stan`, `analysis/fits/*-csv/` | the Stan program of each regression and its sampler output | no |
| `analysis/cache/sentence_measures.rds` | posterior mean of each sentence's three logits (§4) | no |
| `analysis/cache/pair_measures.rds` | per-pair aspectual match (§4) | no |
| `figures/cloze_proportions_by_verb.{pdf,png}` | Figure 1 | yes |
| `figures/nonoverlap_by_verb.{pdf,png}` | Figure 2 | yes |
| `figures/aspect_plane.{pdf,png}` | Figure 3 | yes |
| `figures/similarity_by_match.{pdf,png}` | Figure 4 | yes |

The cached fits and measures are excluded from version control. Given the data,
fixed seeds, and pinned docker image, the notebook reproduces them. A first run
from a clean checkout refits every model. Subsequent runs reuse upstream `.rds`
files. To force a refit, delete the relevant `.rds`.

## Runtime

On an 8-core M-series Mac:

- Cloze fit (§2): ~1 h
- Proportion fit (§3): ~3.5 h
- Aspectual match (§4): ~5 min
- Similarity ordered-beta fit (§5): ~4–6.5 h
- Figures: ~1 min each

A cold run takes roughly 9 to 11 hours in total. The similarity fit takes the
longest, so a run that needs only Figures 1–3 can stop once §4 has written
its caches, saving about half the wall-clock time.
