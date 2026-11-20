"""Build data/propbank-sense-distribution.csv from the OntoNotes 5.0 archive.

The script extracts per-verb PropBank-roleset counts. OntoNotes 5.0 is
LDC-licensed and not shipped here, so running the script requires a local copy
of the release tarball (see ONTONOTES_ARCHIVE below).

This script reads the OntoNotes release tarball *in place* (it never extracts
the archive to disk). It streams every ``.prop`` file, parses the PropBank
roleset assigned to each predicate, and computes:

- raw counts of each sense (roleset, e.g. ``run.01``),
- the marginal log-probability ``log p(sense)`` over all predicate instances, and
- the conditional log-probability ``log p(sense | verb)`` for each lemma.

All log-probabilities are natural logs.

Here a "sense" is a full PropBank roleset such as ``open.01``, and the "verb"
is the lemma preceding the dot (``open``). ``p(sense | verb)`` is thus the
normalized distribution over the rolesets that share a given lemma.

Examples
--------
Write the full English distribution to CSVs::

    python propbank_sense_distribution.py --out-dir ./output

Print the distribution for a single verb::

    python propbank_sense_distribution.py --verb open
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
import tarfile
from collections import Counter, defaultdict
from collections.abc import Iterator
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# OntoNotes 5.0 is LDC-licensed and not distributed with this repository. Point
# ONTONOTES_ARCHIVE at your own copy of the release tarball, or drop it at the
# default path below (which .gitignore excludes so it can never be committed).
DEFAULT_ARCHIVE = Path(
    os.environ.get("ONTONOTES_ARCHIVE",
                   REPO / "data" / "ontonotes-release-5.0_LDC2013T19.tgz")
)

# a roleset looks like "lemma.NN": a lemma, a dot, then a sense id (digits or
# tokens like "LV"). the lemma itself may contain hyphens or underscores.
ROLESET_RE = re.compile(r"^(?P<verb>.+)\.(?P<sense>[A-Za-z0-9]+)$")


def iter_prop_lines(archive: Path, language: str) -> Iterator[str]:
    """Yield raw ``.prop`` lines from the archive without extracting it.

    Parameters
    ----------
    archive
        Path to the OntoNotes ``.tgz`` file.
    language
        Language subtree to include (e.g. ``"english"``), or ``"all"`` to
        include every language.

    Yields
    ------
    str
        A single line from a ``.prop`` file.
    """
    lang_marker = None if language == "all" else f"/{language}/"

    # "r|gz" streams the gzip archive without loading it into memory.
    # extractfile must be consumed before advancing.
    with tarfile.open(archive, mode="r|gz") as tar:
        for member in tar:
            if not member.isfile() or not member.name.endswith(".prop"):
                continue

            if lang_marker is not None and lang_marker not in member.name:
                continue

            handle = tar.extractfile(member)
            if handle is None:
                continue

            yield from handle.read().decode("utf-8", "replace").splitlines()


def parse_roleset(line: str, pos: str) -> tuple[str, str] | None:
    """Extract the (verb, sense) pair from a single ``.prop`` line.

    Parameters
    ----------
    line
        A whitespace-delimited PropBank proposition line.
    pos
        Predicate part-of-speech tag to keep (e.g. ``"v"``), or ``"all"`` to
        keep every predicate regardless of tag.

    Returns
    -------
    tuple of (str, str) or None
        The ``(verb, sense)`` pair, or ``None`` if the line should be skipped.
    """
    fields = line.split()

    # Expected layout: docid sent tok gold lemma-pos roleset ----- args...
    if len(fields) < 6:
        return None

    lemma_pos = fields[4]
    roleset = fields[5]

    # The predicate tag is the suffix after the final hyphen, e.g. "have-v".
    if pos != "all" and (
        "-" not in lemma_pos or lemma_pos.rsplit("-", 1)[1] != pos
    ):
        return None

    match = ROLESET_RE.match(roleset)
    if match is None:
        return None

    return match.group("verb"), roleset


def compute_distributions(
    archive: Path,
    language: str,
    pos: str,
) -> tuple[Counter[str], dict[str, Counter[str]], int]:
    """Tally sense counts across the archive.

    Parameters
    ----------
    archive
        Path to the OntoNotes ``.tgz`` file.
    language
        Language subtree to include, or ``"all"``.
    pos
        Predicate part-of-speech tag to keep, or ``"all"``.

    Returns
    -------
    sense_counts
        Counts keyed by full roleset (sense).
    verb_sense_counts
        Per-verb counts keyed by verb, then by roleset.
    total
        Total number of parsed predicate instances.
    """
    sense_counts: Counter[str] = Counter()
    verb_sense_counts: dict[str, Counter[str]] = defaultdict(Counter)
    total = 0

    for line in iter_prop_lines(archive, language):
        parsed = parse_roleset(line, pos)

        if parsed is None:
            continue

        verb, sense = parsed
        sense_counts[sense] += 1
        verb_sense_counts[verb][sense] += 1
        total += 1

    return sense_counts, verb_sense_counts, total


def write_csv(
    out_dir: Path,
    sense_counts: Counter[str],
    verb_sense_counts: dict[str, Counter[str]],
    total: int,
) -> Path:
    """Write the full distribution table to a CSV file.

    Parameters
    ----------
    out_dir
        Directory in which to create the CSV.
    sense_counts
        Counts keyed by full roleset.
    verb_sense_counts
        Per-verb counts keyed by verb, then by roleset.
    total
        Total number of parsed predicate instances.

    Returns
    -------
    Path
        The path to the written CSV file.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "propbank-sense-distribution.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["verb", "sense", "count", "logp_sense", "logp_sense_given_verb"])

        # Sort by verb, then by descending count within each verb.
        for verb in sorted(verb_sense_counts):
            verb_total = sum(verb_sense_counts[verb].values())

            for sense, count in verb_sense_counts[verb].most_common():
                # Counts are positive, so both logs are finite.
                logp_sense = math.log(count / total)
                logp_sense_given_verb = math.log(count / verb_total)
                writer.writerow([verb, sense, count, f"{logp_sense:.10g}", f"{logp_sense_given_verb:.10g}"])

    return path


