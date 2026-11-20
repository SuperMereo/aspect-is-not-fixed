#!/usr/bin/env python3
"""Build `data/data-cloze.csv` from the raw Experiment 1a (cloze) JATOS output.

A JATOS result file is one JSON array per participant, one object per trial. This
script keeps the cloze trials, recovers the condition and list each participant
saw by matching the trial text against `materials/src/cloze-items.json`, strips
the `%_%` blank markers back off the sentence, and joins the result to the
sentence inventory, so that every judgment carries its verb, sense, and argument
metadata.

**Recovering the condition.** The JATOS record does not name the assigned list,
so it is inferred: the first cloze trial's text is looked up across every
condition's lists, and whichever list contains it fixes the condition and list
number for the rest of the file. This depends on the item files being the ones
that were deployed; regenerate them with `materials/scripts/make_items_json.py`
if they are missing.

**Participant identifiers.** Raw `PROLIFIC_PID` values never reach the CSV; they
are replaced by stable UUIDs through `anonymize.py`, which documents where the
map lives.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter
from glob import glob
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anonymize import ParticipantAnonymizer

REPO = Path(__file__).resolve().parents[2]
META_PATH = REPO / "data" / "manner-result-sentences.csv"
ITEMS_PATH = REPO / "materials" / "src" / "cloze-items.json"
OUT_PATH = REPO / "data" / "data-cloze.csv"

# The raw JATOS dumps are not distributed with this repository (they carry
# identifiers we do not publish). Point RAW_JATOS_DIR at your local copy.
RAW_DIR = Path(os.environ.get("RAW_JATOS_DIR", REPO / "data" / "raw-jatos"))
JATOS_GLOB = str(RAW_DIR / "jatos_results_data_2024071*" / "*" / "*" / "*.txt")


def load_metadata() -> pd.DataFrame:
    raw = pd.read_csv(META_PATH)

    melted = pd.melt(
        raw,
        id_vars=[
            "verb", "verb_type", "propbank_sense", "concreteness",
            "subject_noun_contentful", "object_noun_contentful",
            "subject_noun_bleached", "object_noun_bleached",
            "subject_noun_contentful_plural", "object_noun_contentful_plural",
            "subject_noun_contentful_mass", "object_noun_contentful_mass",
            "subject_noun_bleached_plural", "object_noun_bleached_plural",
            "subject_noun_bleached_mass", "object_noun_bleached_mass",
        ],
        value_name="sentence",
        var_name="condition",
        value_vars=[
            "sentence_contentful_episodic", "sentence_bleached_episodic",
            "sentence_templatic_episodic",
        ],
    )
    melted["condition"] = melted["condition"].str.replace("sentence_", "", regex=False)
    melted["sentence"] = melted["sentence"].str.strip()

    melted["subject_noun"] = melted.apply(
        lambda x: (
            x["subject_noun_bleached"] if "bleached" in x["condition"]
            else (x["subject_noun_contentful"] if "contentful" in x["condition"] else "X")
        ),
        axis=1,
    )
    melted["object_noun"] = melted.apply(
        lambda x: (
            x["object_noun_bleached"] if "bleached" in x["condition"]
            else (x["object_noun_contentful"] if "contentful" in x["condition"] else "Y")
        ),
        axis=1,
    )
    melted["subject_noun_plural"] = melted.apply(
        lambda x: (
            x["subject_noun_bleached_plural"] if "bleached" in x["condition"]
            else (x["subject_noun_contentful_plural"] if "contentful" in x["condition"] else False)
        ),
        axis=1,
    )
    melted["object_noun_plural"] = melted.apply(
        lambda x: (
            x["object_noun_bleached_plural"] if "bleached" in x["condition"]
            else (x["object_noun_contentful_plural"] if "contentful" in x["condition"] else False)
        ),
        axis=1,
    )
    melted["subject_noun_mass"] = melted.apply(
        lambda x: (
            x["subject_noun_bleached_mass"] if "bleached" in x["condition"]
            else (x["subject_noun_contentful_mass"] if "contentful" in x["condition"] else False)
        ),
        axis=1,
    )
    melted["object_noun_mass"] = melted.apply(
        lambda x: (
            x["object_noun_bleached_mass"] if "bleached" in x["condition"]
            else (x["object_noun_contentful_mass"] if "contentful" in x["condition"] else False)
        ),
        axis=1,
    )

    melted = melted.drop(
        columns=[
            "subject_noun_contentful", "subject_noun_bleached",
            "object_noun_contentful", "object_noun_bleached",
            "subject_noun_contentful_plural", "object_noun_contentful_plural",
            "subject_noun_contentful_mass", "object_noun_contentful_mass",
            "subject_noun_bleached_plural", "object_noun_bleached_plural",
            "subject_noun_bleached_mass", "object_noun_bleached_mass",
        ]
    )

    melted["contentfulness"] = melted["condition"].map(lambda x: x.split("_")[0])
    melted["clause_type"] = melted["condition"].map(lambda x: x.split("_")[1])
    melted["propbank_sense"] = melted.apply(
        lambda x: x["propbank_sense"] if x["contentfulness"] == "contentful" else x["contentfulness"],
        axis=1,
    )
    melted["concreteness"] = melted.apply(
        lambda x: x["concreteness"] if x["contentfulness"] == "contentful" else x["contentfulness"],
        axis=1,
    )

    # Keep one metadata row per experimental sentence, choosing the first row
    # after deterministic sorting.
    melted = (
        melted.sort_values(["condition", "sentence", "verb", "propbank_sense"])
        .drop_duplicates(subset=["condition", "sentence"], keep="first")
        .reset_index(drop=True)
    )
    assert melted.duplicated(subset=["condition", "sentence"]).sum() == 0
    return melted


def load_judgments(items: dict, anon: ParticipantAnonymizer) -> pd.DataFrame:
    max_count = {
        cond: 10 if "contentful" in cond else (20 if "bleached" in cond else 40)
        for cond in items
    }
    list_counts: Counter = Counter()
    rows = []

    for fname in sorted(glob(JATOS_GLOB)):
        with open(fname) as f:
            data_json = json.load(f)

        condition = None
        list_num = None
        for row in data_json:
            if row["trial_type"] != "cloze-dropdown":
                continue
            if condition is None:
                for cond, lists in items.items():
                    for n, lst in enumerate(lists):
                        if row["text"] in lst:
                            condition = cond
                            list_num = n
                            list_counts[(condition, list_num)] += 1
                            break
                    if condition is not None:
                        break
                if condition is None:
                    continue

            if list_counts[(condition, list_num)] > max_count[condition]:
                break

            numeral = (
                row["responses"]["numeral"].replace(",", "")
                if "numeral" in row["responses"]
                else ""
            )
            sentence = (
                row["text"]
                .replace(" %_% %_% %_%", "")
                .replace(" %_% %_%", "")
                .strip()
            )
            rows.append(
                [
                    anon.pseudonym(row["PROLIFIC_PID"]),
                    condition,
                    list_num,
                    sentence,
                    row["responses"]["preposition"],
                    numeral,
                    row["responses"]["duration"],
                ]
            )

    return pd.DataFrame(
        rows,
        columns=[
            "participant", "condition", "list_num",
            "sentence", "preposition", "numeral", "duration",
        ],
    )


def validate(data: pd.DataFrame) -> None:
    n = len(data)
    n_sent = data["sentence"].nunique()
    assert n == 5380, f"expected 5380 judgments, got {n}"
    assert n_sent == 312, f"expected 312 sentences, got {n_sent}"
    assert data.duplicated(
        subset=["participant", "condition", "list_num", "sentence",
                "preposition", "numeral", "duration"]
    ).sum() == 0, "duplicate trial records remain"
    # Count responses by sentence.
    counts = data.groupby(["condition", "sentence"]).size()
    for cond, expected in [
        ("contentful_episodic", 10),
        ("bleached_episodic", 20),
        ("templatic_episodic", 40),
    ]:
        sub = counts.loc[cond] if cond in counts.index.get_level_values(0) else None
        assert sub is not None
        assert (sub == expected).all(), f"{cond} response counts not all {expected}"
    print(f"OK: {n} judgments, {n_sent} sentences")


def main() -> None:
    if not glob(JATOS_GLOB):
        raise SystemExit(
            f"No raw JATOS files under {RAW_DIR}. These are not distributed with\n"
            f"the repository; set RAW_JATOS_DIR to your local copy."
        )

    with open(ITEMS_PATH) as f:
        items = json.load(f)

    anon = ParticipantAnonymizer()
    metadata = load_metadata()
    judgments = load_judgments(items, anon)
    data = pd.merge(metadata, judgments, on=["condition", "sentence"], how="inner")
    assert len(data) == len(judgments), (
        f"merge changed row count: judgments={len(judgments)} merged={len(data)}"
    )

    # Verify sample completeness against the collection thresholds.
    list_counts = (
        data[["condition", "contentfulness", "list_num", "participant"]]
        .drop_duplicates()[["condition", "contentfulness", "list_num"]]
        .value_counts()
        .reset_index(name="count")
    )
    needs_more = list_counts[
        ((list_counts.contentfulness == "contentful") & (list_counts["count"] < 10))
        | ((list_counts.contentfulness == "bleached") & (list_counts["count"] < 20))
        | ((list_counts.contentfulness == "templatic") & (list_counts["count"] < 40))
    ]
    if len(needs_more):
        raise SystemExit(f"Incomplete sample: {len(needs_more)} lists still short")

    header = [
        "participant", "verb_type",
        "verb", "propbank_sense",
        "concreteness", "contentfulness", "clause_type",
        "condition", "list_num",
        "subject_noun", "object_noun",
        "subject_noun_plural", "object_noun_plural",
        "subject_noun_mass", "object_noun_mass",
        "sentence", "preposition", "numeral", "duration",
    ]
    # Normalize empty numerals.
    data["numeral"] = data["numeral"].fillna("").astype(str)

    validate(data[header])
    data[header].to_csv(OUT_PATH, index=False)
    anon.save()
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
