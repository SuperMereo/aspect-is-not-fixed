#!/usr/bin/env python3
"""Build `data/data-similarity.csv` from the raw Experiment 2 (similarity) JATOS
output.

Experiment 2 paired two event descriptions sharing a verb and collected a slider
rating. Each trial is an `html-slider-response` record whose stimulus HTML
carries both the item ID and the two sentences, so both are parsed back out with
a regular expression rather than by a lookup.

**Presentation order.** The item ID stores the pair in its canonical order, while
the stimulus shows whichever order the participant saw. The two are compared to
set `sentences_reversed`, and the canonical order is always written into
`sentence1`/`sentence2`, so that a pair is one key across participants regardless
of how it was displayed. Note that `sentences_reversed` is True when the displayed
first sentence *equals* the canonical `sentence1`, that is, when the pair was shown
in (sentence1, sentence2) order.

**Per-sentence columns.** Every paired column (`contentfulness1/2`,
`propbank_sense1/2`, `concreteness1/2`) follows the `sentence1`/`sentence2`
positions. The sense and concreteness labels come from the items file, which
orders them by position. Contentfulness is instead looked up per sentence in the
sentence inventory, because the items file labels every mixed pair
`contentful`/`bleached` even when `sentence1` is the bleached member (the
materials notebook tagged both orders alike to balance them across lists).

**Calibration trials.** The eight calibration pairs are defined inline below
rather than read from the items file, because they also live inline in
`similarity-experiment.js` and are prepended to every participant's timeline.
They take `verb_type = "calibration"` and placeholder sense labels, and the
analysis filters them out.

**Recovering the list.** The record does not name the list, and no single pair
identifies one, so the candidate lists are intersected: for each participant, the
set of lists consistent with every non-calibration pair they saw converges on the
one list they were assigned.

**Participant identifiers.** Raw `PROLIFIC_PID` values never reach the CSV; they
are replaced by stable UUIDs through `anonymize.py`.
"""
import json
import os
import re
import sys
from collections import Counter
from glob import glob
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from anonymize import ParticipantAnonymizer

REPO = Path(__file__).resolve().parents[2]

# The raw JATOS dumps are not distributed with this repository (they carry
# identifiers we do not publish). Point RAW_JATOS_DIR at your local copy.
RAW_DIR = Path(os.environ.get("RAW_JATOS_DIR", REPO / "data" / "raw-jatos"))

anon = ParticipantAnonymizer()

# Load sentence metadata.
metadata = pd.read_csv(REPO / "data" / "manner-result-sentences.csv")

metadata = pd.melt(
    metadata,
    id_vars=[
        'verb', 'verb_type', 'propbank_sense', 'concreteness',
        'subject_noun_contentful', 'object_noun_contentful',
        'subject_noun_bleached', 'object_noun_bleached',
        'subject_noun_contentful_plural', 'object_noun_contentful_plural',
        'subject_noun_contentful_mass', 'object_noun_contentful_mass',
        'subject_noun_bleached_plural', 'object_noun_bleached_plural',
        'subject_noun_bleached_mass', 'object_noun_bleached_mass'
    ],
    value_name="sentence",
    var_name="condition",
    value_vars=[
        'sentence_contentful_episodic', 'sentence_bleached_episodic',
        'sentence_templatic_episodic'
    ]
)

metadata["condition"] = metadata.condition.str.replace("sentence_", "")

metadata["subject_noun"] = metadata[["condition", "subject_noun_contentful", "subject_noun_bleached"]].apply(
    lambda x: x[2] if "bleached" in x[0] else (x[1] if "contentful" in x[0] else "X"),
    axis=1
)
metadata["object_noun"] = metadata[["condition", "object_noun_contentful", "object_noun_bleached"]].apply(
    lambda x: x[2] if "bleached" in x[0] else (x[1] if "contentful" in x[0] else "Y"),
    axis=1
)

metadata["subject_noun_plural"] = metadata[["condition", "subject_noun_contentful_plural", "subject_noun_bleached_plural"]].apply(
    lambda x: x[2] if "bleached" in x[0] else (x[1] if "contentful" in x[0] else False),
    axis=1
)
metadata["object_noun_plural"] = metadata[["condition", "object_noun_contentful_plural", "object_noun_bleached_plural"]].apply(
    lambda x: x[2] if "bleached" in x[0] else (x[1] if "contentful" in x[0] else False),
    axis=1
)