def print_verb(
    verb: str,
    sense_counts: Counter[str],
    verb_sense_counts: dict[str, Counter[str]],
    total: int,
) -> None:
    """Print the sense distribution for a single verb.

    Parameters
    ----------
    verb
        The lemma to report.
    sense_counts
        Counts keyed by full roleset.
    verb_sense_counts
        Per-verb counts keyed by verb, then by roleset.
    total
        Total number of parsed predicate instances.
    """
    if verb not in verb_sense_counts:
        print(f"verb {verb!r} not found among {len(verb_sense_counts)} lemmas.")
        return

    counts = verb_sense_counts[verb]
    verb_total = sum(counts.values())

    print(f"\nverb: {verb}  (instances: {verb_total})")
    print(f"{'sense':<16}{'count':>8}{'logp(sense|verb)':>18}{'logp(sense)':>14}")
    print("-" * 56)

    for sense, count in counts.most_common():
        logp_cond = math.log(count / verb_total)
        logp_marg = math.log(sense_counts[sense] / total)
        print(f"{sense:<16}{count:>8}{logp_cond:>18.4f}{logp_marg:>14.4f}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Parameters
    ----------
    argv
        Argument list to parse, or ``None`` to read from ``sys.argv``.

    Returns
    -------
    argparse.Namespace
        The parsed arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE, help="path to the ontonotes .tgz")
    parser.add_argument("--language", default="english", help="language subtree to include, or 'all'")
    parser.add_argument("--pos", default="v", help="predicate pos tag to keep (e.g. 'v'), or 'all'")
    parser.add_argument("--verb", default=None, help="if given, print this verb's sense distribution")
    parser.add_argument("--out-dir", type=Path, default=REPO / "data",
                        help="directory for the output csv (default: data/)")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the distribution computation as a command-line program.

    Parameters
    ----------
    argv
        Argument list to parse, or ``None`` to read from ``sys.argv``.

    Returns
    -------
    int
        Process exit code.
    """
    args = parse_args(argv)

    if not args.archive.exists():
        print(f"archive not found: {args.archive}", file=sys.stderr)
        return 1

    print(f"scanning {args.archive.name} (language={args.language}, pos={args.pos}) ...", file=sys.stderr)
    sense_counts, verb_sense_counts, total = compute_distributions(args.archive, args.language, args.pos)

    print(
        f"parsed {total} predicate instances | "
        f"{len(sense_counts)} distinct senses | "
        f"{len(verb_sense_counts)} distinct verbs",
        file=sys.stderr,
    )

    if args.verb is not None:
        print_verb(args.verb, sense_counts, verb_sense_counts, total)

    if args.out_dir is not None:
        path = write_csv(args.out_dir, sense_counts, verb_sense_counts, total)
        print(f"wrote {path}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
