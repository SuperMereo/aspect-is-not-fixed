#!/usr/bin/env python3
"""Generate the Layers and chive records for White, Grimm, & Glass (2026).

Builds every ``pub.layers.*`` record describing the dataset of "Aspect is not a
fixed property of linguistic expressions" (ELM 4) and the ``pub.chive.*``
records describing the paper, from the tracked files in ``data/``,
``materials/experiment_text.json``, ``paper/``, and ``metadata/cache/``:

    cache/lexical_refs.json     scripts/resolve_lexical_refs.py (live Layers PDS)
    cache/*.csv                 scripts/export_fits.R (the paper's model fits)

Every record is validated against the generated lairs model for its lexicon
as it is built (``lairs`` 0.9.0, Layers lexicons 0.11.0), so the generator
refuses to write a record the lexicon rejects. ``scripts/check_metadata.py``
then re-validates everything strictly and checks references and counts.

All records live in ONE account, the DID in ``metadata/release.toml``. Each
AT-URI is ``at://<did>/<collection>/<rkey>`` with a deterministic rkey (the
first 24 hex of SHA-256 over the collection and a stable local id), so the
output is byte-identical across runs and a republish upserts in place.
Records referring to PropBank and VerbNet point at the DID-based AT-URIs of
the records in the Layers repository (repo.layers.pub) listed in
``cache/lexical_refs.json``; nothing from those resources is copied.

Output: ``metadata/layers/*.jsonl`` and ``metadata/chive/*.jsonl``, one record
per line as ``{"uri": ..., "value": {...}}``.

Usage (from metadata/):  .venv/bin/python scripts/generate_metadata.py
"""

from __future__ import annotations

import base64
import csv
import hashlib
import json
import re
import sys
import tomllib
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from lairs.records._generated import (
    acquisition,
    annotation,
    catalog,
    corpus,
    eprint,
    expression,
    graph,
    judgment,
    ontology,
    persona,
    resource,
)

META = Path(__file__).resolve().parent.parent
REPO = META.parent
DATA = REPO / "data"
CACHE = META / "cache"
PAPER = REPO / "paper"
OUT_LAYERS = META / "layers"
OUT_CHIVE = META / "chive"

CONFIG = tomllib.loads((META / "release.toml").read_text())
DID = CONFIG["account"]
if not re.fullmatch(r"did:(plc:[a-z2-7]{24}|web:[a-zA-Z0-9.:%-]+)", DID):
    sys.exit(f"release.toml: account {DID!r} is not a did:plc or did:web DID")

DATASET = "aspect-is-not-fixed"
CREATED_AT = "2026-11-21T00:00:00.000Z"   # fixed so the output is deterministic
REPO_URL = "https://github.com/SuperMereo/aspect-is-not-fixed"
INFO_SHEET = "http://factslab.io/information_sheet_021523.pdf"
TITLE = "Aspect is not a fixed property of linguistic expressions"

# Participant consent. Status is "granted" (participation required consent
# through the information sheet) and identifiability is "pseudonymous" (UUIDs
# whose re-identification map the authors hold privately; see data/README.md).
# Scope: participants agreed to public release of anonymized data, which is the
# lexicon's `public` scope (pub.layers.acquisition.defs#consent).
CONSENT_SCOPE = "public"

# Paper Table 1: manner/result pairs by semantic class (not in data/).
PAIRS = [
    ("Cleaning", [("wipe", "clear"), ("scrub", "clean")],
     "levin_wiping_1991"),
    ("Contact caused change", [("hit", "break"), ("jab", "shatter"),
                               ("bump", "chip"), ("kick", "split")],
     "fillmore_grammar_1970; levin_english_1993"),
    ("Contact caused motion", [("push", "open"), ("pull", "close"),
                               ("pound", "fold")],
     "fillmore_grammar_1970; levin2015semantics; levin2020resultatives"),
    ("Violence", [("stab", "kill"), ("shoot", "murder"), ("fight", "destroy")],
     "beavers_manner_2012; levin2015semantics"),
    ("Moving liquid", [("wash", "empty"), ("pour", "fill")],
     "levin_wiping_1991; levin2015semantics"),
    ("Moving substance", [("smear", "cover"), ("shake", "combine")],
     "gentner1978lexical; levin_wiping_1991; levin2015semantics"),
    ("Deliberating", [("consider", "conclude"), ("investigate", "discover"),
                      ("ponder", "decide"), ("debate", "prove")],
     "fillmore_frame_2006"),
]

# ---- NSIDs ------------------------------------------------------------------
C_ONT = "pub.layers.ontology.ontology"
C_TD = "pub.layers.ontology.typeDef"
C_CORPUS = "pub.layers.corpus.corpus"
C_CMEMB = "pub.layers.corpus.membership"
C_EXPR = "pub.layers.expression.expression"
C_LAYER = "pub.layers.annotation.annotationLayer"
C_CLUSTER = "pub.layers.annotation.clusterSet"
C_EDGE = "pub.layers.graph.graphEdge"
C_RCOLL = "pub.layers.resource.collection"
C_RENTRY = "pub.layers.resource.entry"
C_RMEMB = "pub.layers.resource.collectionMembership"
C_TMPL = "pub.layers.resource.template"
C_FILL = "pub.layers.resource.filling"
C_EXP = "pub.layers.judgment.experimentDef"
C_JSET = "pub.layers.judgment.judgmentSet"
C_AGREE = "pub.layers.judgment.agreementReport"
C_PART = "pub.layers.acquisition.participant"
C_PERSONA = "pub.layers.persona.persona"
C_EPRINT = "pub.layers.eprint.eprint"
C_DLINK = "pub.layers.eprint.dataLink"
C_CAT = "pub.layers.catalog.collection"
C_CATM = "pub.layers.catalog.membership"
C_SUB = "pub.chive.eprint.submission"
C_CIT = "pub.chive.eprint.citation"

MODELS = {
    C_ONT: ontology.Ontology, C_TD: ontology.TypeDef,
    C_CORPUS: corpus.Corpus, C_CMEMB: corpus.Membership,
    C_EXPR: expression.Expression, C_LAYER: annotation.AnnotationLayer,
    C_CLUSTER: annotation.ClusterSet, C_EDGE: graph.GraphEdge,
    C_RCOLL: resource.Collection, C_RENTRY: resource.Entry,
    C_RMEMB: resource.CollectionMembership, C_TMPL: resource.Template,
    C_FILL: resource.Filling, C_EXP: judgment.ExperimentDef,
    C_JSET: judgment.JudgmentSet, C_AGREE: judgment.AgreementReport,
    C_PART: acquisition.Participant, C_PERSONA: persona.Persona,
    C_EPRINT: eprint.Eprint, C_DLINK: eprint.DataLink,
    C_CAT: catalog.Collection, C_CATM: catalog.Membership,
}


# ---- identity ---------------------------------------------------------------
def rkey(collection: str, local_id: str) -> str:
    seed = f"{DATASET}|{collection}|{local_id}".encode()
    return hashlib.sha256(seed).hexdigest()[:24]


_B32S = "234567abcdefghijklmnopqrstuvwxyz"
_TID_EPOCH_US = int(datetime(2026, 11, 21, tzinfo=UTC).timestamp() * 1_000_000)


def tid(local_id: str, ordinal: int) -> str:
    """A deterministic, valid TID (chive records declare key=tid)."""
    clock = int(hashlib.sha256(local_id.encode()).hexdigest(), 16) % 1024
    n = ((_TID_EPOCH_US + ordinal) << 10) | clock
    return "".join(_B32S[(n >> (5 * i)) & 31] for i in reversed(range(13)))


def uri(collection: str, local_id: str) -> str:
    return f"at://{DID}/{collection}/{rkey(collection, local_id)}"


# ---- output -----------------------------------------------------------------
class Records:
    """Collects records per output file, validating each with lairs."""

    def __init__(self) -> None:
        self.files: dict[str, list[dict]] = defaultdict(list)
        self.seen: set[str] = set()

    def add(self, group: str, collection: str, local_id: str, value: dict,
            *, rk: str | None = None) -> str:
        at = (f"at://{DID}/{collection}/{rk}" if rk else uri(collection, local_id))
        if at in self.seen:
            sys.exit(f"duplicate record {at} ({local_id})")
        self.seen.add(at)
        value = {"$type": collection, **prune(value)}
        model = MODELS.get(collection)
        if model is not None:
            body = {k: v for k, v in value.items() if k != "$type"}
            try:
                model.model_validate_json(json.dumps(body))
            except Exception as exc:  # noqa: BLE001 - surface lairs' message
                sys.exit(f"lairs rejected {collection} {local_id}:\n{exc}")
        self.files[group].append({"uri": at, "value": value})
        return at

    def write(self) -> Counter:
        counts: Counter = Counter()
        for d in (OUT_LAYERS, OUT_CHIVE):
            d.mkdir(parents=True, exist_ok=True)
            for old in d.glob("*.jsonl"):
                old.unlink()
        for group, rows in self.files.items():
            out = (OUT_CHIVE if group.startswith("chive/") else OUT_LAYERS)
            name = group.removeprefix("chive/").replace("/", "-")
            path = out / f"{name}.jsonl"
            with path.open("w") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
                    counts[r["value"]["$type"]] += 1
        return counts


def prune(v):
    """Drop None / empty containers so optional fields are simply absent."""
    if isinstance(v, dict):
        out = {k: prune(x) for k, x in v.items()}
        return {k: x for k, x in out.items() if x not in (None, [], {}, "")}
    if isinstance(v, list):
        return [prune(x) for x in v if x is not None]
    return v


def fmap(d: dict) -> dict | None:
    entries = [{"key": str(k), "value": str(v)} for k, v in d.items()
               if v is not None and v != ""]
    return {"entries": entries} if entries else None


def span(text: str, start_char: int = 0, end_char: int | None = None) -> dict:
    end_char = len(text) if end_char is None else end_char
    return {"textSpan": {
        "byteStart": len(text[:start_char].encode()),
        "byteEnd": len(text[:end_char].encode()),
        "charStart": start_char, "charEnd": end_char}}


def word_span(text: str, word: str, after: int = 0) -> tuple[int, int]:
    m = re.compile(rf"\b{re.escape(word)}\b").search(text, after)
    if not m:
        sys.exit(f"cannot locate {word!r} in {text!r}")
    return m.start(), m.end()


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="") as f:
        return list(csv.DictReader(f))


def read_cache(name: str) -> list[dict]:
    with (CACHE / name).open(newline="") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def roleset_id(label: str) -> str:
    return label.split(":", 1)[0].strip()


def truthy(s: str) -> bool:
    return s.strip().lower() == "true"


# ---- inputs -----------------------------------------------------------------
INV = read_csv("manner-result-sentences.csv")
VERBS = read_csv("manner-result-verbs.csv")
CLOZE = read_csv("data-cloze.csv")
PROP = read_csv("data-proportion.csv")
SIM = read_csv("data-similarity.csv")
DIST = read_csv("propbank-sense-distribution.csv")
EXP_TEXT = json.loads((REPO / "materials" / "experiment_text.json").read_text())
LEX = json.loads((CACHE / "lexical_refs.json").read_text())
SENT_M = {r["sentence"]: r for r in read_cache("sentence_measures.csv")}
PAIR_M = {(r["sentence1"], r["sentence2"]): r for r in read_cache("pair_measures.csv")}
FITP = read_cache("fit_parameters.csv")
SPROP = read_cache("sense_proportions.csv")
SWEIGHT = read_cache("sense_weights.csv")