metadata["subject_noun_mass"] = metadata[["condition", "subject_noun_contentful_mass", "subject_noun_bleached_mass"]].apply(
    lambda x: x[2] if "bleached" in x[0] else (x[1] if "contentful" in x[0] else False),
    axis=1
)
metadata["object_noun_mass"] = metadata[["condition", "object_noun_contentful_mass", "object_noun_bleached_mass"]].apply(
    lambda x: x[2] if "bleached" in x[0] else (x[1] if "contentful" in x[0] else False),
    axis=1
)

metadata = metadata.drop(
    columns=[
        "subject_noun_contentful", "subject_noun_bleached",
        "object_noun_contentful", "object_noun_bleached",
        'subject_noun_contentful_plural', 'object_noun_contentful_plural',
        'subject_noun_contentful_mass', 'object_noun_contentful_mass',
        'subject_noun_bleached_plural', 'object_noun_bleached_plural',
        'subject_noun_bleached_mass', 'object_noun_bleached_mass'
    ]
)

metadata["contentfulness"] = metadata.condition.map(lambda x: x.split("_")[0])
metadata["clause_type"] = metadata.condition.map(lambda x: x.split("_")[1])

metadata["propbank_sense"] = metadata[["contentfulness", "propbank_sense"]].apply(
    lambda x: x[1] if x[0] == "contentful" else x[0], axis=1
)

metadata["concreteness"] = metadata[["contentfulness", "concreteness"]].apply(
    lambda x: x[1] if x[0] == "contentful" else x[0], axis=1
)

metadata = metadata.drop_duplicates()

# Each contentful and bleached sentence occurs exactly once in the inventory, so
# its contentfulness can be read off the sentence itself. The items file cannot
# be trusted for this: it labels every mixed pair "contentful"/"bleached"
# whichever member is in the sentence1 position (see the module docstring).
sentence_contentfulness = dict(
    zip(metadata.sentence, metadata.contentfulness)
)

calibration_items = {
    "calibration_somewhat_similar-1": {
        "sentence1": "The architect designed the building.",
        "sentence2": "The strategist designed the message.",
        "verb": "design"
    },
    "calibration_somewhat_different-1": {
        "sentence1": "The college permitted the event.",
        "sentence2": "The weather permitted the picnic.",
        "verb": "permit"
    },
    "calibration_very_different-1": {
        "sentence1": "The player bounced the ball.",
        "sentence2": "The bank bounced the check.",
        "verb": "bounce"
    },
    "calibration_very_similar-1": {
        "sentence1": "The dog scratched the itch.",
        "sentence2": "The patient scratched the rash.",
        "verb": "scratch"
    },
    "calibration_somewhat_different-2": {
        "sentence1": "The botanist recognized the mushroom.",
        "sentence2": "The king recognized the bravery.",
        "verb": "recognize"
    },
    "calibration_somewhat_similar-2": {
        "sentence1": "The company dismissed the worker.",
        "sentence2": "The teacher dismissed the class.",
        "verb": "dismiss"
    },
    "calibration_very_similar-2": {
        "sentence1": "The mailman delivered the package.",
        "sentence2": "The visitor delivered the gift.",
        "verb": "deliver"
    },
    "calibration_very_different-2": {
        "sentence1": "The thief stole the painting.",
        "sentence2": "The dancer stole the show.",
        "verb": "steal"
    }
}

# Load the deployed item file.
with open(REPO / "materials" / "src" / "similarity-items.json") as f:
    items = json.load(f)

# Load the raw responses.
data = []

max_count = 10
list_counts = Counter()

