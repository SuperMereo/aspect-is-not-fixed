#!/usr/bin/env python3
"""Guard against drift between experiment_text.json and the jsPsych sources.

`materials/experiment_text.json` is a structured, condition-keyed copy of the
verbatim participant-facing text. The canonical source of that text is the
`src/*-experiment.js` files, which are the deployed programs. Because the JSON is
a hand-maintained copy, the two can drift: an instruction is edited in the `.js`
and not updated in the JSON, or the reverse.

The check asserts that every substantial verbatim string in the JSON (the
per-condition instructions, the similarity prompt, and the calibration sentences)
still appears in the corresponding `.js`. It collapses whitespace before
comparison so that source reflowing does not cause a false positive. It omits
short structured tokens because the `.js` render them with placeholders.

Exit status is non-zero if anything has drifted. Run it from anywhere.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TEXT = REPO / "materials" / "experiment_text.json"
SRC = REPO / "materials" / "src"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s)).strip()


def main() -> int:
    text = json.loads(TEXT.read_text())
    js = {
        "cloze": norm((SRC / "cloze-experiment.js").read_text()),
        "proportion": norm((SRC / "proportion-experiment.js").read_text()),
        "similarity": norm((SRC / "similarity-experiment.js").read_text()),
    }

    # (label, expected-substring, which .js it should appear in)
    checks: list[tuple[str, str, str]] = []
    for cond, txt in text["cloze_instructions"].items():
        checks.append((f"cloze_instructions[{cond}]", txt, "cloze"))
    for cond, txt in text["proportion_instructions"].items():
        checks.append((f"proportion_instructions[{cond}]", txt, "proportion"))
    checks.append(("similarity_instructions", text["similarity_instructions"], "similarity"))
    checks.append(("similarity_base_prompt", text["similarity_base_prompt"], "similarity"))
    for it in text["similarity_calibration_items"]:
        checks.append((f"calibration[{it['item_id']}].sentence1", it["sentence1"], "similarity"))
        checks.append((f"calibration[{it['item_id']}].sentence2", it["sentence2"], "similarity"))

    drifted = [label for label, expected, where in checks if norm(expected) not in js[where]]

    if drifted:
        print(f"DRIFT: {len(drifted)} of {len(checks)} strings are no longer in the .js sources:")
        for label in drifted:
            print(f"  - {label}")
        print("\nUpdate materials/experiment_text.json to match the src/*-experiment.js text.")
        return 1

    print(f"OK: all {len(checks)} verbatim strings in experiment_text.json match the .js sources.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
