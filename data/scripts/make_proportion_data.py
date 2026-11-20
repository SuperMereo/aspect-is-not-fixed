#!/usr/bin/env python3
"""Build `data/data-proportion.csv` from the raw Experiment 1b (proportion) JATOS
output.

Experiment 1b showed each sentence with a temporal modifier already filled in and
asked what proportion of that span the event occupied. Every trial is a
`survey-likert` record whose response key is the item ID that
`materials/scripts/make_proportion_items.ipynb` built, and that ID encodes the
whole design (contentfulness, verb, sentence, preposition, numeral, and time
unit), so the trial's condition is recovered by splitting the string rather than
by a lookup.

The participant's list is inferred as in the cloze script: the first Likert
trial's item ID is searched across the deployed lists in
`materials/src/proportion-items.json`, and the list that contains it fixes the
condition for the rest of the file.

The script stops short of writing if any list is still under quota, printing the
JATOS batch-session JSON needed to recruit the remainder. This is a
data-collection convenience retained from the original run; with the full sample
in hand it falls through to writing the CSV.

**Participant identifiers.** Raw `PROLIFIC_PID` values never reach the CSV; they
are replaced by stable UUIDs through `anonymize.py`.
"""
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

# Load the deployed item file.
with open(REPO / "materials" / "src" / "proportion-items.json") as f:
    items = json.load(f)

# Load the raw responses.
data = []

max_count = {
    cond: 10 if "contentful" in cond else (20 if "bleached" in cond else 40)
    for cond in items
}
list_counts = Counter()

for fname in sorted(glob(str(RAW_DIR / "jatos_results_data_202408031*" / "*" / "*" / "*.txt"))):
    with open(fname) as f:
        data_json = json.load(f)

        condition = None
        list_num = None

        for row in data_json:
            if row["trial_type"] == "survey-likert":
                item_id = next(iter(row["response"]))
                if condition is None:
                    for cond, lists in items.items():
                        for n, item_list in enumerate(lists):
                            if item_id in [r["item_id"] for r in item_list]:
                                condition = cond
                                list_num = n

                                list_counts[(condition, list_num)] += 1

                if list_counts[(condition, list_num)] > max_count[condition]:
                    break

                response = row["response"][item_id]
                contentfulness, _, _, sentence, preposition, numeral, duration = item_id.split("-")

                data.append(
                    [
                        anon.pseudonym(row["PROLIFIC_PID"]),
                        contentfulness,
                        list_num,
                        sentence,
                        preposition,
                        numeral,
                        duration,
                        response,
                        row["rt"]
                    ]
            )

data = pd.DataFrame(
    data,
    columns=["participant", "contentfulness", "list_num",
             "sentence", "preposition", "numeral", "duration",
             "response", "rt"]
)

data = pd.merge(metadata, data)

# Verify that every list reached its sample target.
list_counts = data[["condition", "contentfulness", "list_num", "participant"]].drop_duplicates()[["condition", "contentfulness", "list_num"]].value_counts().reset_index()

needs_more = list_counts[
    ((list_counts.contentfulness == "contentful") & (list_counts["count"] < 10)) |
    ((list_counts.contentfulness == "bleached") & (list_counts["count"] < 20)) |
    ((list_counts.contentfulness == "templatic") & (list_counts["count"] < 40))
]

if needs_more.shape[0]:
    needs_more["needed"] = needs_more[["contentfulness", "count"]].apply(
        lambda x: 10 - x[1] if x[0] == "contentful" else (20 - x[1] if x[0] == "bleached" else 40 - x[1]),
        axis=1
    )

    lists_to_run = [
    {"condition": row.contentfulness, "list_num": row.list_num}
    for _, row in needs_more.iterrows()
    for _ in range(row.needed)
    ]

    print(f"{len(lists_to_run)} more participants are needed")
    print()
    print("Batch session data:")
    print()
    print(json.dumps({"lists_to_run": lists_to_run}, indent=4))

    preprocessed_fpath = REPO / "data" / "data-proportion-partial.csv"

    print(f"Only partial sample obtained. Dumping data to {preprocessed_fpath}")

else:
    preprocessed_fpath = REPO / "data" / "data-proportion.csv"

    print(f"Full sample obtained. Dumping data to {preprocessed_fpath}")

header = [
    'participant', 'verb_type',
    'verb', 'propbank_sense',
    'concreteness', 'contentfulness', 'clause_type',
    'condition', 'list_num',
    'subject_noun', 'object_noun',
    'subject_noun_plural', 'object_noun_plural',
    'subject_noun_mass', 'object_noun_mass',
    'sentence', 'preposition', 'numeral', 'duration',
    'response', 'rt'
]

data[header].to_csv(preprocessed_fpath, index=False)
anon.save()
print(f"Wrote {preprocessed_fpath}")