for fname in sorted(glob(str(RAW_DIR / "jatos_results_data_20240807*" / "*" / "*" / "*.txt"))):
    with open(fname) as f:
        data_json = json.load(f)

        condition = None
        list_num = None

        for row in data_json:
            if row["trial_type"] == "html-slider-response":
                item_id, = re.findall('<div class="itemid">(.*?)</div>', row["stimulus"])
                sentence1, sentence2 = re.findall('<p>(.*?)</p>', row["stimulus"])

                if "calibration" not in item_id:
                    canonical_order, _ = item_id.split("%_%")

                    sentence1_canonical, sentence2_canonical = canonical_order.split("%")

                    sentences_reversed = sentence1 == sentence1_canonical

                    item = next(
                        i for item_list in items for i in item_list
                        if i["sentence1"] == sentence1_canonical
                        if i["sentence2"] == sentence2_canonical
                    )

                    verb_type = item["verb_type"]
                    verb = item["verb"]
                    pb_sense1, pb_sense2 = item["propbank_sense1"], item["propbank_sense2"]
                    contentfulness1 = sentence_contentfulness[sentence1_canonical]
                    contentfulness2 = sentence_contentfulness[sentence2_canonical]
                    concreteness1, concreteness2 = item["concreteness1"], item["concreteness2"]

                else:
                    item = calibration_items[item_id]

                    sentence1_canonical = item["sentence1"]
                    sentence2_canonical = item["sentence2"]

                    sentences_reversed = sentence1 == sentence1_canonical

                    contentfulness1 = contentfulness2 = "contentful"

                    verb_type = "calibration"
                    verb = item["verb"]

                    pb_sense1 = pb_sense2 = concreteness1 = concreteness2 = "calibration"

                # Raw IDs are replaced by pseudonyms before writing (below).
                data.append(
                    [
                        row["PROLIFIC_PID"],
                        verb_type,
                        verb,
                        contentfulness1,
                        contentfulness2,
                        pb_sense1, pb_sense2,
                        concreteness1, concreteness2,
                        sentences_reversed,
                        sentence1_canonical,
                        sentence2_canonical,
                        row["response"],
                        row["rt"]
                    ]
            )

data = pd.DataFrame(
    data,
    columns=["participant",
             "verb_type", "verb",
             "contentfulness1", "contentfulness2",
            "propbank_sense1", "propbank_sense2",
            "concreteness1", "concreteness2",
            "sentences_reversed",
            "sentence1", "sentence2",
             "response", "rt"]
)

possible_lists = {}

for pid, df_part in data.groupby("participant"):
    possible_lists[pid] = set(range(len(items)))
    for _, r in df_part[df_part.verb_type != "calibration"].iterrows():
        possible_lists[pid] &= {
            j for j, item_list in enumerate(items)
            for it in item_list
            if r.sentence1 == it["sentence1"]
            and r.sentence2 == it["sentence2"]
        }


participant_list = pd.DataFrame(
    [[pid, next(iter(s))] for pid, s in possible_lists.items()],
    columns=["participant", "list_num"]
)

data = pd.merge(participant_list, data)

# Replace raw IDs with pseudonyms.
data["participant"] = data.participant.map(anon.pseudonym)
participant_list["participant"] = participant_list.participant.map(anon.pseudonym)

# Verify that every list reached its sample target.
list_counts = participant_list.value_counts("list_num").reset_index()

needs_more = list_counts[list_counts["count"] < 10]

if needs_more.shape[0]:
    needs_more["needed"] = 10 - needs_more["count"]

    lists_to_run = [
        {"list_num": int(row.list_num)}
        for _, row in needs_more.iterrows()
        for _ in range(row.needed)
    ]

    print(f"{len(lists_to_run)} more participants are needed")
    print()
    print("Batch session data:")
    print()
    print(json.dumps({"lists_to_run": lists_to_run}, indent=4))

    preprocessed_fpath = REPO / "data" / "data-similarity-partial.csv"

    print(f"Only partial sample obtained. Dumping data to {preprocessed_fpath}")

else:
    preprocessed_fpath = REPO / "data" / "data-similarity.csv"

    print(f"Full sample obtained. Dumping data to {preprocessed_fpath}")

header = ["participant", "list_num",
             "verb_type", "verb",
             "contentfulness1", "contentfulness2",
            "propbank_sense1", "propbank_sense2",
            "concreteness1", "concreteness2",
            "sentences_reversed",
            "sentence1", "sentence2",
             "response", "rt"]

data[header].to_csv(preprocessed_fpath, index=False)
anon.save()
print(f"Wrote {preprocessed_fpath}")