VERB_TYPE = {}
for r in INV:  # the inventory and every trial file agree; see README on 'cover'
    VERB_TYPE.setdefault(r["verb"], r["verb_type"])
VERB_TYPE_VERBS_CSV = {r["verb"]: r["verb_type"] for r in VERBS}
VERB_PAST = {r["verb"]: r["verb_past"] for r in VERBS}
SEM_CLASS, PARTNER, CLASS_SOURCE = {}, {}, {}
for cls, pairs, src in PAIRS:
    for m, r in pairs:
        SEM_CLASS[m] = SEM_CLASS[r] = cls
        PARTNER[m], PARTNER[r] = r, m
        CLASS_SOURCE[cls] = src
assert set(SEM_CLASS) == set(VERB_TYPE), "paper Table 1 and data disagree on verbs"

PB_ONTOLOGY = LEX["propbankOntology"]
VN_ONTOLOGY = LEX["verbnetOntology"]
ROLESETS = LEX["rolesets"]

UNITS_PLURAL = EXP_TEXT["cloze_duration_choices_plural"]
UNITS_SINGULAR = dict(zip(UNITS_PLURAL, EXP_TEXT["cloze_duration_choices_singular"],
                          strict=True))

LANG = ["en"]
LANG_REFS = [{"tag": "en", "knowledgeRef": {"source": "iso639-3", "identifier": "eng"}}]

R = Records()

# ---- shared blocks ------------------------------------------------------------
LIC_DATA = {"licenses": [{
    "spdx": "CC-BY-SA-4.0",
    "name": "Creative Commons Attribution-ShareAlike 4.0 International",
    "url": "https://creativecommons.org/licenses/by-sa/4.0/",
    "attribution": "White, A. S., Grimm, S., & Glass, L. (2026). " + TITLE + ".",
    "appliesTo": "whole"}]}
LIC_CATALOG = {"expression": "CC-BY-SA-4.0 AND MIT", "licenses": [
    {**LIC_DATA["licenses"][0], "appliesTo": "derived-data",
     "notes": "Stimuli, trial-level data, annotations, and derived measures (data/LICENSE)."},
    {"spdx": "MIT", "name": "MIT License", "appliesTo": "code",
     "url": REPO_URL + "/blob/main/LICENSE",
     "notes": "Experiment code, analysis pipeline, and these metadata scripts (LICENSE)."}]}
LIC_ONTONOTES = {"expression": "CC-BY-SA-4.0", "licenses": [{
    **LIC_DATA["licenses"][0], "appliesTo": "derived-data",
    "notes": ("Aggregate per-verb roleset counts derived from OntoNotes 5.0 "
              "(LDC2013T19). OntoNotes itself is licensed under the LDC User "
              "Agreement and is not redistributed; only these counts are.")}]}


def repro(name: str, command: str, **extra) -> dict:
    return {"codeUri": REPO_URL, "name": name, "command": command,
            "environment": "docker/ (pinned analysis image); metadata/requirements.lock",
            **extra}


REPRO_META = repro("aspect-is-not-fixed Layers metadata", "cd metadata && "
                   ".venv/bin/python scripts/generate_metadata.py", version="1.0.0")
REPRO_FITS = repro("analysis/reproduce.ipynb + metadata/scripts/export_fits.R",
                   "analysis/reproduce.ipynb (docker/), then Rscript "
                   "metadata/scripts/export_fits.R", randomSeed=2030491)
FIT_TOOL = "brms + cmdstanr (analysis/reproduce.ipynb, analysis/src/latent_senses.R)"
FIT_LINK = {f: f"at://{DID}/pub.layers.eprint.dataLink/{rkey('pub.layers.eprint.dataLink', f'datalink/fit/{f}')}"
            for f in ("cloze", "proportion", "similarity")}
FIT_DEPS = [{"recordRef": FIT_LINK["cloze"]}, {"recordRef": FIT_LINK["proportion"]}]

# ============================================================================
# Paper: chive submission + citations, Layers eprint
# ============================================================================
SUB_RKEY = tid("submission", 0)
SUB_URI = f"at://{DID}/{C_SUB}/{SUB_RKEY}"
EPRINT_URI = uri(C_EPRINT, "paper")
CORPUS_URI = uri(C_CORPUS, "corpus")
ONT_URI = uri(C_ONT, "ontology")
PERSONA_URI = uri(C_PERSONA, "prolific-participant")
ROOT_URI = uri(C_CAT, "root")

ABSTRACT = re.sub(r"\s+", " ", (PAPER / "sections" / "abstract.tex").read_text()
                  .replace("---", "—")).strip()
AUTHORS = [("Aaron Steven", "White", "University of Rochester", "0000-0003-0057-9246"),
           ("Scott", "Grimm", "University of Rochester", "0000-0002-0358-5038"),
           ("Lelia", "Glass", "Georgia Institute of Technology", "0000-0003-0428-7785")]
CITE_RAW = ("White, A. S., Grimm, S., & Glass, L. (2026). " + TITLE +
            ". In Proceedings of Experiments in Linguistic Meaning (ELM 4).")


def pdf_blob(path: Path) -> dict:
    data = path.read_bytes()
    cid = bytes([0x01, 0x55, 0x12, 0x20]) + hashlib.sha256(data).digest()
    return {"$type": "blob",
            "ref": {"$link": "b" + base64.b32encode(cid).decode().rstrip("=").lower()},
            "mimeType": "application/pdf", "size": len(data)}


R.add("chive/submission", C_SUB, "submission", {
    "title": TITLE,
    "titleRich": [{"$type": "pub.chive.richtext.defs#textItem", "type": "text", "content": TITLE}],
    "abstract": [{"$type": "pub.chive.richtext.defs#textItem", "type": "text", "content": ABSTRACT}],
    "abstractPlainText": ABSTRACT,
    "document": pdf_blob(PAPER / "main.pdf"),
    "documentFormatSlug": "pdf",
    "authors": [{"name": f"{g} {f}", "order": i + 1, "orcid": o,
                 "affiliations": [{"name": a}],
                 **({"isCorrespondingAuthor": True} if i == 0 else {})}
                for i, (g, f, a, o) in enumerate(AUTHORS)],
    "submittedBy": DID,
    "keywords": ["lexical aspect", "telicity", "durativity", "verb sense",
                 "PropBank", "manner/result verbs", "similarity judgments",
                 "cloze task", "Bayesian mixed-effects models", "experimental semantics"],
    "licenseSlug": "CC-BY-SA-4.0", "paperTypeSlug": "original-research",
    "publicationStatusSlug": "preprint",
    "conferencePresentation": {"conferenceName": "Experiments in Linguistic Meaning",
                               "conferenceAcronym": "ELM",
                               "conferenceIteration": "ELM 4 (2026)"},
    "repositories": {
        "code": [{"url": REPO_URL, "platformSlug": "github",
                  "label": "Data, materials, and analysis pipeline"}],
        "data": [{"url": REPO_URL + "/tree/main/data", "recordUri": ROOT_URI,
                  "label": "Stimuli and trial-level data (Layers catalog collection)",
                  "accessStatement": "CC-BY-SA-4.0. Raw experiment-platform dumps are not "
                                     "redistributed (they carry platform identifiers)."}]},
    "createdAt": CREATED_AT,
}, rk=SUB_RKEY)


def parse_bib(text: str) -> list[dict]:
    out = []
    for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", text):
        depth, i = 1, m.end()
        while i < len(text) and depth > 0:
            depth += (text[i] == "{") - (text[i] == "}")
            i += 1
        body = text[m.end():i - 1]
        fields = {"kind": m.group(1).lower(), "key": m.group(2)}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}\s*,?", body):
            fields[fm.group(1).lower()] = re.sub(r"\s+", " ", fm.group(2)).strip()
        out.append(fields)
    return out


def detex(s: str) -> str:
    return re.sub(r"[{}]", "", s).replace("\\&", "&").replace("--", "–")


BIB = parse_bib((PAPER / "references.bib").read_text())
for i, e in enumerate(BIB, start=1):
    cited = {"title": detex(e.get("title") or e["key"])[:1000]}
    if e.get("doi"):
        cited["doi"] = e["doi"][:200]
    if e.get("year") and re.search(r"\d{4}", e["year"]):
        cited["year"] = int(re.search(r"\d{4}", e["year"]).group())
    for v in ("journal", "booktitle", "publisher"):
        if e.get(v):
            cited["venue"] = detex(e[v])[:500]
            break
    if e.get("url"):
        cited["url"] = e["url"][:1000]
    if e.get("author"):
        cited["authors"] = [detex(a.strip()) for a in re.split(r"\s+and\s+", e["author"])
                            if a.strip()][:50]
    R.add("chive/citations", C_CIT, f"citation/{e['key']}",
          {"eprintUri": SUB_URI, "citedWork": cited, "citationType": "cites",
           "createdAt": CREATED_AT}, rk=tid(f"citation/{e['key']}", i))

R.add("paper", C_EPRINT, "paper", {
    "eprintIdentifier": SUB_URI, "eprintIdentifierType": "at-uri",
    "platformEprintRefs": [SUB_URI],
    "linkType": "produced-by",
    "corpusRef": CORPUS_URI,
    "description": ("The paper that produced this dataset: three judgment experiments "
                    "(cloze, temporal-overlap proportion, pairwise similarity) on event "
                    "descriptions built around 40 English transitive verbs."),
    "citation": {
        "raw": CITE_RAW, "type": "paper-conference", "title": TITLE,
        "creators": [{"role": "author", "nameType": "personal", "family": f, "given": g,
                      "affiliation": a, "sequence": i + 1,
                      "knowledgeRef": {"source": "orcid", "identifier": o,
                                       "uri": f"https://orcid.org/{o}"}}
                     for i, (g, f, a, o) in enumerate(AUTHORS)],
        "containerTitle": "Proceedings of Experiments in Linguistic Meaning (ELM 4)",
        "issued": {"year": 2026}, "url": REPO_URL, "language": "en"},
    "createdAt": CREATED_AT,
})

# ============================================================================
# Vocabulary: one ontology + typeDefs for every attribute, measure, and kind
# ============================================================================
R.add("vocabulary", C_ONT, "ontology", {
    "name": "Aspect-is-not-fixed annotation vocabulary",
    "description": ("Design factors, annotation layers, derived measures, and custom kinds "
                    "used by the Layers release of White, Grimm, & Glass (2026). Verb "
                    "senses are not defined here: they point into the PropBank ontology in "
                    "the Layers repository (" + PB_ONTOLOGY + ")."),
    "version": "1.0.0", "domain": "scientific", "eprintRefs": [EPRINT_URI],
    "licensing": LIC_DATA, "languages": LANG, "createdAt": CREATED_AT,
})

