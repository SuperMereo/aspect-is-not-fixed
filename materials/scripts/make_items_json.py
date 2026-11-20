"""Build the Experiment 1a (cloze) stimulus lists.

Reads the sentence inventory in ``data/manner-result-sentences.csv`` and writes
``materials/src/cloze-items.json``, which ``cloze-experiment.js`` loads at run
time. The generator performs three operations.

**1. Blanks are inserted into each sentence.** A cloze trial is a sentence with
in-line dropdowns, and ``plugin-cloze-dropdown.ts`` builds those by splitting the
trial text on the literal marker ``%_%``, so the number of markers written is the
number of dropdowns the participant sees. This script drops the final period,
appends three markers (preposition, numeral, time unit), and restores the period.

**2. The per-condition set removes shared surface forms.** Each row of the CSV is
one PropBank sub-sense, so distinct senses of the same verb are distinct rows, but
they often share a *bleached* counterpart, since bleaching replaces the arguments
with general nouns and collapses the sense distinction. Collecting into a set per
condition deduplicates those collisions. This is why the conditions come out at
different sizes: 166 contentful episodic sentences, 106 bleached episodic ones,
and 40 templatic (one per verb).

**3. Sentences are assigned to lists by round robin over the sorted set.**
Sentence *i* is assigned to list ``i % num_lists[cond]``, which distributes each
condition evenly and yields near-equal list lengths. Sorting before assignment
makes the output independent of hash iteration order: reruns produce a
byte-identical file. Each participant sees one list.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# How many Latin-square lists to split each condition across. Contentful
# conditions get the most lists because they have the most sentences; templatic
# gets one because 40 items is already a short enough block for one sitting.
num_lists = {
    "contentful_episodic": 4,
    "bleached_episodic": 2,
    "templatic_episodic": 1
}

# A set per condition, so bleached and templatic sentences shared across senses
# collapse to one item rather than being presented several times over.
sentences = {
    cond: set() for cond in num_lists
}

items = {
    cond: [[] for _ in range(num_lists[cond])]
    for cond in sentences
}

def make_json(csv_fpath, json_fpath):
    """Read the sentence inventory and write the per-condition, per-list JSON."""

    with open(csv_fpath, encoding='utf-8') as csvf:
        print(f"Constructing sentences from {csv_fpath}...")

        for r in csv.DictReader(csvf):
            for cond, condition_sentences in sentences.items():
                # Strip the period, append one `%_%` per dropdown, restore the
                # period: three markers for preposition, numeral, and time unit.
                condition_sentences.add(
                    r[f"sentence_{cond}"][:-1] + r" %_% %_% %_%."
                )

    for cond, sents in sentences.items():
        # Round robin over the *sorted* sentences: item i lands in list
        # i % num_lists. Sorting is what makes the output reproducible.
        for i, s in enumerate(sorted(sents)):
            list_num = i % num_lists[cond]
            items[cond][list_num].append(s)

        # Sanity check on the assignment; list lengths differ by at most 1.
        for item_list in items[cond]:
            print(cond, len(item_list))

    with open(json_fpath, 'w', encoding='utf-8') as jsonf:
        print(f"Dumping json to {json_fpath}...")
        jsonf.write(json.dumps(items, indent=4))


if __name__ == "__main__":
    make_json(
        str(ROOT / "data" / "manner-result-sentences.csv"),
        str(ROOT / "materials" / "src" / "cloze-items.json")
    )
