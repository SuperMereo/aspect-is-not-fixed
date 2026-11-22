"""Build the Experiment 1a (cloze) stimulus lists.

Reads the sentence inventory in ``data/manner-result-sentences.csv`` and writes
``materials/src/cloze-items.json``, which ``cloze-experiment.js`` loads at run
time. The output holds the five conditions the experiment ran, each split into
the lists participants were assigned to, in the order the items were deployed.

**1. Blanks are inserted into each sentence.** A cloze trial is a sentence with
in-line dropdowns, and ``plugin-cloze-dropdown.ts`` builds those by splitting the
trial text on the literal marker ``%_%``, so the number of markers written is the
number of dropdowns the participant sees. This script drops the final period,
appends the markers, and restores the period. Episodic sentences get three
(preposition, numeral, time unit); generic sentences get two (preposition, time
unit), since a generic description does not ask for a number of units.

**2. Each sentence is placed in its deployed list.** The inventory records, for
every condition, which list a sentence was assigned to
(``cloze_list_<condition>``) and its 0-based position within that list
(``cloze_position_<condition>``). Each participant sees one list. Every
inventory row is one PropBank (sub-)sense, so the bleached, generic, and
templatic sentences of distinct senses of a verb often coincide; such a shared
sentence is one item, and every row carrying it records the same list and
position. This is why the conditions differ in size: 166 contentful sentences
per clause type, 106 bleached episodic, 96 bleached generic, and 40 templatic
(one per verb).

The generic conditions were run but are not reported in the paper; see
``materials/README.md``.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The conditions in the order the experiment defines them, with the number of
# dropdowns each condition's items carry.
CONDITIONS = {
    "contentful_episodic": 3,
    "bleached_episodic": 3,
    "contentful_generic": 2,
    "bleached_generic": 2,
    "templatic_episodic": 3,
}


def make_item(sentence, num_blanks):
    """Replace the final period with `num_blanks` dropdown markers and a period."""
    assert sentence.endswith("."), sentence
    return sentence[:-1] + " %_%" * num_blanks + "."


def make_json(csv_fpath, json_fpath):
    """Read the sentence inventory and write the per-condition, per-list JSON."""

    placement = {cond: {} for cond in CONDITIONS}

    with open(csv_fpath, encoding="utf-8") as csvf:
        print(f"Constructing sentences from {csv_fpath}...")

        for r in csv.DictReader(csvf):
            for cond, num_blanks in CONDITIONS.items():
                item = make_item(r[f"sentence_{cond}"], num_blanks)
                slot = (int(r[f"cloze_list_{cond}"]), int(r[f"cloze_position_{cond}"]))
                # A sentence shared by several rows must sit in one place.
                assert placement[cond].setdefault(item, slot) == slot, (cond, item)

    items = {}
    for cond, placed in placement.items():
        num_lists = 1 + max(list_num for list_num, _ in placed.values())
        items[cond] = [[] for _ in range(num_lists)]
        for item, (list_num, position) in sorted(placed.items(), key=lambda kv: kv[1]):
            # Positions run 0, 1, 2, ... within each list, with no gaps or ties.
            assert position == len(items[cond][list_num]), (cond, item)
            items[cond][list_num].append(item)

        print(cond, [len(item_list) for item_list in items[cond]])

    with open(json_fpath, "w", encoding="utf-8") as jsonf:
        print(f"Dumping json to {json_fpath}...")
        jsonf.write(json.dumps(items, indent=4))


if __name__ == "__main__":
    make_json(
        str(ROOT / "data" / "manner-result-sentences.csv"),
        str(ROOT / "materials" / "src" / "cloze-items.json")
    )