TYPEDEFS = {
    # design factors
    "generality": ("attribute-type", "Generality",
                   "Position of an event description on the generality cline (paper §2.1): "
                   "contentful (specific nouns; picks out one sense), bleached (definite NPs "
                   "headed by general nouns such as 'person' and 'thing'), or templatic "
                   "('X verb-PAST Y'; compatible with any sense). Called 'contentfulness' "
                   "in the data files.", ["contentful", "bleached", "templatic"]),
    "concreteness": ("attribute-type", "Concreteness",
                     "Whether a (sub-)sense is read concretely or abstractly; a PropBank "
                     "roleset supporting both readings was split into two sub-senses "
                     "(e.g. hit.01-concrete, hit.01-abstract).", ["concrete", "abstract"]),
    "verb-type": ("attribute-type", "Verb type",
                  "Manner v. result classification of a verb (paper Table 1).",
                  ["manner", "result"]),
    "semantic-class": ("attribute-type", "Semantic class",
                       "Semantic field of a manner/result pair (paper Table 1).",
                       [c for c, _, _ in PAIRS]),
    "argument-head": ("entity-type", "Argument head",
                      "Head noun (or templatic placeholder X/Y) of a subject or object NP. "
                      "Annotations carry the grammatical function as their label and the "
                      "noun's number (plural) and countability (mass) as features.", None),
    "sentence-pair": ("entity-type", "Sentence pair",
                      "Two event descriptions sharing a verb, shown together on one "
                      "Experiment 2 trial (one per line).", None),
    "calibration-category": ("attribute-type", "Calibration category",
                             "Target similarity band of an Experiment 2 calibration pair "
                             "(pairs from Cao et al. 2024 whose normed ratings span the scale).",
                             ["very_similar", "somewhat_similar", "somewhat_different",
                              "very_different"]),
    "telicity": ("attribute-type", "Telicity (in/for cloze diagnostic)",
                 "Measured property of Experiment 1a: the preference for completing an event "
                 "description with a temporal modifier headed by 'in' v. 'for'.", None),
    "durativity": ("attribute-type", "Durativity (temporal-overlap diagnostic)",
                   "Measured property of Experiment 1b: what proportion of a temporal "
                   "modifier's span the described event is judged to occupy.", None),
    "modal-response-share": ("attribute-type", "Modal response share",
                             "Mean, over items, of the share of an item's responses that "
                             "fall on its most frequent response (paper §6).", None),
    # per-sentence measures (§4)
    "sentence-measures": ("attribute-type", "Per-sentence aspectual measures",
                          "Layer subkind: the three posterior-mean logits of paper §4 and "
                          "the time unit each sentence was evaluated at.", None),
    "cloze-logit": ("attribute-type", "Cloze in-logit",
                    "Posterior mean log-odds of choosing 'in' (Experiment 1a fit), for an "
                    "average participant and list, at numeral 1 and the sentence's "
                    "evaluation time unit, with the latent sense weights applied.", None),
    "overlap-in-logit": ("attribute-type", "Overlap logit under 'in'",
                         "Posterior mean log-odds of an overlap response under 'in' "
                         "(Experiment 1b fit), evaluated as for the cloze logit.", None),
    "overlap-for-logit": ("attribute-type", "Overlap logit under 'for'",
                          "Posterior mean log-odds of an overlap response under 'for' "
                          "(Experiment 1b fit), evaluated as for the cloze logit.", None),
    "evaluation-time-unit": ("attribute-type", "Evaluation time unit",
                             "Time unit at which a sentence's logits are evaluated: the mode "
                             "of a Gaussian KDE over its cloze durations in log-minutes, "
                             "snapped to the nearest (numeral=1, unit) duration (§4).",
                             UNITS_PLURAL),
    # per-pair measures (§4, §5)
    "pair-measures": ("attribute-type", "Per-pair measures",
                      "Layer subkind: aspectual match (overall and per logit) and the "
                      "same-sense probability of an Experiment 2 sentence pair.", None),
    "aspectual-match": ("attribute-type", "Aspectual match",
                        "Probability that a third sentence drawn uniformly from the other "
                        "materials does not lie between the two sentences on any of the "
                        "three logits, averaged over posterior draws (§4).", None),
    "match-cloze": ("attribute-type", "Aspectual match on the cloze logit alone", "§4.", None),
    "match-overlap-in": ("attribute-type", "Aspectual match on the overlap-in logit alone",
                         "§4.", None),
    "match-overlap-for": ("attribute-type", "Aspectual match on the overlap-for logit alone",
                          "§4.", None),
    "same-sense-probability": ("attribute-type", "Same-sense probability",
                               "Probability that the two sentences are interpreted under the "
                               "same PropBank roleset: the dot product of their sense weights "
                               "(concreteness marginalized), averaged over the posterior "
                               "draws of the Experiment 1b fit (§5.4).", None),
    "generality-pair": ("attribute-type", "Generality pair",
                        "Generality of the two members of an Experiment 2 pair.",
                        ["contentful-contentful", "contentful-bleached"]),
    # sense weights
    "sense-weight": ("attribute-type", "Latent sense weight",
                     "Posterior weight of one (roleset, concreteness) sense in a sentence's "
                     "multi-membership sense term (§2.4), per Experiment 1 fit.", None),
}
TD_URI = {k: uri(C_TD, f"typedef/{k}") for k in TYPEDEFS}
for k, (kind, name, gloss, allowed) in TYPEDEFS.items():
    R.add("vocabulary", C_TD, f"typedef/{k}", {
        "ontologyRef": ONT_URI, "name": name, "typeKind": kind, "gloss": gloss,
        "allowedValues": allowed, "createdAt": CREATED_AT})


# ============================================================================
# Lexical layer: verbs, sub-senses, and the OntoNotes sense distribution,
# pointing into PropBank and VerbNet in the Layers repository
# ============================================================================
def pb_ref(rid: str, label: str | None = None) -> dict:
    rs = ROLESETS.get(rid)
    ref = {"source": "propbank", "identifier": rid,
           "label": label or (f"PropBank {rid}: {rs['gloss']}" if rs else f"PropBank {rid}")}
    if rs:
        ref["uri"] = rs["uri"]
    return ref


def vn_ref(cls: dict) -> dict:
    return {"source": "verbnet", "identifier": cls["class"], "uri": cls["uri"],
            "label": f"VerbNet {cls['class']}"}


VERB_COLL = R.add("lexicon", C_RCOLL, "collection/verbs", {
    "name": "Verb inventory",
    "description": ("The 40 English transitive verbs of the study, 20 manner/result pairs "
                    "across seven semantic classes (data/manner-result-verbs.csv; paper "
                    "Table 1). Each entry points at its PropBank lemma entry, its PropBank "
                    "rolesets, and its VerbNet class memberships in the Layers repository."),
    "kind": "lexicon", "version": "1.0.0", "ontologyRef": ONT_URI,
    "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
    "languages": LANG, "languageRefs": LANG_REFS, "createdAt": CREATED_AT})

VERB_URI = {}
EDGE_N = 0
for i, v in enumerate(VERBS):
    verb = v["verb"]
    lx = LEX["verbs"][verb]
    krefs = [{"source": "propbank", "identifier": verb,
              "uri": lx["propbankLemmaEntry"]["uri"], "label": f"PropBank lemma {verb}"}]
    krefs += [pb_ref(r) for r in lx["rolesets"]]
    seen_cls = {}
    for m in lx["verbnetMembers"]:
        if m["class"] and m["classUri"] not in seen_cls:
            seen_cls[m["classUri"]] = {"class": m["class"], "uri": m["classUri"]}
    krefs += [vn_ref(c) for c in seen_cls.values()]
    feats = {"verb_past": v["verb_past"], "verb_type": VERB_TYPE[verb],
             "semantic_class": SEM_CLASS[verb], "pair_partner": PARTNER[verb],
             "class_source": CLASS_SOURCE[SEM_CLASS[verb]],
             "propbank_rolesets": " ".join(lx["rolesets"]),
             "verbnet_classes": " ".join(c["class"] for c in seen_cls.values())}
    if VERB_TYPE_VERBS_CSV[verb] != VERB_TYPE[verb]:
        feats["verb_type_in_manner_result_verbs_csv"] = VERB_TYPE_VERBS_CSV[verb]
    VERB_URI[verb] = R.add("lexicon", C_RENTRY, f"verb/{verb}", {
        "lemma": verb, "form": verb, "knowledgeRefs": krefs[:32], "features": fmap(feats),
        "languages": LANG, "createdAt": CREATED_AT})
    if len(krefs) > 32:
        sys.exit(f"{verb}: more than 32 knowledgeRefs")
    R.add("lexicon", C_RMEMB, f"verb-membership/{verb}", {
        "collectionRef": VERB_COLL, "entryRef": VERB_URI[verb], "ordinal": i,
        "createdAt": CREATED_AT})
    # typed cross-repository edges (recordRefs into the PropBank/VerbNet accounts)
    lemma = lx["propbankLemmaEntry"]
    R.add("lexical-links", C_EDGE, f"edge/verb-propbank/{verb}", {
        "source": {"recordRef": VERB_URI[verb]}, "target": {"recordRef": lemma["uri"]},
        "edgeType": "same-as", "label": "PropBank lemma entry",
        "properties": fmap({"targetCid": lemma["cid"], "resource": "PropBank 3.4 frames"}),
        "createdAt": CREATED_AT})
    for m in lx["verbnetMembers"]:
        R.add("lexical-links", C_EDGE, f"edge/verb-verbnet/{verb}/{m['uri']}", {
            "source": {"recordRef": VERB_URI[verb]}, "target": {"recordRef": m["uri"]},
            "edgeType": "related-to", "label": "VerbNet member entry for this lemma",
            "properties": fmap({"targetCid": m["cid"], "verbnetClass": m["class"],
                                "verbnetClassUri": m["classUri"],
                                "resource": "VerbNet 3.4"}),
            "createdAt": CREATED_AT})

# manner/result pairs (paper Table 1)
R.add("lexicon", C_CLUSTER, "clusters/verb-pairs", {
    "kind": "clustering",
    "clusters": [{"uuid": {"value": f"pair-{m}-{r}"}, "canonicalLabel": f"{m}/{r}",
                  "members": [{"recordRef": VERB_URI[m]}, {"recordRef": VERB_URI[r]}],
                  "features": fmap({"semantic_class": cls, "manner": m, "result": r,
                                    "sources": src})}
                 for cls, pairs, src in PAIRS for m, r in pairs],
    "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA, "createdAt": CREATED_AT})

# sub-senses: (roleset, concreteness) combinations instantiated by the stimuli
SUBSENSES = sorted({(r["verb"], roleset_id(r["propbank_sense"]), r["concreteness"],
                     r["propbank_sense"]) for r in INV})
SENSE_COLL = R.add("lexicon", C_RCOLL, "collection/senses", {
    "name": "Verb sense inventory (PropBank roleset x concreteness)",
    "description": ("The 83 senses the stimuli instantiate: transitive PropBank rolesets of "
                    "the 40 verbs (62 rolesets, idiomatic senses and senses favoring non-"
                    "'the' determiners set aside), split into concrete and abstract sub-"
                    "senses where both readings were available (paper §2.1). Each entry's "
                    "ontologyTypeRef is the roleset's typeDef in the Layers PropBank "
                    "ontology; its features carry the posterior p(sense | verb) of both "
                    "Experiment 1 fits."),
    "kind": "frame-inventory", "version": "PropBank 3.4 rolesets", "ontologyRef": PB_ONTOLOGY,
    "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
    "languages": LANG, "createdAt": CREATED_AT})
SENSE_URI = {}
SPROP_BY = defaultdict(dict)
for r in SPROP:
    SPROP_BY[(r["verb"], r["roleset"], r["concreteness"])][r["fit"]] = r
for i, (verb, rid, conc, label) in enumerate(SUBSENSES):
    rs = ROLESETS[rid]
    feats = {"roleset": rid, "concreteness": conc, "sense_label_in_data": label,
             "propbank_gloss": rs["gloss"], "roleset_cid": rs["cid"]}
    for fit, p in sorted(SPROP_BY[(verb, rid, conc)].items()):
        feats[f"p_sense_given_verb.{fit}_fit.mean"] = p["mean"]
        feats[f"p_sense_given_verb.{fit}_fit.q2.5"] = p["q2.5"]
        feats[f"p_sense_given_verb.{fit}_fit.q97.5"] = p["q97.5"]
    krefs = [pb_ref(rid)] + [vn_ref(c) for c in rs.get("verbnetClasses", [])]
    SENSE_URI[(rid, conc)] = R.add("lexicon", C_RENTRY, f"sense/{rid}/{conc}", {
        "lemma": verb, "form": f"{rid}-{conc}", "ontologyTypeRef": rs["uri"],
        "knowledgeRefs": krefs[:32], "features": fmap(feats),
        "languages": LANG, "createdAt": CREATED_AT})
    R.add("lexicon", C_RMEMB, f"sense-membership/{rid}/{conc}", {
        "collectionRef": SENSE_COLL, "entryRef": SENSE_URI[(rid, conc)], "ordinal": i,
        "createdAt": CREATED_AT})

# OntoNotes 5.0 roleset distribution (data/propbank-sense-distribution.csv)
DIST_COLL = R.add("sense-distribution", C_RCOLL, "collection/ontonotes-distribution", {
    "name": "OntoNotes 5.0 PropBank roleset distribution",
    "description": ("Per-verb counts of PropBank rolesets in the English portion of OntoNotes "
                    "5.0 (Weischedel et al. 2013), one entry per (verb, roleset) row of "
                    "data/propbank-sense-distribution.csv, with the raw count and the log "
                    "marginal and verb-conditional probabilities as features. These counts "
                    "weight the multi-membership sense term (§2.4) and the same-sense "
                    "predictor (§5.4). Where the roleset still exists in the PropBank 3.4 "
                    "frames, ontologyTypeRef points at its typeDef in the Layers PropBank "
                    "ontology; OntoNotes rolesets retired before PropBank 3.4 carry only a "
                    "knowledgeRef with the OntoNotes roleset id."),
    "kind": "frame-inventory", "version": "OntoNotes 5.0 (LDC2013T19)",
    "ontologyRef": PB_ONTOLOGY,
    "knowledgeRefs": [{"source": "ldc", "identifier": "LDC2013T19",
                       "label": "OntoNotes Release 5.0",
                       "uri": "https://catalog.ldc.upenn.edu/LDC2013T19"}],
    "eprintRefs": [EPRINT_URI], "licensing": LIC_ONTONOTES,
    "metadata": {"tool": "data/scripts/make_propbank_sense_distribution.py "
                         "(ONTONOTES_ARCHIVE=<LDC2013T19 tarball>)"},
    "languages": LANG, "createdAt": CREATED_AT})
for i, r in enumerate(DIST):
    rid = r["sense"]
    resolved = rid in ROLESETS
    e = R.add("sense-distribution", C_RENTRY, f"distribution/{r['verb']}/{rid}", {
        "lemma": r["verb"], "form": rid,
        "ontologyTypeRef": ROLESETS[rid]["uri"] if resolved else None,
        "knowledgeRefs": [pb_ref(rid) if resolved else
                          {"source": "propbank", "identifier": rid,
                           "label": f"OntoNotes 5.0 roleset {rid} (not in the PropBank 3.4 "
                                    "frames in the Layers repository)"}],
        "features": fmap({"count": r["count"], "logp_sense": r["logp_sense"],
                          "logp_sense_given_verb": r["logp_sense_given_verb"],
                          "in_propbank_3_4": str(resolved).lower()}),
        "languages": LANG, "createdAt": CREATED_AT})
    R.add("sense-distribution", C_RMEMB, f"distribution-membership/{r['verb']}/{rid}", {
        "collectionRef": DIST_COLL, "entryRef": e, "ordinal": i, "createdAt": CREATED_AT})

# ============================================================================
# Corpus: the 312 event descriptions
# ============================================================================
SENTENCES = {}   # text -> dict(verb, generality, rows)
for idx, r in enumerate(INV):
    for gen, col in (("contentful", "sentence_contentful_episodic"),
                     ("bleached", "sentence_bleached_episodic"),
                     ("templatic", "sentence_templatic_episodic")):
        s = SENTENCES.setdefault(r[col], {"verb": r["verb"], "generality": gen, "rows": []})
        assert s["verb"] == r["verb"] and s["generality"] == gen
        s["rows"].append(idx)
assert len(SENTENCES) == 312, len(SENTENCES)
SENT_ORDER = sorted(SENTENCES)   # the analysis numbers sentences in sorted order too


def sent_uri(text: str) -> str:
    return uri(C_EXPR, f"sentence/{text}")


def sense_set(text: str) -> list[tuple[str, str, str]]:
    """(roleset, concreteness, data label) the sentence is assigned/compatible with."""
    s = SENTENCES[text]
    if s["generality"] == "templatic":
        rows = [r for r in INV if r["verb"] == s["verb"]]
    else:
        rows = [INV[i] for i in s["rows"]]
    return sorted({(roleset_id(r["propbank_sense"]), r["concreteness"], r["propbank_sense"])
                   for r in rows})


for text in SENT_ORDER:
    s = SENTENCES[text]
    feats = {"verb": s["verb"], "verb_type": VERB_TYPE[s["verb"]],
             "generality": s["generality"], "clause_type": "episodic",
             "inventory_rows": " ".join(str(i + 2) for i in s["rows"])}
    if s["generality"] == "contentful":
        row = INV[s["rows"][0]]
        feats |= {"propbank_sense": row["propbank_sense"], "roleset": roleset_id(row["propbank_sense"]),
                  "concreteness": row["concreteness"]}
    R.add("corpus/sentences", C_EXPR, f"sentence/{text}", {
        "id": f"{s['generality']}:{text}", "kind": "sentence", "text": text,
        "features": fmap(feats), "eprintRefs": [EPRINT_URI],
        "languages": LANG, "languageRefs": LANG_REFS, "createdAt": CREATED_AT})

# bleached <- contentful construction edges (one per inventory row)
for idx, r in enumerate(INV):
    R.add("corpus/derivation-edges", C_EDGE, f"edge/bleached-from/{idx}", {
        "source": {"recordRef": sent_uri(r["sentence_bleached_episodic"])},
        "target": {"recordRef": sent_uri(r["sentence_contentful_episodic"])},
        "edgeType": "derived-from",
        "label": "bleached counterpart constructed from this contentful sentence",
        "properties": fmap({"roleset": roleset_id(r["propbank_sense"]),
                            "concreteness": r["concreteness"],
                            "inventory_row": idx + 2}),
        "createdAt": CREATED_AT})
for verb in sorted(VERB_URI):
    t = next(r["sentence_templatic_episodic"] for r in INV if r["verb"] == verb)
    R.add("corpus/derivation-edges", C_EDGE, f"edge/templatic-from/{verb}", {
        "source": {"recordRef": sent_uri(t)}, "target": {"recordRef": VERB_URI[verb]},
        "edgeType": "derived-from",
        "label": "templatic 'X verb-PAST Y' item generated from the verb (Kane et al. 2022)",
        "createdAt": CREATED_AT})


# ---- per-sentence annotation layers -------------------------------------------
def verb_char_span(text: str, verb: str) -> tuple[int, int]:
    past = VERB_PAST[verb]
    return word_span(text, past)


NOUN_COLS = {
    "contentful": ("subject_noun_contentful", "object_noun_contentful",
                   "subject_noun_contentful_plural", "object_noun_contentful_plural",
                   "subject_noun_contentful_mass", "object_noun_contentful_mass"),
    "bleached": ("subject_noun_bleached", "object_noun_bleached",
                 "subject_noun_bleached_plural", "object_noun_bleached_plural",
                 "subject_noun_bleached_mass", "object_noun_bleached_mass"),
}
WEIGHTS = defaultdict(list)
for w in SWEIGHT:
    WEIGHTS[w["sentence"]].append(w)
SENSE_LAYER = {}
for text in SENT_ORDER:
    s = SENTENCES[text]
    e_uri = sent_uri(text)
    vs, ve = verb_char_span(text, s["verb"])
    # (1) PropBank sense: assigned (contentful) or compatible (bleached, templatic)
    relation = {"contentful": "assigned", "bleached": "compatible: senses of the contentful "
                "sentences this item was constructed from",
                "templatic": "compatible: every stimulus sense of the verb"}[s["generality"]]
    anns = []
    for rid, conc, label in sense_set(text):
        anns.append({
            "uuid": {"value": f"sense-{rid}-{conc}"}, "anchor": span(text, vs, ve),
            "text": text[vs:ve], "label": rid, "value": f"{rid}-{conc}",
            "ontologyTypeRef": ROLESETS[rid]["uri"], "knowledgeRefs": [pb_ref(rid)],
            "features": fmap({"concreteness": conc, "relation": relation.split(":")[0],
                              "sense_label_in_data": label,
                              "sense_entry": SENSE_URI[(rid, conc)]})})
    SENSE_LAYER[text] = R.add("annotations/sense", C_LAYER, f"layer/sense/{text}", {
        "expression": e_uri, "kind": "span", "subkind": "sense", "formalism": "propbank",
        "sourceMethod": "manual-native", "labelSet": "propbank-3.4-rolesets x concreteness",
        "ontologyRef": PB_ONTOLOGY, "annotations": anns,
        "metadata": {"tool": "hand annotation (data/manner-result-sentences.csv)",
                     "personaRef": None},
        "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
        "languages": LANG, "createdAt": CREATED_AT})
    # (2) argument heads (subject / object) with number and countability
    if s["generality"] == "templatic":
        heads = [("subject", "X", None, None), ("object", "Y", None, None)]
    else:
        row = INV[s["rows"][0]]
        sn, on, sp, op, sm, om = (row[c] for c in NOUN_COLS[s["generality"]])
        for i in s["rows"][1:]:
            assert tuple(INV[i][c] for c in NOUN_COLS[s["generality"]]) == (sn, on, sp, op, sm, om)
        heads = [("subject", sn, sp, sm), ("object", on, op, om)]
    anns, pos = [], 0
    for fn, noun, plural, mass in heads:
        a, b = word_span(text, noun, ve if fn == "object" else pos)
        pos = b
        anns.append({
            "uuid": {"value": f"arg-{fn}"}, "anchor": span(text, a, b), "text": text[a:b],
            "label": fn, "value": noun, "ontologyTypeRef": TD_URI["argument-head"],
            "features": fmap({"plural": plural and str(truthy(plural)).lower(),
                              "mass": mass and str(truthy(mass)).lower(),
                              "placeholder": "true" if s["generality"] == "templatic" else None})})
    R.add("annotations/arguments", C_LAYER, f"layer/arguments/{text}", {
        "expression": e_uri, "kind": "span", "subkind": "argument-head",
        "subkindUri": TD_URI["argument-head"], "sourceMethod": "manual-native",
        "ontologyRef": ONT_URI, "annotations": anns,
        "metadata": {"tool": "hand annotation (data/manner-result-sentences.csv)"},
        "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
        "languages": LANG, "createdAt": CREATED_AT})
    # (3) derived per-sentence measures (§4)
    m = SENT_M[text]
    assert m["verb"] == s["verb"] and m["generality"] == s["generality"]
    full = span(text)
    anns = [{"uuid": {"value": k}, "anchor": full, "label": k, "value": m[col],
             "ontologyTypeRef": TD_URI[k]}
            for k, col in (("cloze-logit", "cloze"), ("overlap-in-logit", "overlap_in"),
                           ("overlap-for-logit", "overlap_for"),
                           ("evaluation-time-unit", "eval_time_unit"))]
    R.add("annotations/sentence-measures", C_LAYER, f"layer/measures/{text}", {
        "expression": e_uri, "kind": "document-tag", "subkind": "sentence-measures",
        "subkindUri": TD_URI["sentence-measures"], "sourceMethod": "automatic",
        "ontologyRef": ONT_URI, "annotations": anns,
        "metadata": {"tool": FIT_TOOL, "dependencies": FIT_DEPS},
        "eprintRefs": [EPRINT_URI], "reproducibility": REPRO_FITS, "licensing": LIC_DATA,
        "languages": LANG, "createdAt": CREATED_AT})
    # (4) latent sense weights, per Experiment 1 fit
    anns = []
    for w in sorted(WEIGHTS[text], key=lambda w: (w["fit"], w["roleset"], w["concreteness"])):
        anns.append({
            "uuid": {"value": f"weight-{w['fit']}-{w['roleset']}-{w['concreteness']}"},
            "anchor": span(text, vs, ve), "text": text[vs:ve], "label": w["roleset"],
            "value": w["mean"], "ontologyTypeRef": ROLESETS[w["roleset"]]["uri"],
            "features": fmap({"fit": w["fit"], "concreteness": w["concreteness"],
                              "q2.5": w["q2.5"], "q97.5": w["q97.5"],
                              "measure": TD_URI["sense-weight"]})})
    R.add("annotations/sense-weights", C_LAYER, f"layer/sense-weights/{text}", {
        "expression": e_uri, "kind": "span", "subkind": "sense", "formalism": "propbank",
        "sourceMethod": "automatic", "labelSet": "posterior sense weights (Wt)",
        "ontologyRef": PB_ONTOLOGY, "parentLayerRef": SENSE_LAYER[text], "annotations": anns,
        "metadata": {"tool": FIT_TOOL, "dependencies": FIT_DEPS}, "eprintRefs": [EPRINT_URI],
        "reproducibility": REPRO_FITS, "licensing": LIC_DATA,
        "languages": LANG, "createdAt": CREATED_AT})

# ============================================================================
# Stimulus pools (resource collections that template slots draw from)
# ============================================================================
def pool(local: str, name: str, description: str, entries: list[tuple[str, dict, dict]]):
    coll = R.add("stimulus-pools", C_RCOLL, f"pool/{local}", {
        "name": name, "description": description, "kind": "stimulus-pool",
        "version": "1.0.0", "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
        "languages": LANG, "createdAt": CREATED_AT})
    out = {}
    for i, (form, extra, feats) in enumerate(entries):
        e = R.add("stimulus-pools", C_RENTRY, f"pool/{local}/{form}", {
            "form": form, **extra, "features": fmap(feats),
            "languages": LANG, "createdAt": CREATED_AT})
        R.add("stimulus-pools", C_RMEMB, f"pool-membership/{local}/{form}", {
            "collectionRef": coll, "entryRef": e, "ordinal": i, "createdAt": CREATED_AT})
        out[form] = e
    return coll, out


EVENT_POOL, EVENT_ENTRY = pool(
    "events", "Event descriptions",
    "The 312 event descriptions, each an entry whose sourceRef is its expression; the "
    "event slot of every Experiment 1 template and both sentence slots of the Experiment 2 "
    "pair template draw from this pool (Experiment 2 uses its contentful and bleached items).",
    [(t, {"lemma": SENTENCES[t]["verb"], "sourceRef": sent_uri(t)},
      {"generality": SENTENCES[t]["generality"]}) for t in SENT_ORDER])
PREP_POOL, PREP_ENTRY = pool(
    "prepositions", "Temporal-modifier prepositions",
    "First cloze dropdown (Experiment 1a; a response) and the experimenter-fixed "
    "preposition of each Experiment 1b stimulus.",
    [(p, {"lemma": p}, {"pos": "preposition"}) for p in EXP_TEXT["cloze_preposition_choices"]])
NUMERAL_FORMS = EXP_TEXT["cloze_numeral_choices"]
NUM_POOL, NUM_ENTRY = pool(
    "numerals", "Numerals",
    "Second cloze dropdown (Experiment 1a), in display order; Experiment 1b numerals were "
    "fixed by the experimenters from the Experiment 1a responses.",
    [(n, {}, {"value": n.replace(",", "")}) for n in NUMERAL_FORMS])
NUM_BY_VALUE = {n.replace(",", ""): n for n in NUMERAL_FORMS}
UNIT_POOL, UNIT_ENTRY = pool(
    "time-units", "Time units",
    "Third cloze dropdown (Experiment 1a), in display order, with the plural form the "
    "dropdown shows and records ('millenia' is the deployed spelling) and the singular form "
    "Experiment 1b used with the numeral 1.",
    [(u, {"lemma": UNITS_SINGULAR[u]}, {"singular": UNITS_SINGULAR[u], "plural": u})
     for u in UNITS_PLURAL])

# ============================================================================
# Experiments, templates, fillings, materialized stimuli, judgments
# ============================================================================
PERSONA_TEXT = ("Self-identified native speakers of English located in the United States, "
                "recruited through Prolific (paper §2.3, §3.3, §5.2). Eligibility and "
                f"consent per the information sheet at {INFO_SHEET}. Fullscreen mode was "
                "required throughout. Average payment rate $14.31/hour (§2.3).")
R.add("participants", C_PERSONA, "prolific-participant", {
    "name": "Prolific participant (native English speaker, US)",
    "description": PERSONA_TEXT, "kind": "crowd-worker", "domain": "linguistics",
    "guidelines": PERSONA_TEXT, "guidelinesFormat": "plain",
    "features": fmap({"platform": "Prolific", "deployment": "JATOS 3.x + jsPsych 7.x",
                      "eligibility.native_language": "English (self-identified)",
                      "eligibility.location": "United States",
                      "payment.mean_rate_usd_per_hour": "14.31",
                      "consent.information_sheet": INFO_SHEET}),
    "createdAt": CREATED_AT})

# participants: one pseudonymous record per UUID across the three experiments
PARTICIPANTS = defaultdict(set)
for name, rows in (("1a", CLOZE), ("1b", PROP), ("2", SIM)):
    for r in rows:
        PARTICIPANTS[r["participant"]].add(name)
PART_URI = {}
for pid in sorted(PARTICIPANTS):
    PART_URI[pid] = R.add("participants", C_PART, f"participant/{pid}", {
        "participantId": pid, "species": "homo-sapiens",
        "languageProfiles": [{"language": {"tag": "en"},
                              "proficiency": "native",
                              "features": fmap({"basis": "self-identified (Prolific screener)"})}],
        "languages": LANG,
        "consent": {"status": "granted", "scope": CONSENT_SCOPE,
                    "identifiability": "pseudonymous",
                    "notes": (f"Consent via the information sheet {INFO_SHEET}, under which "
                              "participants agreed to public release of anonymized data. The participant "
                              "id is a UUID unrelated to the Prolific id; the map that "
                              "reverses it is held privately by the authors and is not "
                              "published (data/README.md).")},
        "features": fmap({"recruitment_platform": "Prolific",
                          "eligibility.location": "United States",
                          "experiments": ",".join(sorted(PARTICIPANTS[pid]))}),
        "metadata": {"tool": "data/scripts/anonymize.py (UUID pseudonyms)"},
        "createdAt": CREATED_AT})

EXP_URIS: dict[str, str] = {}
EXP_DEFS: dict[str, dict] = {}


def exp_local(exp: str, cond: str) -> str:
    return f"experiment/{exp}/{cond}"


def guidelines(html: str) -> str:
    return re.sub(r"\n\s*\n", "\n", html.strip())


# ---- Experiment 1a (cloze) -------------------------------------------------------
CLOZE_COND = {"contentful_episodic": "contentful", "bleached_episodic": "bleached",
              "templatic_episodic": "templatic"}
CLOZE_TMPL, CLOZE_FILL = {}, {}
for cond, gen in CLOZE_COND.items():
    e_uri = uri(C_EXP, exp_local("1a", gen))
    EXP_URIS[f"1a/{gen}"] = e_uri
    CLOZE_TMPL[gen] = R.add("experiments/templates", C_TMPL, f"template/1a/{gen}", {
        "name": f"Experiment 1a cloze frame ({gen})",
        "text": "{event} {preposition} {numeral} {time_unit}.",
        "slots": [
            {"name": "event", "required": True, "collectionRef": EVENT_POOL,
             "description": f"The {gen} event description without its final period; filled "
                            "by the experimenters."},
            {"name": "preposition", "required": True, "collectionRef": PREP_POOL,
             "description": "Dropdown 1, filled by the participant (the response analysed)."},
            {"name": "numeral", "required": True, "collectionRef": NUM_POOL,
             "description": "Dropdown 2, filled by the participant."},
            {"name": "time_unit", "required": True, "collectionRef": UNIT_POOL,
             "description": "Dropdown 3, filled by the participant."}],
        "experimentRef": e_uri, "ontologyRef": ONT_URI,
        "features": fmap({"response_slots": "preposition numeral time_unit",
                          "plugin": "materials/src/plugin-cloze-dropdown.ts"}),
        "languages": LANG, "createdAt": CREATED_AT})
for text in SENT_ORDER:
    gen = SENTENCES[text]["generality"]
    stem = text.rstrip(".")
    CLOZE_FILL[text] = R.add("experiments/fillings-1a", C_FILL, f"filling/1a/{text}", {
        "templateRef": CLOZE_TMPL[gen],
        "slotFillings": [{"slotName": "event", "entryRef": EVENT_ENTRY[text],
                          "renderedForm": stem}],
        "renderedText": f"{stem} ___ ___ ___.",
        "expressionRef": sent_uri(text), "strategy": "manual",
        "features": fmap({"note": "the three response slots are filled by the participant; "
                                  "each response is a judgment in a judgmentSet"}),
        "createdAt": CREATED_AT})

# ---- Experiment 1b (temporal-overlap proportion) -----------------------------------
PROP_TMPL = {}
for gen in ("contentful", "bleached", "templatic"):
    e_uri = uri(C_EXP, exp_local("1b", gen))
    EXP_URIS[f"1b/{gen}"] = e_uri
    PROP_TMPL[gen] = R.add("experiments/templates", C_TMPL, f"template/1b/{gen}", {
        "name": f"Experiment 1b stimulus frame ({gen})",
        "text": "{event} {preposition} {numeral} {time_unit}.",
        "slots": [
            {"name": "event", "required": True, "collectionRef": EVENT_POOL},
            {"name": "preposition", "required": True, "collectionRef": PREP_POOL},
            {"name": "numeral", "required": True, "collectionRef": NUM_POOL},
            {"name": "time_unit", "required": True, "collectionRef": UNIT_POOL,
             "description": "Singular with the numeral 1, plural otherwise."}],
        "experimentRef": e_uri, "ontologyRef": ONT_URI,
        "features": fmap({
            "question_template": "For what proportion of those {numeral} {time_unit} (if any) "
                                 "was {event-progressive}?",
            "note": "every slot is filled by the experimenters: the modal Experiment 1a "
                    "numeral x time unit for the sentence under each preposition (§3.1)"}),
        "languages": LANG, "createdAt": CREATED_AT})


def unit_form(numeral: str, unit: str) -> str:
    return UNITS_SINGULAR[unit] if numeral == "1" else unit


PROP_STIM = {}   # (sentence, prep, numeral, unit) -> (expression uri, filling uri)
for key in sorted({(r["sentence"], r["preposition"], r["numeral"], r["duration"]) for r in PROP}):
    text, prep, num, unit = key
    gen = SENTENCES[text]["generality"]
    rendered = f"{text.rstrip('.')} {prep} {num} {unit_form(num, unit)}."
    local = "|".join(key)
    ex = R.add("corpus/stimuli-1b", C_EXPR, f"stimulus-1b/{local}", {
        "id": f"exp1b:{local}", "kind": "sentence", "text": rendered,
        "parentRef": sent_uri(text),
        "features": fmap({"verb": SENTENCES[text]["verb"], "generality": gen,
                          "preposition": prep, "numeral": num, "time_unit": unit}),
        "eprintRefs": [EPRINT_URI], "languages": LANG, "createdAt": CREATED_AT})
    fi = R.add("experiments/fillings-1b", C_FILL, f"filling/1b/{local}", {
        "templateRef": PROP_TMPL[gen],
        "slotFillings": [
            {"slotName": "event", "entryRef": EVENT_ENTRY[text], "renderedForm": text.rstrip(".")},
            {"slotName": "preposition", "entryRef": PREP_ENTRY[prep], "renderedForm": prep},
            {"slotName": "numeral", "entryRef": NUM_ENTRY[NUM_BY_VALUE[num]], "renderedForm": num},
            {"slotName": "time_unit", "entryRef": UNIT_ENTRY[unit],
             "renderedForm": unit_form(num, unit)}],
        "renderedText": rendered, "expressionRef": ex, "strategy": "manual",
        "createdAt": CREATED_AT})
    PROP_STIM[key] = (ex, fi)

# ---- Experiment 2 (similarity) ---------------------------------------------------
EXP_URIS["2"] = uri(C_EXP, exp_local("2", "all"))
PAIR_TMPL = R.add("experiments/templates", C_TMPL, "template/2/pair", {
    "name": "Experiment 2 sentence pair",
    "text": "{sentence1}\n{sentence2}",
    "slots": [{"name": "sentence1", "required": True, "collectionRef": EVENT_POOL,
               "description": "First member of the pair as recorded in the data "
                              "(shown first when the trial's sentences_reversed is true, "
                              "second when it is false)."},
              {"name": "sentence2", "required": True, "collectionRef": EVENT_POOL,
               "description": "Second member; same verb as sentence1."}],
    "constraints": [{"expression": "sentence1.lemma == sentence2.lemma",
                     "expressionFormat": "python-expr", "context": ["sentence1", "sentence2"],
                     "description": "Both sentences share a verb."},
                    {"expression": "'templatic' not in (sentence1.features.generality, "
                                   "sentence2.features.generality)",
                     "expressionFormat": "python-expr", "context": ["sentence1", "sentence2"],
                     "description": "Pairs are contentful-contentful or contentful-bleached."}],
    "experimentRef": EXP_URIS["2"], "ontologyRef": ONT_URI,
    "languages": LANG, "createdAt": CREATED_AT})
CAL_TMPL = R.add("experiments/templates", C_TMPL, "template/2/calibration", {
    "name": "Experiment 2 calibration pair",
    "text": "{sentence1}\n{sentence2}",
    "slots": [{"name": "sentence1", "required": True}, {"name": "sentence2", "required": True}],
    "experimentRef": EXP_URIS["2"],
    "knowledgeRefs": [{"source": "doi", "identifier": "10.48550/arXiv.2412.18496",
                       "label": "Cao et al. (2024), source of the calibration pairs"}],
    "languages": LANG, "createdAt": CREATED_AT})


def pair_kind_fields() -> dict:
    return {"kind": "sentence-pair", "kindUri": TD_URI["sentence-pair"]}


PAIR = {}   # (s1, s2) -> (expression uri, filling uri)
# Pair-level columns of data-similarity.csv, verbatim (constant within a pair).
# propbank_sense{1,2} / concreteness{1,2} follow the sentence positions; for a
# bleached member they name the sense of the inventory row the pair was built
# from. contentfulness{1,2} follow the positions too; each member's generality
# is also given from its sentence record.
PAIR_COLS = ("verb_type", "contentfulness1", "contentfulness2", "propbank_sense1",
             "propbank_sense2", "concreteness1", "concreteness2")
PAIR_CSV = {}
for r in SIM:
    vals = tuple(r[c] for c in PAIR_COLS)
    assert PAIR_CSV.setdefault((r["sentence1"], r["sentence2"]), vals) == vals
test_pairs = sorted({(r["sentence1"], r["sentence2"]) for r in SIM if r["verb_type"] != "calibration"})
for s1, s2 in test_pairs:
    m = PAIR_M[(s1, s2)]
    gp = "-".join(sorted((SENTENCES[s1]["generality"], SENTENCES[s2]["generality"]),
                         key=["contentful", "bleached"].index))
    local = f"{s1}|{s2}"
    text = f"{s1}\n{s2}"
    ex = R.add("corpus/pairs-2", C_EXPR, f"pair/{local}", {
        "id": f"exp2:{local}", **pair_kind_fields(), "text": text,
        "features": fmap({"verb": m["verb"], "generality_pair": gp,
                          "sentence1": sent_uri(s1), "sentence2": sent_uri(s2),
                          "sentence1_generality": SENTENCES[s1]["generality"],
                          "sentence2_generality": SENTENCES[s2]["generality"],
                          **{f"csv.{c}": v for c, v in zip(PAIR_COLS, PAIR_CSV[(s1, s2)],
                                                            strict=True)}}),
        "eprintRefs": [EPRINT_URI], "languages": LANG, "createdAt": CREATED_AT})
    fi = R.add("experiments/fillings-2", C_FILL, f"filling/2/{local}", {
        "templateRef": PAIR_TMPL,
        "slotFillings": [{"slotName": "sentence1", "entryRef": EVENT_ENTRY[s1], "renderedForm": s1},
                         {"slotName": "sentence2", "entryRef": EVENT_ENTRY[s2], "renderedForm": s2}],
        "renderedText": text, "expressionRef": ex, "strategy": "manual",
        "createdAt": CREATED_AT})
    PAIR[(s1, s2)] = (ex, fi)
    anns = [{"uuid": {"value": k}, "anchor": span(text), "label": k, "value": m[col],
             "ontologyTypeRef": TD_URI[k]}
            for k, col in (("aspectual-match", "aspect_match"), ("match-cloze", "match_cloze"),
                           ("match-overlap-in", "match_overlap_in"),
                           ("match-overlap-for", "match_overlap_for"),
                           ("same-sense-probability", "p_same_sense"))]
    anns.append({"uuid": {"value": "generality-pair"}, "anchor": span(text),
                 "label": "generality-pair", "value": gp,
                 "ontologyTypeRef": TD_URI["generality-pair"]})
    R.add("annotations/pair-measures", C_LAYER, f"layer/pair-measures/{local}", {
        "expression": ex, "kind": "document-tag", "subkind": "pair-measures",
        "subkindUri": TD_URI["pair-measures"], "sourceMethod": "automatic",
        "ontologyRef": ONT_URI, "annotations": anns,
        "metadata": {"tool": FIT_TOOL, "dependencies": FIT_DEPS},
        "eprintRefs": [EPRINT_URI], "reproducibility": REPRO_FITS, "licensing": LIC_DATA,
        "languages": LANG, "createdAt": CREATED_AT})

CAL = {}
CAL_VERB = {(r["sentence1"], r["sentence2"]): r["verb"] for r in SIM if r["verb_type"] == "calibration"}
for item in EXP_TEXT["similarity_calibration_items"]:
    s1, s2 = item["sentence1"], item["sentence2"]
    category = item["item_id"].removeprefix("calibration_").rsplit("-", 1)[0]
    text = f"{s1}\n{s2}"
    ex = R.add("corpus/calibration-2", C_EXPR, f"calibration/{item['item_id']}", {
        "id": item["item_id"], **pair_kind_fields(), "text": text,
        "features": fmap({"purpose": "calibration", "verb": CAL_VERB[(s1, s2)],
                          **{f"csv.{c}": v for c, v in zip(PAIR_COLS, PAIR_CSV[(s1, s2)],
                                                            strict=True)},
                          "calibration_category": category,
                          "calibration_category_type": TD_URI["calibration-category"]}),
        "eprintRefs": [EPRINT_URI], "languages": LANG, "createdAt": CREATED_AT})
    fi = R.add("experiments/fillings-2", C_FILL, f"filling/2/calibration/{item['item_id']}", {
        "templateRef": CAL_TMPL,
        "slotFillings": [{"slotName": "sentence1", "literalValue": s1, "renderedForm": s1},
                         {"slotName": "sentence2", "literalValue": s2, "renderedForm": s2}],
        "renderedText": text, "expressionRef": ex, "strategy": "manual",
        "features": fmap({"calibration_category": category}), "createdAt": CREATED_AT})
    CAL[(s1, s2)] = (ex, fi, category)

# ---- lists (from the data: lists are what participants on each list saw) -------
LISTS = {}   # (exp key, list_num) -> {"items": set(filling uris), "participants": set}
JSET_KEY = {}


def list_key(exp_key: str, num: str) -> tuple[str, str]:
    return (exp_key, num)


for r in CLOZE:
    k = list_key(f"1a/{CLOZE_COND[r['condition']]}", r["list_num"])
    LISTS.setdefault(k, {"items": set(), "participants": set()})
    LISTS[k]["items"].add(CLOZE_FILL[r["sentence"]])
    LISTS[k]["participants"].add(r["participant"])
for r in PROP:
    k = list_key(f"1b/{r['contentfulness']}", r["list_num"])
    LISTS.setdefault(k, {"items": set(), "participants": set()})
    LISTS[k]["items"].add(PROP_STIM[(r["sentence"], r["preposition"], r["numeral"], r["duration"])][1])
    LISTS[k]["participants"].add(r["participant"])
for r in SIM:
    k = list_key("2", r["list_num"])
    LISTS.setdefault(k, {"items": set(), "participants": set()})
    key = (r["sentence1"], r["sentence2"])
    LISTS[k]["items"].add((CAL[key][1] if r["verb_type"] == "calibration" else PAIR[key][1]))
    LISTS[k]["participants"].add(r["participant"])
for k, v in LISTS.items():   # one list per participant (between-participants lists)
    for p in v["participants"]:
        assert JSET_KEY.setdefault((k[0], p), k) == k, f"{p} on two lists of {k[0]}"


# ---- experimentDefs ------------------------------------------------------------
def participants_of(exp_key: str) -> list[str]:
    return sorted(PART_URI[p] for (ek, p) in JSET_KEY if ek == exp_key)


def lists_of(exp_key: str) -> list[tuple[str, str]]:
    return sorted((k for k in LISTS if k[0] == exp_key), key=lambda k: int(k[1]))


COMMON_FEATS = {"recruitment.platform": "Prolific", "deployment.platform": "JATOS 3.x",
                "frontend": "jsPsych 7.x (jspsych-builder)", "fullscreen_required": "true",
                "consent.information_sheet": INFO_SHEET}


def design(exp_key: str, extra: dict) -> dict:
    ls = lists_of(exp_key)
    return {"distributionStrategy": "custom", "itemOrder": "random-order",
            "features": fmap({"lists": len(ls),
                              "assignment": "each participant saw exactly one list (JATOS "
                                            "batch counter); lists partition the condition's "
                                            "items",
                              "list_numbers_in_data": " ".join(k[1] for k in ls), **extra})}


def add_experiment(exp_key: str, local: str, value: dict) -> None:
    entry = value.pop("_entry")
    value = {**value, "corpusRef": CORPUS_URI, "personaRef": PERSONA_URI,
             "ontologyRef": ONT_URI, "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
             "reproducibility": {"codeUri": REPO_URL + "/tree/main/materials",
                                 "name": "jsPsych experiment", "command":
                                 "cd materials && npm run jspsych -- build --jatos "
                                 + entry},
             "languages": LANG, "languageRefs": LANG_REFS, "createdAt": CREATED_AT}
    EXP_DEFS[exp_key] = value
    R.add("experiments/experiment-defs", C_EXP, local, value)


for gen in ("contentful", "bleached", "templatic"):
    cond = f"{gen}_episodic"
    ek = f"1a/{gen}"
    stims = sorted(sent_uri(t) for t in SENT_ORDER if SENTENCES[t]["generality"] == gen)
    add_experiment(ek, exp_local("1a", gen), {
        "_entry": "cloze-experiment",
        "name": f"Experiment 1a: a cloze diagnostic for telicity ({gen} condition)",
        "description": ("Participants completed each event description with three in-line "
                        "dropdowns (preposition in/for; numeral; time unit), choosing the "
                        "values they found most natural (paper §2). Generality was manipulated "
                        f"between participants; this record is the {gen} condition."),
        "measureType": "telicity", "measureTypeUri": TD_URI["telicity"],
        "taskType": "cloze", "labels": EXP_TEXT["cloze_preposition_choices"],
        "guidelines": guidelines(EXP_TEXT["cloze_instructions"][cond]),
        "guidelinesFormat": "html",
        "templateRefs": [CLOZE_TMPL[gen]],
        "collectionRefs": [EVENT_POOL, PREP_POOL, NUM_POOL, UNIT_POOL],
        "presentation": {"method": "whole-sentence"},
        "recordingMethods": [{"method": "mouse-click", "participantRefs": participants_of(ek),
                              "features": fmap({"instrument": "three HTML <select> dropdowns"})}],
        "design": design(ek, {"condition": cond}),
        "stimulusExpressionRefs": stims,
        "features": fmap({**COMMON_FEATS, "condition": cond, "generality": gen,
                          "clause_type": "episodic",
                          "participants_in_condition": len(participants_of(ek)),
                          "participants_in_experiment_paper": "120"})})
for gen in ("contentful", "bleached", "templatic"):
    ek = f"1b/{gen}"
    stims = sorted(ex for (t, *_), (ex, _) in PROP_STIM.items() if SENTENCES[t]["generality"] == gen)
    add_experiment(ek, exp_local("1b", gen), {
        "_entry": "proportion-experiment",
        "name": f"Experiment 1b: a temporal-overlap diagnostic for durativity ({gen} condition)",
        "description": ("Each event description was shown with a fixed temporal modifier "
                        "(in/for + numeral + time unit), followed by the question 'For what "
                        "proportion of those N units (if any) was [the event happening]?' and "
                        "five ordered options (paper §3). The response is coded 0 (none) to "
                        f"4 (the entirety). This record is the {gen} condition."),
        "measureType": "durativity", "measureTypeUri": TD_URI["durativity"],
        "taskType": "ordinal-scale", "scaleMin": 0, "scaleMax": 4,
        "labels": EXP_TEXT["proportion_response_labels"],
        "guidelines": guidelines(EXP_TEXT["proportion_instructions"][gen]),
        "guidelinesFormat": "html",
        "templateRefs": [PROP_TMPL[gen]],
        "collectionRefs": [EVENT_POOL, PREP_POOL, NUM_POOL, UNIT_POOL],
        "presentation": {"method": "whole-sentence"},
        "recordingMethods": [{"method": "mouse-click", "participantRefs": participants_of(ek),
                              "features": fmap({"instrument": "jsPsych survey-multi-choice "
                                                              "radio buttons"})}],
        "design": design(ek, {"condition": gen}),
        "stimulusExpressionRefs": stims,
        "features": fmap({**COMMON_FEATS, "condition": gen, "generality": gen,
                          "response_coding": "0=none, 1=less than half, 2=about half, "
                                             "3=more than half, 4=the entirety",
                          "participants_in_condition": len(participants_of(ek)),
                          "participants_in_experiment_paper": "250"})})
slider = EXP_TEXT["similarity_slider"]
add_experiment("2", exp_local("2", "all"), {
    "_entry": "similarity-experiment",
    "name": "Experiment 2: sense similarity",
    "description": ("Each trial paired two event descriptions sharing a verb, without temporal "
                    "modifiers; participants rated how different the described situations "
                    "are on a continuous slider from 'completely identical' (0, left) to "
                    "'extremely different' (100, right). Each participant first rated eight "
                    "calibration pairs from Cao et al. (2024), excluded from analysis (§5)."),
    "measureType": "similarity", "taskType": "continuous",
    "scaleMin": slider["min"], "scaleMax": slider["max"],
    "labels": [slider["label_left"], slider["label_right"]],
    "guidelines": guidelines(EXP_TEXT["similarity_instructions"]), "guidelinesFormat": "html",
    "templateRefs": [PAIR_TMPL, CAL_TMPL], "collectionRefs": [EVENT_POOL],
    "presentation": {"method": "whole-sentence",
                     "features": fmap({"prompt": EXP_TEXT["similarity_base_prompt"],
                                       "layout": "the two sentences one above the other; order "
                                                 "randomized per trial (sentences_reversed)"})},
    "recordingMethods": [{"method": "mouse-click", "participantRefs": participants_of("2"),
                          "features": fmap({
                              "instrument": "jsPsych html-slider-response",
                              "slider.min": slider["min"], "slider.max": slider["max"],
                              "slider.step": slider["step"], "slider.start": slider["start"],
                              "slider.require_movement": str(slider["require_movement"]).lower(),
                              "slider.label_left": slider["label_left"],
                              "slider.label_right": slider["label_right"]})}],
    "design": design("2", {"calibration_items_per_participant": "8"}),
    "stimulusExpressionRefs": sorted([v[0] for v in PAIR.values()] + [v[0] for v in CAL.values()]),
    "features": fmap({**COMMON_FEATS, "response_scale": "0 = completely identical, 100 = "
                                                         "extremely different (lower = more similar)",
                      "participants_in_experiment_paper": "202"})})

# ---- judgment sets (one per participant; each participant saw one list) ---------
JSETS_BY_LIST = defaultdict(list)


def add_jset(exp_key: str, pid: str, judgments: list[dict], tool: str) -> None:
    lk = JSET_KEY[(exp_key, pid)]
    js = R.add(f"judgments/{exp_key.split('/')[0]}", C_JSET, f"judgmentset/{exp_key}/{pid}", {
        "experimentRef": EXP_URIS[exp_key], "agent": {"id": pid},
        "judgments": judgments,
        "metadata": {"tool": tool, "personaRef": PERSONA_URI},
        "features": fmap({"platform": "prolific", "participant": PART_URI[pid],
                          "list_num": lk[1], "list": uri(C_CAT, f"list/{lk[0]}/{lk[1]}")}),
        "createdAt": CREATED_AT})
    JSETS_BY_LIST[lk].append(js)


by_pp = defaultdict(list)
for r in CLOZE:
    by_pp[(f"1a/{CLOZE_COND[r['condition']]}", r["participant"])].append(r)
for r in PROP:
    by_pp[(f"1b/{r['contentfulness']}", r["participant"])].append(r)
for r in SIM:
    by_pp[("2", r["participant"])].append(r)

for (ek, pid), rows in sorted(by_pp.items()):
    js = []
    for r in rows:
        if ek.startswith("1a"):
            js.append({"item": {"recordRef": sent_uri(r["sentence"])},
                       "fillingRef": CLOZE_FILL[r["sentence"]],
                       "categoricalValue": r["preposition"],
                       "freeText": f"{r['preposition']} {r['numeral']} {r['duration']}",
                       "features": fmap({"preposition": r["preposition"],
                                         "numeral": r["numeral"], "time_unit": r["duration"]})})
        elif ek.startswith("1b"):
            ex, fi = PROP_STIM[(r["sentence"], r["preposition"], r["numeral"], r["duration"])]
            js.append({"item": {"recordRef": ex}, "fillingRef": fi,
                       "scalarValue": int(r["response"]), "responseTimeMs": int(r["rt"])})
        else:
            key = (r["sentence1"], r["sentence2"])
            cal = r["verb_type"] == "calibration"
            ex, fi = (CAL[key][:2] if cal else PAIR[key])
            js.append({"item": {"recordRef": ex}, "fillingRef": fi,
                       "continuousValue": {"coefficient": int(r["response"]), "exponent": 0},
                       "responseTimeMs": int(r["rt"]),
                       "features": fmap({"sentences_reversed": r["sentences_reversed"].lower(),
                                         "calibration": str(cal).lower()})})
    add_jset(ek, pid, js, {"1a": "jsPsych 7 plugin-cloze-dropdown on JATOS",
                           "1b": "jsPsych 7 survey-multi-choice on JATOS",
                           "2": "jsPsych 7 html-slider-response on JATOS"}[ek.split("/")[0]])

# ---- §6: agreement among Experiment 1b responses with the adverbial fixed ------
for gen in ("contentful", "bleached", "templatic"):
    ek = f"1b/{gen}"
    groups = defaultdict(list)
    for r in PROP:
        if r["contentfulness"] == gen:
            groups[(r["sentence"], r["preposition"])].append(r["response"])
    shares = [max(Counter(v).values()) / len(v) for v in groups.values()]
    unanimous = sum(len(set(v)) == 1 for v in groups.values())
    R.add("experiments/agreement", C_AGREE, f"agreement/{ek}", {
        "experimentRef": EXP_URIS[ek],
        "judgmentSetRefs": sorted(uri(C_JSET, f"judgmentset/{ek}/{p}")
                                  for (k, p) in JSET_KEY if k == ek),
        "metric": "modal-response-share", "metricUri": TD_URI["modal-response-share"],
        "value": round(1000 * sum(shares) / len(shares)),
        "numAnnotators": len({p for (k, p) in JSET_KEY if k == ek}),
        "numItems": len(groups),
        "features": fmap({"item": "(sentence, preposition)",
                          "unanimous_items": unanimous,
                          "mean_responses_per_item": f"{sum(map(len, groups.values())) / len(groups):.3f}",
                          "paper_section": "§6"}),
        "createdAt": CREATED_AT})

# ============================================================================
# Corpus record + memberships
# ============================================================================
CORPUS_EXPRS = ([sent_uri(t) for t in SENT_ORDER] + [v[0] for v in PROP_STIM.values()]
                + [v[0] for v in PAIR.values()] + [v[0] for v in CAL.values()])
R.add("corpus/corpus", C_CORPUS, "corpus", {
    "name": "Aspect is not a fixed property of linguistic expressions: stimuli",
    "description": ("Every stimulus of White, Grimm, & Glass (2026). 312 event descriptions "
                    "built around 40 English transitive verbs (20 manner/result pairs, seven "
                    "semantic classes) at three points on a generality cline: 166 contentful "
                    "sentences (two per PropBank roleset x concreteness sub-sense), 106 "
                    "bleached counterparts, and 40 templatic 'X verb-PAST Y' items. Also the "
                    f"{len(PROP_STIM)} Experiment 1b stimuli (an event description plus an "
                    "in/for temporal modifier), the 750 Experiment 2 test pairs, and the 8 "
                    "Experiment 2 calibration pairs."),
    "version": "1.0.0", "domain": "scientific", "licensing": LIC_DATA,
    "ontologyRefs": [ONT_URI, PB_ONTOLOGY], "eprintRefs": [EPRINT_URI],
    "expressionCount": len(CORPUS_EXPRS),
    "reproducibility": REPRO_META,
    "annotationDesign": {"redundancy": {"annotatorPool": len(PART_URI),
                                        "assignmentStrategy": "custom"},
                         "adjudication": {"method": "none"},
                         "features": fmap({"note": "judgments are not adjudicated; every "
                                                   "participant response is kept"})},
    "features": fmap({"sentences": 312, "contentful": 166, "bleached": 106, "templatic": 40,
                      "stimuli_1b": len(PROP_STIM), "pairs_2": len(PAIR),
                      "calibration_pairs_2": len(CAL)}),
    "languages": LANG, "languageRefs": LANG_REFS, "createdAt": CREATED_AT})
for i, e in enumerate(CORPUS_EXPRS):
    R.add("corpus/memberships", C_CMEMB, f"membership/{e}", {
        "corpusRef": CORPUS_URI, "expressionRef": e, "ordinal": i, "split": "unlabeled",
        "createdAt": CREATED_AT})

# ============================================================================
# Data links: every data/ file and the three model fits
# ============================================================================
DL = [
    ("data-cloze.csv", "judgments", "Experiment 1a trial-level cloze responses", "§2",
     [EXP_URIS[f"1a/{g}"] for g in ("contentful", "bleached", "templatic")]),
    ("data-proportion.csv", "judgments", "Experiment 1b trial-level proportion judgments", "§3",
     [EXP_URIS[f"1b/{g}"] for g in ("contentful", "bleached", "templatic")]),
    ("data-similarity.csv", "judgments", "Experiment 2 trial-level similarity ratings "
     "(test and calibration trials)", "§5", [EXP_URIS["2"]]),
    ("manner-result-sentences.csv", "corpus", "Sentence inventory: one row per PropBank "
     "(sub-)sense with its contentful, bleached, and templatic event descriptions, the "
     "generic descriptions of the unreported Experiment 1a conditions, and each "
     "description's Experiment 1a list and position", "§2.1", []),
    ("manner-result-verbs.csv", "supplementary", "The 40 verbs with past-tense forms and "
     "manner/result classification", "Table 1", []),
    ("propbank-sense-distribution.csv", "supplementary", "Per-verb PropBank roleset counts "
     "from the English portion of OntoNotes 5.0", "§2.4", []),
]
for fn, kind, desc, sec, exps in DL:
    R.add("paper", C_DLINK, f"datalink/{fn}", {
        "eprintUri": SUB_URI, "eprintDid": DID, "dataKind": kind, "corpusRef": CORPUS_URI,
        "catalogRef": ROOT_URI, "experimentRefs": exps, "description": desc,
        "paperSection": sec, "reproducibility": repro("data/scripts", "see data/scripts/README.md"),
        "features": fmap({"path": f"data/{fn}", "url": f"{REPO_URL}/blob/main/data/{fn}",
                          "format": "text/csv", "sha256": sha256_file(DATA / fn),
                          "license": "CC-BY-SA-4.0"}),
        "createdAt": CREATED_AT})
FIT_INFO = {"cloze": ("§2.4-2.5", "Bayesian mixed-effects logistic regression of preposition "
                      "(brms, latent multi-membership sense weights); analysis/fits/cloze-latent.rds",
                      [EXP_URIS[f"1a/{g}"] for g in ("contentful", "bleached", "templatic")]),
            "proportion": ("§3.4-3.5", "Bayesian mixed-effects logistic regression of "
                           "binarized overlap; analysis/fits/proportion-latent.rds",
                           [EXP_URIS[f"1b/{g}"] for g in ("contentful", "bleached", "templatic")]),
            "similarity": ("§5.4-5.5", "Bayesian mixed-effects ordered-beta regression of "
                           "similarity (ordbetareg); analysis/fits/similarity.rds",
                           [EXP_URIS["2"]])}
for fit, (sec, desc, exps) in FIT_INFO.items():
    feats = {"table": "metadata/cache/fit_parameters.csv", "fit": fit}
    for p in FITP:
        if p["fit"] == fit:
            for stat in ("mean", "median", "q2.5", "q97.5", "rhat", "ess_bulk", "ess_tail"):
                feats[f"{p['variable']}.{stat}"] = p[stat]
            feats[f"{p['variable']}.kind"] = p["kind"]
    R.add("paper", C_DLINK, f"datalink/fit/{fit}", {
        "eprintUri": SUB_URI, "eprintDid": DID, "dataKind": "model-output",
        "corpusRef": CORPUS_URI, "catalogRef": ROOT_URI, "experimentRefs": exps,
        "description": "Posterior summary of every population-level effect, group-level SD and "
                       "correlation, and distributional parameter: " + desc,
        "paperSection": sec, "reproducibility": REPRO_FITS, "features": fmap(feats),
        "createdAt": CREATED_AT})

# ============================================================================
# Catalog: the dataset node, one node per experiment, one per deployed list
# ============================================================================
CITE_AS = CITE_RAW + " Data: " + REPO_URL
R.add("catalog", C_CAT, "root", {
    "name": "Aspect is not a fixed property of linguistic expressions (ELM 4) dataset",
    "localId": DATASET, "kind": "experiment-series",
    "description": ("Stimuli, trial-level judgments, annotations, and derived measures for "
                    "White, Grimm, & Glass (2026): Experiment 1a (cloze, 120 participants), "
                    "Experiment 1b (temporal-overlap proportion, 250), and Experiment 2 "
                    "(pairwise similarity, 202) on event descriptions headed by 40 English "
                    "verbs. Verb senses point into the PropBank and VerbNet records of the "
                    "Layers repository."),
    "rootRef": ROOT_URI, "depth": 0, "version": "1.0.0",
    "pinPolicy": "floating", "stability": "frozen", "access": "open",
    "contents": [
        {"produceCollection": C_EXPR, "count": len(CORPUS_EXPRS), "unit": "expression",
         "countSource": "declared", "countIsExact": True, "modality": "text"},
        {"produceCollection": C_JSET, "count": len(by_pp), "unit": "custom",
         "countSource": "declared", "countIsExact": True,
         "features": fmap({"unit": "judgment set (one per participant per experiment condition)"})},
        {"produceCollection": C_JSET, "count": len(CLOZE) + len(PROP) + len(SIM),
         "unit": "judgment", "countSource": "declared", "countIsExact": True},
        {"produceCollection": C_PART, "count": len(PART_URI), "unit": "participant",
         "countSource": "declared", "countIsExact": True}],
    "citation": {"creditPolicy": "cite-self", "citeAs": CITE_AS,
                 "authors": [{"name": f"{g} {f}", "knowledgeRef":
                              {"source": "orcid", "identifier": o}} for g, f, _, o in AUTHORS]},
    "homepage": REPO_URL, "languages": LANG,
    "ontologyRefs": [ONT_URI, PB_ONTOLOGY, VN_ONTOLOGY], "eprintRefs": [EPRINT_URI],
    "licensing": LIC_CATALOG, "reproducibility": REPRO_META,
    "metadata": {"tool": "metadata/scripts/generate_metadata.py (lairs 0.9.0)"},
    "createdAt": CREATED_AT})


def cat_member(container: str, local: str, member: str, member_type: str, role: str,
               ordinal: int | None = None, name: str | None = None, notes: str | None = None):
    R.add("catalog-memberships", C_CATM, f"catm/{local}", {
        "catalogRef": container,
        "member": {"ref": {"recordRef": member}, "memberType": member_type, "memberName": name},
        "role": role, "ordinal": ordinal, "notes": notes, "createdAt": CREATED_AT})


STUDY = {"1a": ("Experiment 1a: cloze diagnostic for telicity", "§2"),
         "1b": ("Experiment 1b: temporal-overlap diagnostic for durativity", "§3"),
         "2": ("Experiment 2: sense similarity", "§5")}
for i, (sk, (name, sec)) in enumerate(STUDY.items()):
    s_uri = R.add("catalog", C_CAT, f"study/{sk}", {
        "name": name, "localId": f"experiment-{sk}", "kind": "judgment-study",
        "description": f"Paper {sec}. Children: one stimulus-set node per deployed list.",
        "parentRef": ROOT_URI, "rootRef": ROOT_URI, "depth": 1, "stability": "frozen",
        "access": "open", "eprintRefs": [EPRINT_URI], "licensing": LIC_DATA,
        "createdAt": CREATED_AT})
    cat_member(ROOT_URI, f"root/study/{sk}", s_uri, C_CAT, "member", i, name)
    for j, ek in enumerate(k for k in EXP_URIS if k.split("/")[0] == sk):
        cat_member(s_uri, f"study/{sk}/experiment/{ek}", EXP_URIS[ek], C_EXP, "produce", j,
                   EXP_DEFS[ek]["name"])
    for j, (ek, num) in enumerate(sorted((k for k in LISTS if k[0].split("/")[0] == sk),
                                         key=lambda k: (k[0], int(k[1])))):
        l_uri = R.add("catalog", C_CAT, f"list/{ek}/{num}", {
            "name": f"Experiment {ek.replace('/', ' ')} list {num}",
            "localId": f"list-{ek.replace('/', '-')}-{num}", "kind": "stimulus-set",
            "description": ("A deployed stimulus list, as recovered from the data: the stimuli "
                            "(stimulus-for edges to their fillings) that participants assigned "
                            "this list judged after exclusions, and the judgment sets those "
                            "participants produced (produce edges)."),
            "parentRef": s_uri, "rootRef": ROOT_URI, "depth": 2, "stability": "frozen",
            "access": "open", "licensing": LIC_DATA,
            "features": fmap({"experiment": ek, "list_num": num,
                              "experimentDef": EXP_URIS[ek],
                              "stimuli": len(LISTS[(ek, num)]["items"]),
                              "participants": len(LISTS[(ek, num)]["participants"])}),
            "createdAt": CREATED_AT})
        cat_member(s_uri, f"study/{sk}/list/{ek}/{num}", l_uri, C_CAT, "member", j)
        for js in sorted(JSETS_BY_LIST[(ek, num)]):
            cat_member(l_uri, f"list/{ek}/{num}/jset/{js}", js, C_JSET, "produce")
        for fi in sorted(LISTS[(ek, num)]["items"]):
            cat_member(l_uri, f"list/{ek}/{num}/item/{fi}", fi, C_FILL, "stimulus-for")
for k, (target, mtype, name) in {
        "corpus": (CORPUS_URI, C_CORPUS, "Stimuli corpus"),
        "ontology": (ONT_URI, C_ONT, "Annotation vocabulary"),
        "verbs": (VERB_COLL, C_RCOLL, "Verb inventory"),
        "senses": (SENSE_COLL, C_RCOLL, "Verb sense inventory"),
        "distribution": (DIST_COLL, C_RCOLL, "OntoNotes 5.0 roleset distribution"),
        "pool-events": (EVENT_POOL, C_RCOLL, "Event descriptions pool"),
        "pool-prepositions": (PREP_POOL, C_RCOLL, "Prepositions pool"),
        "pool-numerals": (NUM_POOL, C_RCOLL, "Numerals pool"),
        "pool-units": (UNIT_POOL, C_RCOLL, "Time units pool")}.items():
    cat_member(ROOT_URI, f"root/produce/{k}", target, mtype, "produce", name=name)
cat_member(ROOT_URI, "root/eprint", EPRINT_URI, C_EPRINT, "documented-by", name=TITLE)
for k, (target, name) in {"propbank": (PB_ONTOLOGY, "PropBank 3.4 frames (Layers)"),
                          "verbnet": (VN_ONTOLOGY, "VerbNet 3.4 (Layers)")}.items():
    cat_member(ROOT_URI, f"root/typed-by/{k}", target, C_ONT, "typed-by", name=name,
               notes="Sense annotations and lexical entries point into this ontology; it is "
                     "not part of this dataset.")

# ============================================================================
counts = R.write()
total = sum(counts.values())
print(f"account: {DID}")
for nsid, n in sorted(counts.items()):
    print(f"  {n:6d}  {nsid}")
print(f"  {total:6d}  records in {len(R.files)} files")
