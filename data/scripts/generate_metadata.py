#!/usr/bin/env python3
"""Generate the pub.layers.* metadata records for the SuperTelicity dataset.

Reads the handle convention from environment (loaded from data/scripts/.env if
present); see the AT-URI convention note below:
  SUPERMEREO_STEM         (dataset stem, default supertelicity.eng)
  SUPERMEREO_DOMAIN       (project domain, default supermereo.io)
  SUPERMEREO_EPRINT_URL   (external URL/DOI for the paper eprint)

Outputs pub.layers.* records to data/scripts/records/ (untracked; override with
LAYERS_RECORDS_DIR). Only the generation scripts are versioned, not their output.

AT-URI convention: authority is the per-namespace supermereo.io data account
<namespace>.<stem>.repo.<domain> (stem defaults to supertelicity.eng); rkeys are
the stable SHA-256 hash defined below. Configure via SUPERMEREO_* env vars.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
DATA = REPO / "data"
SCRIPT_DIR = Path(__file__).resolve().parent
# Generated records are written here and are untracked. Only the generation
# scripts under data/scripts/ are versioned.
OUT = Path(os.environ.get("LAYERS_RECORDS_DIR", SCRIPT_DIR / "records"))

# ----- env loader (no dotenv dep) ------------------------------------------
ENV_FILE = SCRIPT_DIR / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())

# ---- supermereo.io handle + rkey convention --------------------------------
# Records publish to the Layers PDS under the finalized handle convention
# (layers-repo notes/handle-convention-for-new-datasets.md):
#
#     <namespace>.<stem>.repo.<domain>     per-namespace data account
#     <stem>.repo.<domain>                 the dataset account (no namespace)
#
# <namespace> is a pub.layers lexicon namespace (corpus, expression, judgment,
# ...), <stem> is <dataset>.<lang-iso639-3>, `repo` is the literal data-account
# marker, and <domain> is the project domain. rkeys are the first 24 hex chars
# of SHA-256("<handle>|<collection>|<local_id>"), so a rebuild upserts the same
# record. The handle resolves to a minted DID at publish time via the
# bring-your-own-handle DNS flow; nothing here hardcodes a DID.
STEM          = os.environ.get("SUPERMEREO_STEM", "supertelicity.eng")
LAYERS_DOMAIN = os.environ.get("SUPERMEREO_DOMAIN", "supermereo.io")

def _namespace(collection: str) -> str:
    # "pub.layers.corpus.corpus" -> "corpus"
    return collection.split(".")[2]

def _domain(collection: str) -> str:
    return LAYERS_DOMAIN

def account_handle(collection: str) -> str:
    """Per-namespace data account for a collection: <ns>.<stem>.repo.<domain>."""
    return f"{_namespace(collection)}.{STEM}.repo.{_domain(collection)}"

def dataset_handle(domain: str | None = None) -> str:
    """The un-prefixed dataset account: <stem>.repo.<domain>."""
    return f"{STEM}.repo.{domain or LAYERS_DOMAIN}"

def stable_rkey(handle: str, collection: str, local_id: str) -> str:
    seed = f"{handle}|{collection}|{local_id}".encode()
    return hashlib.sha256(seed).hexdigest()[:24]

# ----- helpers --------------------------------------------------------------
NOW = "2026-06-07T00:00:00.000Z"  # deterministic; rewrite at publish time if desired

def aturi(collection: str, local_id: str) -> str:
    """AT-URI for a record from its collection and stable local id.

    Authority is the per-namespace data-account handle; the rkey is the
    content-independent stable hash. Every reference to the same
    (collection, local_id) resolves to the same URI.
    """
    handle = account_handle(collection)
    return f"at://{handle}/{collection}/{stable_rkey(handle, collection, local_id)}"

def slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s[:40] or "x"

def short_hash(s: str, n: int = 8) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:n]

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n")

def write_jsonl(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def byte_len(s: str) -> int:
    return len(s.encode("utf-8"))


# ----- RKEYS (deterministic, descriptive) -----------------------------------
RK_CORPUS = "supertelicity"
RK_ONTOLOGY = "supertelicity-ontology"
RK_TYPEDEFS = {
    "propbank-sense": "td-propbank-sense",
    "concreteness":   "td-concreteness",
    "contentfulness": "td-contentfulness",
}
RK_EXPERIMENTS = {
    "exp1a": "experiment-1a-cloze",
    "exp1b": "experiment-1b-temporal-overlap",
    "exp2":  "experiment-2-similarity",
}
RK_EPRINT_LINK = "elm2026-dataset-link"

# ----- collection names -----------------------------------------------------
COLL_CORPUS       = "pub.layers.corpus.corpus"
COLL_EXPRESSION   = "pub.layers.expression.expression"
COLL_ANNLAYER     = "pub.layers.annotation.annotationLayer"
COLL_ONTOLOGY     = "pub.layers.ontology.ontology"
COLL_TYPEDEF      = "pub.layers.ontology.typeDef"
COLL_EXPERIMENT   = "pub.layers.judgment.experimentDef"
COLL_JUDGMENTSET  = "pub.layers.judgment.judgmentSet"
COLL_EPRINT_LINK  = "pub.layers.eprint.eprint"
COLL_DATALINK     = "pub.layers.eprint.dataLink"
COLL_MEMBERSHIP   = "pub.layers.corpus.membership"
COLL_CLUSTERSET   = "pub.layers.annotation.clusterSet"
COLL_RES_COLL     = "pub.layers.resource.collection"
COLL_RES_ENTRY    = "pub.layers.resource.entry"
COLL_RES_MEMB     = "pub.layers.resource.collectionMembership"
COLL_RES_TEMPLATE = "pub.layers.resource.template"
COLL_RES_FILLING  = "pub.layers.resource.filling"
COLL_PERSONA      = "pub.layers.persona.persona"

# Verbatim text + allowed values extracted from materials/src/*.js
EXP_TEXT = json.loads((REPO / "materials" / "experiment_text.json").read_text())

# Condition lists
CLOZE_CONDITIONS = ["contentful_episodic", "bleached_episodic", "templatic_episodic"]
PROP_CONDITIONS  = ["contentful", "bleached", "templatic"]

# rkeys per condition
EXP1A_RKEYS = {c: f"experiment-1a-cloze-{c.replace('_', '-')}"      for c in CLOZE_CONDITIONS}
EXP1B_RKEYS = {c: f"experiment-1b-proportion-{c}"                   for c in PROP_CONDITIONS}
EXP2_RKEY   = "experiment-2-similarity"
TMPL1A_RKEYS = {c: f"tmpl-cloze-{c.replace('_', '-')}"              for c in CLOZE_CONDITIONS}
TMPL1B_RKEYS = {c: f"tmpl-proportion-{c}"                           for c in PROP_CONDITIONS}
TMPL_CAL_RKEY = "tmpl-similarity-calibration"

EXP1A_URIS = {c: aturi(COLL_EXPERIMENT, rk) for c, rk in EXP1A_RKEYS.items()}
EXP1B_URIS = {c: aturi(COLL_EXPERIMENT, rk) for c, rk in EXP1B_RKEYS.items()}
EXP2_URI   = aturi(COLL_EXPERIMENT, EXP2_RKEY)
TMPL1A_URIS = {c: aturi(COLL_RES_TEMPLATE, rk) for c, rk in TMPL1A_RKEYS.items()}
TMPL1B_URIS = {c: aturi(COLL_RES_TEMPLATE, rk) for c, rk in TMPL1B_RKEYS.items()}
TMPL_CAL_URI = aturi(COLL_RES_TEMPLATE, TMPL_CAL_RKEY)

PERSONA_RKEY = "prolific-elm2026-participant"
PERSONA_URI  = aturi(COLL_PERSONA, PERSONA_RKEY)

# External identifier for the ELM paper (placeholder; set the real URL/DOI).
EPRINT_IDENTIFIER = os.environ.get(
    "SUPERMEREO_EPRINT_URL",
    "https://experimentsinlinguisticmeaning.org/",
)
# The layers eprint record's own URI; layers records reference the paper via it.
EPRINT_URI = aturi(COLL_EPRINT_LINK, RK_EPRINT_LINK)
CORPUS_URI     = aturi(COLL_CORPUS, RK_CORPUS)
ONTOLOGY_URI   = aturi(COLL_ONTOLOGY, RK_ONTOLOGY)
TYPEDEF_URIS   = {k: aturi(COLL_TYPEDEF, v) for k, v in RK_TYPEDEFS.items()}
EXPERIMENT_URIS= {k: aturi(COLL_EXPERIMENT, v) for k, v in RK_EXPERIMENTS.items()}
VERB_COLL_URI  = aturi(COLL_RES_COLL, "verbs")
SENSE_COLL_URI = aturi(COLL_RES_COLL, "propbank-senses")

def fmap(d: dict) -> dict:
    """Build a pub.layers.defs#featureMap from a flat str->str dict."""
    return {"entries": [{"key": str(k), "value": str(v)} for k, v in d.items()]}

def make_ontology():
    return {
        "$type": COLL_ONTOLOGY,
        "name": "SuperTelicity Annotation Ontology",
        "description": (
            "Annotation vocabulary for the SuperTelicity dataset: PropBank "
            "sense, concreteness, and contentfulness "
            "(contentful/bleached/templatic)."
        ),
        "version": "1.0.0",
        "domain": "linguistic",
        "domainUri": aturi("pub.layers.ontology.typeDef", "domain-linguistic"),
        "createdAt": NOW,
    }

def make_typedefs():
    base = {"$type": COLL_TYPEDEF, "ontologyRef": ONTOLOGY_URI, "createdAt": NOW}
    return [
        {**base, "name": "PropBank sense", "typeKind": "attribute-type",
         "gloss": "PropBank roleset identifier and sub-sense label (e.g., 'hit.01: strike; concrete'). The roleset is taken from the English PropBank inventory; sub-senses split a single roleset into concrete and abstract variants where both are attested."},
        {**base, "name": "Concreteness", "typeKind": "attribute-type",
         "gloss": "Whether the sub-sense picks out a concrete or abstract event.",
         "allowedValues": ["concrete", "abstract"]},
        {**base, "name": "Contentfulness", "typeKind": "attribute-type",
         "gloss": "Position on the generality cline: contentful (fully specified arguments), bleached (definite NPs headed by general nouns), or templatic ('X verb-PAST Y').",
         "allowedValues": ["contentful", "bleached", "templatic"]},
    ]

# ============================================================================
# LAYERS: corpus + expressions + annotation layers
# ============================================================================
def make_corpus(sentence_count: int):
    return {
        "$type": COLL_CORPUS,
        "name": "SuperTelicity",
        "description": (
            "166 English transitive-verb event descriptions across 40 verbs "
            "(20 manner/result pairs) at three generality levels (contentful, "
            "bleached, templatic), with three behavioral measures: a cloze "
            "diagnostic for telicity (Exp 1a), a temporal-overlap diagnostic "
            "for durativity (Exp 1b), and a pairwise similarity rating task "
            "(Exp 2)."
        ),
        "version": "1.0.0",
        "domain": "scientific",
        "domainUri": aturi("pub.layers.ontology.typeDef", "domain-scientific"),
        "license": "CC-BY-SA-4.0",
        "ontologyRefs": [ONTOLOGY_URI],
        "eprintRefs": [EPRINT_URI],
        "expressionCount": sentence_count,
        "languages": ["en"],
        "createdAt": NOW,
    }

def load_sentences():
    with (DATA / "manner-result-sentences.csv").open() as f:
        return list(csv.DictReader(f))

def expression_rkey(row, variant):
    # rkey: "<verb>-<sense-slug>-<concreteness>-<variant>"
    sense = row["propbank_sense"].split(":")[0].strip()
    return f"{row['verb']}-{slugify(sense)}-{row['concreteness'][:3]}-{variant}"

def make_expressions(rows):
    """Each stimulus row spawns 3 expression records (one per variant).
    The contentful-episodic variant is the canonical sentence; the other 2
    variants set parentRef to it. Argument-noun features (subject_noun,
    object_noun, plural, mass) ride on features.entries."""
    out = []
    for row in rows:
        canonical_rkey = expression_rkey(row, "ce")
        canonical_uri = aturi(COLL_EXPRESSION, canonical_rkey)
        variants = [
            ("sentence_contentful_episodic", "ce", "contentful"),
            ("sentence_bleached_episodic",   "be", "bleached"),
            ("sentence_templatic_episodic",  "te", "templatic"),
        ]
        for variant_col, variant, contentfulness in variants:
            text = row.get(variant_col) or ""
            if not text.strip():
                continue
            rkey = expression_rkey(row, variant)
            features = {
                "verb": row["verb"],
                "verb_type": row["verb_type"],
                "propbank_sense": row["propbank_sense"],
                "concreteness": row["concreteness"],
                "contentfulness": contentfulness,
                "variant": variant,
                "clause_type": "episodic",
            }
            if contentfulness == "contentful":
                features.update({
                    "subject_noun":         row.get("subject_noun_contentful", ""),
                    "object_noun":          row.get("object_noun_contentful", ""),
                    "subject_noun_plural":  row.get("subject_noun_contentful_plural", ""),
                    "object_noun_plural":   row.get("object_noun_contentful_plural", ""),
                    "subject_noun_mass":    row.get("subject_noun_contentful_mass", ""),
                    "object_noun_mass":     row.get("object_noun_contentful_mass", ""),
                })
            elif contentfulness == "bleached":
                features.update({
                    "subject_noun":         row.get("subject_noun_bleached", ""),
                    "object_noun":          row.get("object_noun_bleached", ""),
                    "subject_noun_plural":  row.get("subject_noun_bleached_plural", ""),
                    "object_noun_plural":   row.get("object_noun_bleached_plural", ""),
                    "subject_noun_mass":    row.get("subject_noun_bleached_mass", ""),
                    "object_noun_mass":     row.get("object_noun_bleached_mass", ""),
                })
            # else templatic: subject/object are X/Y placeholders, no features.
            rec = {
                "$type": COLL_EXPRESSION,
                "id": rkey,
                # Layers enums are open (see docs/foundations/flexible-enums.md);
                # `knownValues` is documentation, not validation. The `sentence`
                # slug is paired with a kindUri pointing at a custom node.
                "kind": "sentence",
                "kindUri": aturi("pub.layers.ontology.typeDef", "kind-sentence"),
                "text": text,
                "eprintRef": EPRINT_URI,
                "features": fmap(features),
                "createdAt": NOW,
                "languages": ["en"],
                "_rkey": rkey,
            }
            if variant != "ce":
                rec["parentRef"] = canonical_uri
            out.append(rec)
    return out

def make_annotation_layers(rows, expressions):
    """Three layers per row (not per variant): each layer carries one of
    {PropBank sense, concreteness, contentfulness}.
    Anchored to the contentful_episodic expression (the canonical text)."""
    out = []
    # Index expressions by (verb, sense-base, concreteness, variant)
    expr_lookup = {e["_rkey"]: e for e in expressions}

    def layer(
        kind_label,
        value,
        typedef_key,
        rkey,
        base_anchor,
        expr_uri,
        formalism=None,
    ):
        ann_id = short_hash(f"{rkey}|{kind_label}|{value}")
        ann = {
            "uuid": {"value": ann_id},
            "anchor": base_anchor,
            "label": kind_label,
            "value": str(value),
            "ontologyTypeRef": TYPEDEF_URIS[typedef_key],
        }
        # "document-tag" is not in the kind knownValues, but layers enums
        # are open (docs/foundations/flexible-enums.md). We pair the slug
        # with a custom kindUri so consumers can resolve it.
        layer_rec = {
            "$type": COLL_ANNLAYER,
            "expression": expr_uri,
            "kind": "document-tag",
            "kindUri": aturi("pub.layers.ontology.typeDef", "kind-document-tag"),
            "subkindUri": TYPEDEF_URIS[typedef_key],
            "ontologyRef": ONTOLOGY_URI,
            "annotations": [ann],
            "createdAt": NOW,
            "languages": ["en"],
            "_rkey": f"ann-{rkey}-{typedef_key[:4]}",
        }
        if formalism:
            layer_rec["formalism"] = formalism
        return layer_rec

    for row in rows:
        sense_full = row["propbank_sense"]  # e.g. "hit.01: strike;"
        # The five layers each apply to all three variants of this row.
        for variant in ["ce", "be", "te"]:
            rkey = expression_rkey(row, variant)
            expr = expr_lookup.get(rkey)
            if not expr:
                continue
            text = expr["text"]
            full_span = {"byteStart": 0, "byteEnd": byte_len(text)}
            base_anchor = {"textSpan": full_span}
            expr_uri = aturi(COLL_EXPRESSION, rkey)
            layer_context = {
                "rkey": rkey,
                "base_anchor": base_anchor,
                "expr_uri": expr_uri,
            }

            # contentfulness: encoded in the variant code
            contentfulness = {
                "ce": "contentful",
                "be": "bleached",
                "te": "templatic",
            }[variant]

            out.append(
                layer(
                    "propbank-sense",
                    sense_full,
                    "propbank-sense",
                    formalism="propbank",
                    **layer_context,
                )
            )
            out.append(
                layer(
                    "concreteness",
                    row["concreteness"],
                    "concreteness",
                    **layer_context,
                )
            )
            out.append(
                layer(
                    "contentfulness",
                    contentfulness,
                    "contentfulness",
                    **layer_context,
                )
            )
    return out

# ============================================================================
# LAYERS: persona (the Prolific participant cohort)
# ============================================================================
SHARED_PARTICIPANT_TEXT = (
    "Inclusion criteria: self-identified native speaker of English, "
    "located in the United States, recruited via Prolific. No participant "
    "permitted to participate in more than one of the studies reported in "
    "White, Grimm, and Glass (2026). Average payment $14.31/hour. Consent "
    "and information sheet at http://factslab.io/information_sheet_021523.pdf. "
    "Fullscreen mode required throughout the task."
)

def make_persona():
    return {
        "$type": COLL_PERSONA,
        "name": "Prolific participant (ELM 2026 aspectual similarity)",
        "description": (
            "Unified annotator profile for every Prolific worker in the three "
            "experiments (Exp 1a cloze, Exp 1b proportion, Exp 2 similarity)."
        ),
        "kind": "crowd-worker",
        "domain": "linguistics",
        "guidelines": SHARED_PARTICIPANT_TEXT,
        "guidelinesFormat": "plain",
        "features": fmap({
            "inclusion.native_english_speaker": "true",
            "inclusion.location":               "US",
            "inclusion.no_prior_participation": "true",
            "inclusion.fullscreen_required":    "true",
            "platform":                         "Prolific",
            "deployment":                       "JATOS",
            "payment.rate_per_hour_usd":        "14.31",
            "consent.information_sheet_url":    "http://factslab.io/information_sheet_021523.pdf",
            "consent.information_sheet_version":"021523",
            "researcher.name":                  "Aaron Steven White",
            "researcher.affiliation":           "University of Rochester",
        }),
        "createdAt": NOW,
    }

# ============================================================================
# LAYERS: allowed-value collections (cloze response options, etc.)
# ============================================================================
def _alv_block(name: str, description: str, kind: str, entries_data, rk_prefix: str):
    """Build (collection, entries[], memberships[], text->entry-uri lookup)
    for one allowed-value pool."""
    coll_rkey = f"alv-{rk_prefix}"
    coll_uri  = aturi(COLL_RES_COLL, coll_rkey)
    collection = {
        "$type": COLL_RES_COLL,
        "name": name,
        "description": description,
        "kind": kind,
        "version": "1.0.0",
        "createdAt": NOW,
        "languages": ["en"],
        "_rkey": coll_rkey,
    }
    entries = []
    memberships = []
    lookup = {}
    for i, (form, features) in enumerate(entries_data, start=1):
        rk = f"av-{rk_prefix}-{slugify(form)}"
        entry_uri = aturi(COLL_RES_ENTRY, rk)
        lookup[form] = entry_uri
        entries.append({
            "$type": COLL_RES_ENTRY,
            "form": form[:4096],
            "features": fmap(features) if features else None,
            "createdAt": NOW,
            "languages": ["en"],
            "_rkey": rk,
        })
        # Omit an empty features field.
        if entries[-1]["features"] is None:
            del entries[-1]["features"]
        memberships.append({
            "$type": COLL_RES_MEMB,
            "collectionRef": coll_uri,
            "entryRef": entry_uri,
            "ordinal": i,
            "createdAt": NOW,
            "_rkey": f"avm-{rk_prefix}-{slugify(form)}",
        })
    return coll_uri, collection, entries, memberships, lookup

def make_allowed_value_collections():
    """Five pools the experiments draw from:
       - prepositions (in/for): cloze + proportion stimulus values
       - numerals (37 values from cloze plugin)
       - duration time units (22 entries: 11 singular + 11 plural, matching
         the cloze plugin's number-dependent form selection)
       - proportion response options (5 Likert positions)
       - similarity slider extremes (2 anchors)"""
    out = {}
    out["prep"] = _alv_block(
        "Prepositions (cloze + proportion tasks)",
        "Closed two-item set used as the first dropdown in Exp 1a and as a stimulus parameter in Exp 1b.",
        "stimulus-pool",
        [(p, {"pos": "preposition"}) for p in EXP_TEXT["cloze_preposition_choices"]],
        "prepositions",
    )
    out["num"] = _alv_block(
        "Numerals (cloze numeral dropdown)",
        "37-element list shown in the second cloze dropdown (Exp 1a, episodic conditions only): 1-10, then 15/20/.../100, then 200/300/.../900, 1000.",
        "stimulus-pool",
        [(n, {"numeric_value": n.replace(",", "")}) for n in EXP_TEXT["cloze_numeral_choices"]],
        "numerals",
    )
    duration_data = (
        [(d, {"form": "singular", "granularity": d}) for d in EXP_TEXT["cloze_duration_choices_singular"]] +
        [(d, {"form": "plural",   "granularity": d.rstrip("s")}) for d in EXP_TEXT["cloze_duration_choices_plural"]]
    )
    out["dur"] = _alv_block(
        "Duration time units (cloze duration dropdown)",
        "22-item pool covering milliseconds through millennia in both singular and plural forms; the cloze plugin selects the form based on the numeral chosen (singular when numeral=1).",
        "stimulus-pool",
        duration_data,
        "durations",
    )
    out["prop"] = _alv_block(
        "Proportion response options (Exp 1b)",
        "5-point ordinal scale; the literal text shown to participants substitutes the trial's numeral+duration for 'N units'.",
        "stimulus-pool",
        [(label, {"ordinal_value": str(i), "label_pattern": label})
         for i, label in enumerate(EXP_TEXT["proportion_response_labels"])],
        "proportion-options",
    )
    out["sim_anchor"] = _alv_block(
        "Similarity slider anchors (Exp 2)",
        "Two endpoint labels on the continuous 0-100 slider; participants rate similarity between these anchors.",
        "stimulus-pool",
        [
            (EXP_TEXT["similarity_slider"]["label_left"],  {"position": "left",  "scalar_value": "0"}),
            (EXP_TEXT["similarity_slider"]["label_right"], {"position": "right", "scalar_value": "100"}),
        ],
        "similarity-anchors",
    )
    return out

# ============================================================================
# LAYERS: per-condition experimentDef records (9 total)
# ============================================================================
def make_experiments():
    """One experimentDef per (paper-experiment × condition variant). Each
    participant in Exp 1a was randomly assigned to one of 5 conditions; in
    Exp 1b to one of 3; Exp 2 has no condition split. The condition
    determines which verbatim instructions the participant saw and which
    template they were tested against."""
    out = []

    # --- Exp 1a: 5 condition variants -------------------------------------
    for cond in CLOZE_CONDITIONS:
        contentfulness = "contentful" if cond.startswith("contentful") else \
                         "bleached" if cond.startswith("bleached") else "templatic"
        rec = {
            "$type": COLL_EXPERIMENT,
            "name": f"Experiment 1a (cloze diagnostic for telicity): {cond.replace('_', ' / ')}",
            "description": (
                f"Per-trial cloze task in the {cond} condition. Participants "
                "saw a sentence followed by three dropdowns and selected the "
                "preposition, numeral, and time unit they judged most natural."
            ),
            "measureType": "comprehension",
            "taskType": "cloze",
            "guidelines": EXP_TEXT["cloze_instructions"][cond],
            "guidelinesFormat": "html",
            "corpusRef": CORPUS_URI,
            "personaRef": PERSONA_URI,
            "templateRefs": [TMPL1A_URIS[cond]],
            "design": {
                "distributionStrategy": "latin-square",
                "itemOrder": "random-order",
                "listConstraints": [{
                    "kind": "latin-square",
                    "targetProperty": "verb",
                }],
            },
            "recordingMethods": [{"method": "mouse-click"}],
            "features": fmap({
                "condition":                    cond,
                "contentfulness":               contentfulness,
                "clause_type":                  "episodic",
                "n_dropdowns":                  "3",
                "preposition_pool_ref":         aturi(COLL_RES_COLL, "alv-prepositions"),
                "numeral_pool_ref":             aturi(COLL_RES_COLL, "alv-numerals"),
                "duration_pool_ref":            aturi(COLL_RES_COLL, "alv-durations"),
                "frontend.framework":           "jsPsych 7.x",
                "frontend.custom_plugin":       "plugin-cloze-dropdown",
                "frontend.fullscreen":          "true",
                "deployment.platform":          "JATOS",
                "recruitment.platform":         "Prolific",
            }),
            "createdAt": NOW,
            "_rkey": EXP1A_RKEYS[cond],
        }
        out.append(rec)

    # --- Exp 1b: 3 condition variants -------------------------------------
    for cond in PROP_CONDITIONS:
        rec = {
            "$type": COLL_EXPERIMENT,
            "name": f"Experiment 1b (temporal-overlap diagnostic for durativity): {cond}",
            "description": (
                f"Per-trial proportion-judgment task in the {cond} condition. "
                "Participants saw a fully realized sentence with experimenter-"
                "supplied preposition, numeral, and duration unit, then chose "
                "one of five ordinal Likert options describing how much of "
                "the modifier's time span the event was occupying."
            ),
            "measureType": "comprehension",
            "taskType": "ordinal-scale",
            "scaleMin": 0,
            "scaleMax": 4,
            "labels": EXP_TEXT["proportion_response_labels"],
            "guidelines": EXP_TEXT["proportion_instructions"][cond],
            "guidelinesFormat": "html",
            "corpusRef": CORPUS_URI,
            "personaRef": PERSONA_URI,
            "templateRefs": [TMPL1B_URIS[cond]],
            "design": {
                "distributionStrategy": "latin-square",
                "itemOrder": "random-order",
                "listConstraints": [{
                    "kind": "latin-square",
                    "targetProperty": "verb",
                }],
            },
            "recordingMethods": [{"method": "mouse-click"}],
            "features": fmap({
                "condition":                    cond,
                "contentfulness":               cond,
                "response_pool_ref":            aturi(COLL_RES_COLL, "alv-proportion-options"),
                "per_trial_question_template":  "For what proportion of those {numeral} {duration} (if any) was the [event] [happening]?",
                "frontend.framework":           "jsPsych 7.x",
                "frontend.plugin":              "jspsych-survey-multi-choice",
                "frontend.fullscreen":          "true",
                "deployment.platform":          "JATOS",
                "recruitment.platform":         "Prolific",
            }),
            "createdAt": NOW,
            "_rkey": EXP1B_RKEYS[cond],
        }
        out.append(rec)

    # --- Exp 2: single condition ------------------------------------------
    out.append({
        "$type": COLL_EXPERIMENT,
        "name": "Experiment 2 (sense similarity)",
        "description": (
            "Pairwise similarity rating task. Each trial paired two event "
            "descriptions sharing a verb (temporal modifier removed). "
            "Participants rated similarity on a continuous slider from "
            "'completely identical' (left) to 'extremely different' (right). "
            "8 calibration trials per participant in 4 categories "
            "(very_similar, somewhat_similar, somewhat_different, very_different)."
        ),
        "measureType": "similarity",
        "taskType": "magnitude",
        "scaleMin": EXP_TEXT["similarity_slider"]["min"],
        "scaleMax": EXP_TEXT["similarity_slider"]["max"],
        "labels": [
            EXP_TEXT["similarity_slider"]["label_left"],
            EXP_TEXT["similarity_slider"]["label_right"],
        ],
        "guidelines": EXP_TEXT["similarity_instructions"],
        "guidelinesFormat": "html",
        "corpusRef": CORPUS_URI,
        "personaRef": PERSONA_URI,
        "templateRefs": [PAIR_TEMPLATE_URI, TMPL_CAL_URI],
        "design": {
            "distributionStrategy": "latin-square",
            "itemOrder": "random-order",
            "listConstraints": [{
                "kind": "latin-square",
                "targetProperty": "verb",
            }],
        },
        "recordingMethods": [{"method": "mouse-click"}],
        "features": fmap({
            "per_trial_prompt":          EXP_TEXT["similarity_base_prompt"],
            "slider.min":                str(EXP_TEXT["similarity_slider"]["min"]),
            "slider.max":                str(EXP_TEXT["similarity_slider"]["max"]),
            "slider.step":               str(EXP_TEXT["similarity_slider"]["step"]),
            "slider.start":              str(EXP_TEXT["similarity_slider"]["start"]),
            "slider.require_movement":   str(EXP_TEXT["similarity_slider"]["require_movement"]).lower(),
            "slider.label_left":         EXP_TEXT["similarity_slider"]["label_left"],
            "slider.label_right":        EXP_TEXT["similarity_slider"]["label_right"],
            "slider.anchor_pool_ref":    aturi(COLL_RES_COLL, "alv-similarity-anchors"),
            "frontend.framework":        "jsPsych 7.x",
            "frontend.plugin":           "jsPsychHtmlSliderResponse",
            "frontend.shuffle_pairs":    "true",
            "frontend.fullscreen":       "true",
            "deployment.platform":       "JATOS",
            "recruitment.platform":      "Prolific",
            "calibration.n_per_participant": "8",
            "calibration.n_categories":      "4",
        }),
        "createdAt": NOW,
        "_rkey": EXP2_RKEY,
    })

    return out

# ============================================================================
# LAYERS: per-condition templates for Exp 1a / Exp 1b + calibration template
# ============================================================================
def make_cloze_templates():
    """One template per cloze condition. Each models the participant-facing
    stimulus as the base sentence followed by 2 or 3 dropdown slots. The
    base_sentence slot is filled from manner-result-sentences.csv; the
    response slots are populated per-trial from participant responses."""
    out = []
    for cond in CLOZE_CONDITIONS:
        slots = [
            {
                "name": "base_sentence",
                "description": "The stimulus sentence with all temporal-modifier slots stripped. Filled from the corpus stimulus inventory.",
                "required": True,
            },
            {
                "name": "preposition",
                "description": "First cloze dropdown: participant selects 'in' or 'for'.",
                "required": True,
                "collectionRef": aturi(COLL_RES_COLL, "alv-prepositions"),
            },
        ]
        slots.append({
            "name": "numeral",
            "description": "Second cloze dropdown: participant selects a numeral.",
            "required": True,
            "collectionRef": aturi(COLL_RES_COLL, "alv-numerals"),
        })
        slots.append({
            "name": "duration",
            "description": "Final cloze dropdown: participant selects a time unit. Form (singular vs plural) co-varies with the numeral.",
            "required": True,
            "collectionRef": aturi(COLL_RES_COLL, "alv-durations"),
        })
        text = "{base_sentence} {preposition} {numeral} {duration}."
        out.append({
            "$type": COLL_RES_TEMPLATE,
            "name": f"Cloze template: {cond}",
            "text": text,
            "slots": slots,
            "experimentRef": EXP1A_URIS[cond],
            "createdAt": NOW,
            "languages": ["en"],
            "features": fmap({
                "condition": cond,
                "n_response_slots": str(len(slots) - 1),  # excludes base_sentence
                "frontend.plugin": "plugin-cloze-dropdown",
            }),
            "_rkey": TMPL1A_RKEYS[cond],
        })
    return out

def make_proportion_templates():
    """One template per proportion condition. All four slots are
    experimenter-filled at trial construction time; the participant's
    response is captured in judgment.scalarValue rather than as a slot
    filling."""
    out = []
    for cond in PROP_CONDITIONS:
        out.append({
            "$type": COLL_RES_TEMPLATE,
            "name": f"Proportion template: {cond}",
            "text": "{base_sentence} {preposition} {numeral} {duration}.",
            "slots": [
                {
                    "name": "base_sentence",
                    "description": "Stimulus sentence with temporal modifier slots stripped.",
                    "required": True,
                },
                {
                    "name": "preposition",
                    "description": "Experimenter-fixed preposition (in / for).",
                    "required": True,
                    "collectionRef": aturi(COLL_RES_COLL, "alv-prepositions"),
                },
                {
                    "name": "numeral",
                    "description": "Experimenter-fixed numeral (constrained to the cloze numeral pool).",
                    "required": True,
                    "collectionRef": aturi(COLL_RES_COLL, "alv-numerals"),
                },
                {
                    "name": "duration",
                    "description": "Experimenter-fixed time unit; co-varies in form with the numeral.",
                    "required": True,
                    "collectionRef": aturi(COLL_RES_COLL, "alv-durations"),
                },
            ],
            "experimentRef": EXP1B_URIS[cond],
            "createdAt": NOW,
            "languages": ["en"],
            "features": fmap({
                "condition": cond,
                "frontend.plugin": "jspsych-survey-multi-choice",
                "response_pool_ref": aturi(COLL_RES_COLL, "alv-proportion-options"),
                "per_trial_question_template":
                    "For what proportion of those {numeral} {duration} (if any) "
                    "was the [event] [happening]?",
            }),
            "_rkey": TMPL1B_RKEYS[cond],
        })
    return out

def make_calibration_template_and_items():
    """The 8 Exp 2 calibration pairs each become a parent pair expression with
    two child sentence expressions, plus a filling against a dedicated
    calibration template. Each pair is a `calibration-pair` expression whose
    text is the two sentences (newline-joined, matching the two-paragraph
    display), with the two sentences materialized as child `sentence`
    expressions anchored by byte span, so each sentence is independently
    addressable rather than stashed in features. This mirrors the corpus
    stimulus expressions in make_expressions. Calibration items have known
    target categories (very_similar / somewhat_similar / somewhat_different /
    very_different) recorded as features on the pair."""
    template = {
        "$type": COLL_RES_TEMPLATE,
        "name": "SuperTelicity Exp 2 calibration-pair template",
        "text": "{sentence1}\n{sentence2}",
        "slots": [
            {"name": "sentence1", "required": True},
            {"name": "sentence2", "required": True},
        ],
        "experimentRef": EXP2_URI,
        "createdAt": NOW,
        "languages": ["en"],
        "features": fmap({
            "purpose": "calibration",
            "shared_with": "similarity-pair template structure; held separate so calibration filling URIs are distinct.",
        }),
        "_rkey": TMPL_CAL_RKEY,
    }
    expressions = []
    fillings = []
    cat_to_anchor = {
        "very_similar":       ("0", "25"),
        "somewhat_similar":   ("25", "50"),
        "somewhat_different": ("50", "75"),
        "very_different":     ("75", "100"),
    }
    for item in EXP_TEXT["similarity_calibration_items"]:
        item_id = item["item_id"]
        s1, s2  = item["sentence1"], item["sentence2"]
        # category from item_id like "calibration_very_similar-1"
        category = item_id.replace("calibration_", "").rsplit("-", 1)[0]
        exp_rk  = f"cal-{slugify(item_id)}"
        fil_rk  = f"fill-{slugify(item_id)}"
        pair_uri = aturi(COLL_EXPRESSION, exp_rk)
        # Parent pair expression. Its text is the two sentences, newline-joined,
        # so the child byte spans below index into it.
        pair_text = f"{s1}\n{s2}"
        expressions.append({
            "$type": COLL_EXPRESSION,
            "id": exp_rk,
            "kind": "calibration-pair",
            "kindUri": aturi("pub.layers.ontology.typeDef", "kind-calibration-pair"),
            "text": pair_text,
            "eprintRef": EPRINT_URI,
            "features": fmap({
                "purpose":           "calibration",
                "category":          category,
                "expected_min":      cat_to_anchor.get(category, ("",""))[0],
                "expected_max":      cat_to_anchor.get(category, ("",""))[1],
                "experiment_ref":    EXP2_URI,
            }),
            "createdAt": NOW,
            "languages": ["en"],
            "_rkey": exp_rk,
        })
        # Two child sentence expressions, anchored by byte span in the parent
        # text. The newline between them is one byte, hence the +1 offset.
        s1_end = byte_len(s1)
        s2_start = s1_end + 1
        for slot, sent, start, end in (
            ("sentence1", s1, 0,        s1_end),
            ("sentence2", s2, s2_start, s2_start + byte_len(s2)),
        ):
            child_rk = f"{exp_rk}-{slot[-1]}"  # cal-...-1 / cal-...-2
            expressions.append({
                "$type": COLL_EXPRESSION,
                "id": child_rk,
                "kind": "sentence",
                "kindUri": aturi("pub.layers.ontology.typeDef", "kind-sentence"),
                "text": sent,
                "parentRef": pair_uri,
                "anchor": {"textSpan": {"byteStart": start, "byteEnd": end}},
                "eprintRef": EPRINT_URI,
                "features": fmap({
                    "purpose":  "calibration",
                    "position": slot,
                }),
                "createdAt": NOW,
                "languages": ["en"],
                "_rkey": child_rk,
            })
        fillings.append({
            "$type": COLL_RES_FILLING,
            "templateRef": TMPL_CAL_URI,
            "slotFillings": [
                {"slotName": "sentence1", "literalValue": s1, "renderedForm": s1},
                {"slotName": "sentence2", "literalValue": s2, "renderedForm": s2},
            ],
            "renderedText": f"{s1}\n{s2}"[:100000],
            "strategy": "manual",
            "expressionRef": pair_uri,
            "features": fmap({
                "purpose":  "calibration",
                "category": category,
            }),
            "createdAt": NOW,
            "_rkey": fil_rk,
        })
    return template, expressions, fillings

# ============================================================================
# LAYERS: Exp 1a + Exp 1b stimulus fillings
# ============================================================================
def make_cloze_fillings(rows, expressions):
    """One filling per cloze-eligible expression, pointing at the matching
    condition template. The filling records only the base_sentence slot
    (filled from the expression's text); the response slots are intentionally
    left empty because participants supply them, and those responses live in
    the judgment record (categoricalValue / scalarValue / freeText)."""
    # Map: variant code -> cloze condition slug
    variant_to_cond = {
        "ce": "contentful_episodic", "be": "bleached_episodic",
        "te": "templatic_episodic",
    }
    expr_lookup = {e["_rkey"]: e for e in expressions}
    out = []
    expr_to_filling_uri = {}
    for row in rows:
        for variant, cond in variant_to_cond.items():
            rkey = expression_rkey(row, variant)
            expr = expr_lookup.get(rkey)
            if not expr:
                continue
            fill_rk = f"fill-cloze-{rkey}"
            fill_uri = aturi(COLL_RES_FILLING, fill_rk)
            expr_uri = aturi(COLL_EXPRESSION, rkey)
            expr_to_filling_uri[expr_uri] = fill_uri
            out.append({
                "$type": COLL_RES_FILLING,
                "templateRef": TMPL1A_URIS[cond],
                "slotFillings": [
                    {"slotName": "base_sentence",
                     "literalValue": expr["text"][:4096],
                     "renderedForm": expr["text"][:4096]},
                ],
                "renderedText": expr["text"][:100000],
                "strategy": "manual",
                "expressionRef": expr_uri,
                "features": fmap({
                    "condition": cond,
                    "purpose":   "stimulus-display",
                    "note":      "participant fills the response slots at trial time",
                }),
                "createdAt": NOW,
                "_rkey": fill_rk,
            })
    return out, expr_to_filling_uri

def make_proportion_fillings(expr_lookup_by_text):
    """One filling per unique (sentence, preposition, numeral, duration) tuple
    presented in data-proportion.csv. All four slots are filled at
    construction time; the participant only contributes the Likert response
    (recorded on judgment.scalarValue, not on this filling)."""
    out = []
    by_key = {}
    with (DATA / "data-proportion.csv").open() as f:
        for r in csv.DictReader(f):
            text = r["sentence"]
            expr_uri = expr_lookup_by_text.get(text)
            if not expr_uri:
                continue
            key = (text, r.get("preposition",""), r.get("numeral",""), r.get("duration",""))
            cond = r.get("contentfulness", "contentful")
            tmpl = TMPL1B_URIS.get(cond, TMPL1B_URIS["contentful"])
            by_key.setdefault(key, (expr_uri, tmpl, cond))
    trial_to_filling_uri = {}
    for i, (key, (expr_uri, tmpl_uri, cond)) in enumerate(by_key.items(), start=1):
        text, prep, num, dur = key
        rk = f"fill-prop-{short_hash('|'.join(key), 12)}"
        filling_uri = aturi(COLL_RES_FILLING, rk)
        trial_to_filling_uri[key] = filling_uri
        out.append({
            "$type": COLL_RES_FILLING,
            "templateRef": tmpl_uri,
            "slotFillings": [
                {"slotName": "base_sentence",
                 "literalValue": text[:4096], "renderedForm": text[:4096]},
                {"slotName": "preposition", "literalValue": prep, "renderedForm": prep},
                {"slotName": "numeral",     "literalValue": num,  "renderedForm": num},
                {"slotName": "duration",    "literalValue": dur,  "renderedForm": dur},
            ],
            "renderedText": (f"{text} {prep} {num} {dur}.")[:100000],
            "strategy": "manual",
            "expressionRef": expr_uri,
            "features": fmap({
                "condition": cond,
                "purpose":   "stimulus-display",
                "per_trial_prompt":
                    f"For what proportion of those {num} {dur} (if any) was "
                    "the event happening?",
            }),
            "createdAt": NOW,
            "_rkey": rk,
        })
    return out, trial_to_filling_uri

# ============================================================================
# LAYERS: eprint link
# ============================================================================
def make_eprint_link():
    return {
        "$type": COLL_EPRINT_LINK,
        "eprintIdentifier": EPRINT_IDENTIFIER,
        "eprintIdentifierType": "url",
        "linkType": "produced-by",
        "corpusRef": CORPUS_URI,
        "description": (
            "The SuperTelicity corpus was produced for White, Grimm, and "
            "Glass (2026), 'Aspect is not a fixed property of linguistic expressions' "
            "(ELM 4, 2026)."
        ),
        "citation": {
            "raw": (
                "White, A. S., Grimm, S., & Glass, L. (2026). Aspect is not a fixed "
                "property of linguistic expressions. In Proceedings of "
                "Experiments in Linguistic Meaning (ELM 4)."
            ),
        },
        "createdAt": NOW,
    }

# ============================================================================
# LAYERS: verb inventory (resource collection + entries + memberships)
# ============================================================================
def make_verb_resources():
    with (DATA / "manner-result-verbs.csv").open() as f:
        verbs = list(csv.DictReader(f))

    collection = {
        "$type": COLL_RES_COLL,
        "name": "SuperTelicity verb inventory",
        "description": "40 English transitive verbs in 20 manner/result pairs, anchoring the SuperTelicity stimuli.",
        "kind": "lexicon",
        "version": "1.0.0",
        "createdAt": NOW,
        "languages": ["en"],
    }
    entries = []
    memberships = []
    for i, v in enumerate(verbs, start=1):
        rk = f"verb-{v['verb']}"
        entry_uri = aturi(COLL_RES_ENTRY, rk)
        entries.append({
            "$type": COLL_RES_ENTRY,
            "lemma": v["verb"],
            "form": v["verb"],
            "features": fmap({
                "verb_past": v["verb_past"],
                "verb_type": v["verb_type"],
            }),
            "createdAt": NOW,
            "languages": ["en"],
            "_rkey": rk,
        })
        memberships.append({
            "$type": COLL_RES_MEMB,
            "collectionRef": VERB_COLL_URI,
            "entryRef": entry_uri,
            "ordinal": i,
            "createdAt": NOW,
            "_rkey": f"vm-{v['verb']}",
        })
    return verbs, collection, entries, memberships

def make_verb_pair_clusterset(verbs):
    """One clusterSet (kind=clustering) with 20 clusters, each cluster
    grouping the manner and result verbs that share an analytical pair.
    Pairing is inferred from row order in manner_result_verbs.csv (manner row
    immediately followed by its result counterpart)."""
    pairs = []
    i = 0
    while i + 1 < len(verbs):
        a, b = verbs[i], verbs[i + 1]
        if {a["verb_type"], b["verb_type"]} == {"manner", "result"}:
            pairs.append((a["verb"], b["verb"]))
            i += 2
        else:
            i += 1
    clusters = []
    for j, (v1, v2) in enumerate(pairs, start=1):
        clusters.append({
            "uuid": {"value": f"pair-{j:02d}"},
            "canonicalLabel": f"{v1}/{v2}",
            "members": [
                {"recordRef": aturi(COLL_RES_ENTRY, f"verb-{v1}")},
                {"recordRef": aturi(COLL_RES_ENTRY, f"verb-{v2}")},
            ],
        })
    return {
        "$type": COLL_CLUSTERSET,
        "kind": "clustering",
        "corpusRef": CORPUS_URI,
        "clusters": clusters,
        "createdAt": NOW,
    }

# ============================================================================
# LAYERS: PropBank sense inventory (only senses appearing in our data)
# ============================================================================
def make_sense_resources(rows):
    """Build a resource collection of every PropBank sense referenced by our
    stimuli (the propbank_sense column). The full OntoNotes distribution
    (5,291 rows) is left in CSV form and linked via dataLink; we only
    materialize the senses our experimental design touches."""
    senses = set()
    for r in rows:
        senses.add(r["propbank_sense"].strip())

    collection = {
        "$type": COLL_RES_COLL,
        "name": "SuperTelicity PropBank sense inventory",
        "description": (
            "PropBank rolesets and concrete/abstract sub-senses referenced by "
            "SuperTelicity stimuli. The full per-verb sense distribution "
            "across the English portion of OntoNotes 5.0 is linked separately "
            "as a dataLink."
        ),
        "kind": "frame-inventory",
        "version": "1.0.0",
        "createdAt": NOW,
        "languages": ["en"],
    }

    entries = []
    memberships = []
    for i, sense in enumerate(sorted(senses), start=1):
        roleset = sense.split(":")[0].strip()
        rk = f"sense-{slugify(sense)}-{short_hash(sense, 4)}"
        entry_uri = aturi(COLL_RES_ENTRY, rk)
        entries.append({
            "$type": COLL_RES_ENTRY,
            "lemma": roleset.split(".")[0] if "." in roleset else roleset,
            "form": sense[:4096],
            "features": fmap({"roleset": roleset, "sense_label": sense}),
            "createdAt": NOW,
            "languages": ["en"],
            "_rkey": rk,
        })
        memberships.append({
            "$type": COLL_RES_MEMB,
            "collectionRef": SENSE_COLL_URI,
            "entryRef": entry_uri,
            "ordinal": i,
            "createdAt": NOW,
            "_rkey": f"sm-{rk}",
        })
    return collection, entries, memberships, {s: aturi(COLL_RES_ENTRY, f"sense-{slugify(s)}-{short_hash(s, 4)}") for s in senses}

# ============================================================================
# LAYERS: variant-grouping clusterSet (kind=same-as)
# ============================================================================
def make_variant_clusterset(rows):
    """Each stimulus row groups its 3 variants together as a single
    'same-as' cluster (same underlying event, different surface forms)."""
    clusters = []
    for row in rows:
        rkeys = []
        for variant in ("ce", "be", "te"):
            rkeys.append(expression_rkey(row, variant))
        members = [{"recordRef": aturi(COLL_EXPRESSION, k)} for k in rkeys]
        cluster_id = expression_rkey(row, "ce").rsplit("-", 1)[0]
        clusters.append({
            "uuid": {"value": f"var-{short_hash(cluster_id)}"},
            "canonicalLabel": f"{row['verb']} / {row['propbank_sense'].split(':')[0].strip()} / {row['concreteness']}",
            "members": members,
        })
    return {
        "$type": COLL_CLUSTERSET,
        "kind": "same-as",
        "corpusRef": CORPUS_URI,
        "clusters": clusters,
        "createdAt": NOW,
    }

# ============================================================================
# LAYERS: Exp 2 multi-item structure
#   resource.template  (1): the pair-comparison stimulus template
#   resource.collection + entries + memberships (1 + 332 + 332)
#                            stimulus pool of the 332 sentences shown in Exp 2,
#                              represented as resource entries so they can fill
#                              the template's two slots (per bead integration
#                              spec, integration/data-models/bead.md)
#   resource.filling   (per unique pair): the materialized stimulus for one
#                              comparison trial; judgment.fillingRef points here
# ============================================================================
RK_PAIR_TEMPLATE   = "tmpl-similarity-pair"
RK_EXP2_STIMPOOL   = "exp2-stimulus-pool"
PAIR_TEMPLATE_URI  = aturi(COLL_RES_TEMPLATE, RK_PAIR_TEMPLATE)
EXP2_STIMPOOL_URI  = aturi(COLL_RES_COLL, RK_EXP2_STIMPOOL)

def stim_entry_rkey(text: str) -> str:
    return f"stim-{short_hash(text, 12)}"

def make_pair_template():
    """Single template defining the Exp 2 pair-comparison stimulus: two
    sentence slots whose fillers come from the Exp 2 stimulus-pool collection."""
    return {
        "$type": COLL_RES_TEMPLATE,
        "name": "SuperTelicity similarity-pair stimulus",
        "text": "{sentence1}\n{sentence2}",
        "slots": [
            {
                "name": "sentence1",
                "description": "First sentence shown in the pair (left position when sentences_reversed=false).",
                "required": True,
                "collectionRef": EXP2_STIMPOOL_URI,
            },
            {
                "name": "sentence2",
                "description": "Second sentence shown in the pair (right position when sentences_reversed=false).",
                "required": True,
                "collectionRef": EXP2_STIMPOOL_URI,
            },
        ],
        "experimentRef": EXPERIMENT_URIS["exp2"],
        "createdAt": NOW,
        "languages": ["en"],
    }

def make_exp2_stimulus_pool(expr_lookup_by_text):
    """Collection of every stimulus-text appearing in Exp 2 (test trials).
    Each entry's sourceRef points back to the corresponding expression record
    so consumers can traverse from filler -> expression -> annotations."""
    sim_path = DATA / "data-similarity.csv"
    texts = set()
    with sim_path.open() as f:
        for r in csv.DictReader(f):
            if r.get("verb_type") == "calibration":
                continue
            texts.add(r["sentence1"])
            texts.add(r["sentence2"])
    # Only stimuli that resolve to an expression in our inventory.
    texts = sorted(t for t in texts if t in expr_lookup_by_text)

    collection = {
        "$type": COLL_RES_COLL,
        "name": "SuperTelicity Experiment 2 stimulus pool",
        "description": (
            "Every sentence shown as a filler in Exp 2 (the pairwise "
            "similarity rating task), as resource entries fillable in the "
            "similarity-pair template's two slots."
        ),
        "kind": "stimulus-pool",
        "version": "1.0.0",
        "createdAt": NOW,
        "languages": ["en"],
    }
    entries = []
    memberships = []
    text_to_entry_uri = {}
    for i, text in enumerate(texts, start=1):
        rk = stim_entry_rkey(text)
        entry_uri = aturi(COLL_RES_ENTRY, rk)
        text_to_entry_uri[text] = entry_uri
        entries.append({
            "$type": COLL_RES_ENTRY,
            "form": text[:4096],
            "sourceRef": expr_lookup_by_text[text],
            "createdAt": NOW,
            "languages": ["en"],
            "_rkey": rk,
        })
        memberships.append({
            "$type": COLL_RES_MEMB,
            "collectionRef": EXP2_STIMPOOL_URI,
            "entryRef": entry_uri,
            "ordinal": i,
            "createdAt": NOW,
            "_rkey": f"sp-{rk}",
        })
    return collection, entries, memberships, text_to_entry_uri

def make_pair_fillings(text_to_entry_uri):
    """One filling per unique (sentence1, sentence2) pair seen in Exp 2 test
    trials. Pair order is canonicalized so swapped presentations share a
    filling; the per-trial sentences_reversed flag is preserved on the
    judgment itself."""
    sim_path = DATA / "data-similarity.csv"
    seen = {}
    with sim_path.open() as f:
        for r in csv.DictReader(f):
            if r.get("verb_type") == "calibration":
                continue
            s1, s2 = r["sentence1"], r["sentence2"]
            if s1 not in text_to_entry_uri or s2 not in text_to_entry_uri:
                continue
            key = tuple(sorted([s1, s2]))
            seen.setdefault(key, (s1, s2))
    out = []
    text_pair_to_filling_uri = {}
    for i, (canon, (s1, s2)) in enumerate(seen.items(), start=1):
        # Use canonical order for slotFillings so the filling is
        # order-invariant; sentences_reversed lives on the judgment record.
        a, b = canon
        rk = f"fill-{i:05d}-{short_hash(a+b, 8)}"
        filling_uri = aturi(COLL_RES_FILLING, rk)
        text_pair_to_filling_uri[canon] = filling_uri
        out.append({
            "$type": COLL_RES_FILLING,
            "templateRef": PAIR_TEMPLATE_URI,
            "slotFillings": [
                {"slotName": "sentence1", "entryRef": text_to_entry_uri[a], "renderedForm": a[:4096]},
                {"slotName": "sentence2", "entryRef": text_to_entry_uri[b], "renderedForm": b[:4096]},
            ],
            "renderedText": f"{a}\n{b}"[:100000],
            "strategy": "exhaustive",
            "createdAt": NOW,
            "_rkey": rk,
        })
    return out, text_pair_to_filling_uri

# ============================================================================
# LAYERS: corpus.membership (one per expression)
# ============================================================================
def make_corpus_memberships(expressions):
    out = []
    for i, e in enumerate(expressions, start=1):
        out.append({
            "$type": COLL_MEMBERSHIP,
            "corpusRef": CORPUS_URI,
            "expressionRef": aturi(COLL_EXPRESSION, e["_rkey"]),
            "ordinal": i,
            "createdAt": NOW,
            "_rkey": f"mem-{e['_rkey']}",
        })
    return out

# ============================================================================
# LAYERS: dataLink (raw CSVs)
# ============================================================================
def make_data_links():
    rows = []
    raw_files = [
        ("data-cloze.csv",      "evaluation-data", "Experiment 1a: cloze responses (per-trial dropdown choices)"),
        ("data-proportion.csv", "evaluation-data", "Experiment 1b: proportion-judgment responses"),
        ("data-similarity.csv", "evaluation-data", "Experiment 2: pairwise similarity ratings"),
        ("propbank-sense-distribution.csv", "supplementary",
            "Per-verb PropBank roleset counts from the English portion of OntoNotes 5.0; feeds multi-membership weighting."),
    ]
    for fn, kind, desc in raw_files:
        rec = {
            "$type": COLL_DATALINK,
            "eprintUri": EPRINT_URI,
            "dataKind": kind,
            "corpusRef": CORPUS_URI,
            "description": desc,
            "paperSection": "Methods / Data",
            "features": fmap({
                "filename": f"data/{fn}",
                "format": "csv",
                "license": "CC-BY-SA-4.0",
            }),
            "createdAt": NOW,
        }
        rows.append(rec)
    return rows

# ============================================================================
# LAYERS: judgmentSet (trial-level behavioral data)
# ============================================================================
def make_judgment_sets(expr_lookup_by_text, text_pair_to_filling_uri,
                       cloze_expr_to_filling_uri, prop_trial_to_filling_uri,
                       calibration_filling_by_pair, calibration_expression_by_pair):
    """One judgmentSet per (participant, experiment-condition). Each trial
    becomes a judgment with item + fillingRef pointing at the rendered
    stimulus (so the full template/filling/expression chain is reconstructable
    from any response)."""
    out = []

    # --- CLOZE (Exp 1a) ---------------------------------------------------
    cloze_rows_by_pp = {}
    with (DATA / "data-cloze.csv").open() as f:
        for r in csv.DictReader(f):
            cloze_rows_by_pp.setdefault(r["participant"], []).append(r)

    for pp, rows in cloze_rows_by_pp.items():
        # Each participant saw a single condition; derive it from the modal
        # contentfulness × clause_type combination across their trials.
        first = rows[0]
        contentfulness = first.get("contentfulness", "")
        clause_type    = first.get("clause_type", "")
        cond_key = (
            f"{contentfulness}_episodic"  if clause_type == "episodic"  else
            "templatic_episodic"
        )
        if cond_key not in CLOZE_CONDITIONS:
            continue
        exp_uri = EXP1A_URIS[cond_key]
        anon_id = "p-" + short_hash(pp, 12)
        judgments = []
        for r in rows:
            text = r.get("sentence", "")
            expr_uri = expr_lookup_by_text.get(text)
            if not expr_uri:
                continue
            j = {"item": {"recordRef": expr_uri}}
            filling_uri = cloze_expr_to_filling_uri.get(expr_uri)
            if filling_uri:
                j["fillingRef"] = filling_uri
            # Participant responses: preposition (categorical), numeral (scalar
            # where possible), duration (free text)
            prep = (r.get("preposition") or "").strip()
            if prep:
                j["categoricalValue"] = prep[:512]
            num = (r.get("numeral") or "").replace(",", "").strip()
            if num:
                try:
                    j["scalarValue"] = int(num)
                except ValueError:
                    pass
            dur = (r.get("duration") or "").strip()
            if dur:
                j["freeText"] = dur[:10000]
            j["features"] = fmap({
                "preposition_response": prep,
                "numeral_response":     r.get("numeral", ""),
                "duration_response":    dur,
                "list_num":             r.get("list_num", ""),
                "verb":                 r.get("verb", ""),
                "propbank_sense":       r.get("propbank_sense", ""),
                "concreteness":         r.get("concreteness", ""),
            })
            judgments.append(j)
        if not judgments:
            continue
        out.append({
            "$type": COLL_JUDGMENTSET,
            "experimentRef": exp_uri,
            "agent": {"id": anon_id},
            "judgments": judgments,
            "metadata": {"tool": "JATOS + jsPsych 7.x + plugin-cloze-dropdown", "timestamp": NOW},
            "features": fmap({
                "platform":        "Prolific",
                "list_num":        first.get("list_num", ""),
                "condition":       cond_key,
                "consent.information_sheet_url":
                                    "http://factslab.io/information_sheet_021523.pdf",
                "consent.information_sheet_version": "021523",
            }),
            "createdAt": NOW,
            "_rkey": f"js-exp1a-{cond_key.replace('_', '-')}-{anon_id}",
        })

    # --- PROPORTION (Exp 1b) ----------------------------------------------
    prop_rows_by_pp = {}
    with (DATA / "data-proportion.csv").open() as f:
        for r in csv.DictReader(f):
            prop_rows_by_pp.setdefault(r["participant"], []).append(r)

    for pp, rows in prop_rows_by_pp.items():
        first = rows[0]
        cond = first.get("contentfulness", "contentful")
        if cond not in PROP_CONDITIONS:
            continue
        exp_uri = EXP1B_URIS[cond]
        anon_id = "p-" + short_hash(pp, 12)
        judgments = []
        for r in rows:
            text = r.get("sentence", "")
            expr_uri = expr_lookup_by_text.get(text)
            if not expr_uri:
                continue
            key = (text, r.get("preposition",""), r.get("numeral",""), r.get("duration",""))
            filling_uri = prop_trial_to_filling_uri.get(key)
            j = {"item": {"recordRef": expr_uri}}
            if filling_uri:
                j["fillingRef"] = filling_uri
            try:
                j["scalarValue"] = int(r["response"])
            except (KeyError, ValueError):
                pass
            try:
                j["responseTimeMs"] = int(float(r["rt"]))
            except (KeyError, ValueError):
                pass
            j["features"] = fmap({
                "list_num":     r.get("list_num", ""),
                "verb":         r.get("verb", ""),
                "propbank_sense": r.get("propbank_sense", ""),
                "concreteness": r.get("concreteness", ""),
            })
            judgments.append(j)
        if not judgments:
            continue
        out.append({
            "$type": COLL_JUDGMENTSET,
            "experimentRef": exp_uri,
            "agent": {"id": anon_id},
            "judgments": judgments,
            "metadata": {"tool": "JATOS + jsPsych 7.x + survey-multi-choice", "timestamp": NOW},
            "features": fmap({
                "platform":  "Prolific",
                "list_num":  first.get("list_num", ""),
                "condition": cond,
                "consent.information_sheet_url":
                              "http://factslab.io/information_sheet_021523.pdf",
                "consent.information_sheet_version": "021523",
            }),
            "createdAt": NOW,
            "_rkey": f"js-exp1b-{cond}-{anon_id}",
        })

    # --- SIMILARITY (Exp 2): single condition; embeds calibration ---------
    sim_rows_by_pp = {}
    with (DATA / "data-similarity.csv").open() as f:
        for r in csv.DictReader(f):
            sim_rows_by_pp.setdefault(r["participant"], []).append(r)

    for pp, rows in sim_rows_by_pp.items():
        anon_id = "p-" + short_hash(pp, 12)
        judgments = []
        for r in rows:
            s1, s2 = r["sentence1"], r["sentence2"]
            is_calibration = r.get("verb_type") == "calibration"
            if is_calibration:
                key = tuple(sorted([s1, s2]))
                cal_expr_uri    = calibration_expression_by_pair.get(key)
                cal_filling_uri = calibration_filling_by_pair.get(key)
                if not (cal_expr_uri and cal_filling_uri):
                    continue
                j = {"item": {"recordRef": cal_expr_uri},
                     "fillingRef": cal_filling_uri}
            else:
                ref1 = expr_lookup_by_text.get(s1)
                ref2 = expr_lookup_by_text.get(s2)
                if not (ref1 and ref2):
                    continue
                canon = tuple(sorted([s1, s2]))
                filling_uri = text_pair_to_filling_uri.get(canon)
                j = {"item": {"recordRef": ref1}}
                if filling_uri:
                    j["fillingRef"] = filling_uri
            try:
                j["scalarValue"] = int(float(r["response"]))
            except (KeyError, ValueError):
                pass
            try:
                j["responseTimeMs"] = int(float(r["rt"]))
            except (KeyError, ValueError):
                pass
            j["features"] = fmap({
                "verb_type":          r.get("verb_type", ""),
                "verb":               r.get("verb", ""),
                "contentfulness1":    r.get("contentfulness1", ""),
                "contentfulness2":    r.get("contentfulness2", ""),
                "propbank_sense1":    r.get("propbank_sense1", ""),
                "propbank_sense2":    r.get("propbank_sense2", ""),
                "sentences_reversed": r.get("sentences_reversed", ""),
                "list_num":           r.get("list_num", ""),
                "is_calibration":     "true" if is_calibration else "false",
            })
            judgments.append(j)
        if not judgments:
            continue
        first = rows[0]
        out.append({
            "$type": COLL_JUDGMENTSET,
            "experimentRef": EXP2_URI,
            "agent": {"id": anon_id},
            "judgments": judgments,
            "metadata": {"tool": "JATOS + jsPsych 7.x + html-slider-response", "timestamp": NOW},
            "features": fmap({
                "platform": "Prolific",
                "list_num": first.get("list_num", ""),
                "consent.information_sheet_url":
                            "http://factslab.io/information_sheet_021523.pdf",
                "consent.information_sheet_version": "021523",
            }),
            "createdAt": NOW,
            "_rkey": f"js-exp2-{anon_id}",
        })

    return out

# ============================================================================
# main
# ============================================================================
def strip_rkey(records):
    """Remove the internal _rkey helper before serialization."""
    out = []
    for r in records:
        if "_rkey" in r:
            r = {k: v for k, v in r.items() if k != "_rkey"}
        out.append(r)
    return out

def main():
    print(f"stem: {STEM}   domain: {LAYERS_DOMAIN}")
    print(f"corpus account: {account_handle(COLL_CORPUS)}")
    print(f"Corpus URI: {CORPUS_URI}")
    print(f"output dir: {OUT}")
    print()

    write_json(OUT / "ontology.json", make_ontology())
    print("  records/ontology.json -> 1 record")

    typedefs = make_typedefs()
    write_jsonl(OUT / "typedefs.jsonl", typedefs)
    print(f"  records/typedefs.jsonl -> {len(typedefs)} records")

    rows = load_sentences()
    write_json(OUT / "corpus.json", make_corpus(len(rows)))
    print("  records/corpus.json -> 1 record")

    exprs = make_expressions(rows)
    write_jsonl(OUT / "expressions.jsonl", strip_rkey(exprs))
    print(f"  records/expressions.jsonl -> {len(exprs)} records")

    # Text→URI lookup for cluster + judgment generators.
    expr_lookup_by_text = {e["text"]: aturi(COLL_EXPRESSION, e["_rkey"]) for e in exprs}

    ann_layers = make_annotation_layers(rows, exprs)
    write_jsonl(OUT / "annotation_layers.jsonl", strip_rkey(ann_layers))
    print(f"  records/annotation_layers.jsonl -> {len(ann_layers)} records")

    # persona: single Prolific cohort
    write_json(OUT / "persona.json", make_persona())
    print("  records/persona.json -> 1 record")

    # allowed-value collections (prepositions, numerals, durations, proportion options, similarity anchors)
    alv = make_allowed_value_collections()
    alv_colls = [v[1] for v in alv.values()]
    alv_entries = [e for v in alv.values() for e in v[2]]
    alv_memberships = [m for v in alv.values() for m in v[3]]
    write_jsonl(OUT / "allowed_value_collections.jsonl", strip_rkey(alv_colls))
    print(f"  records/allowed_value_collections.jsonl -> {len(alv_colls)} records")
    write_jsonl(OUT / "allowed_value_entries.jsonl", strip_rkey(alv_entries))
    print(f"  records/allowed_value_entries.jsonl -> {len(alv_entries)} records")
    write_jsonl(OUT / "allowed_value_memberships.jsonl", strip_rkey(alv_memberships))
    print(f"  records/allowed_value_memberships.jsonl -> {len(alv_memberships)} records")

    # condition-split experimentDefs (9 total)
    experiments = make_experiments()
    write_jsonl(OUT / "experiments.jsonl", strip_rkey(experiments))
    print(f"  records/experiments.jsonl -> {len(experiments)} records")

    # cloze + proportion + calibration templates
    cloze_templates = make_cloze_templates()
    write_jsonl(OUT / "exp1a_templates.jsonl", strip_rkey(cloze_templates))
    print(f"  records/exp1a_templates.jsonl -> {len(cloze_templates)} records")
    prop_templates = make_proportion_templates()
    write_jsonl(OUT / "exp1b_templates.jsonl", strip_rkey(prop_templates))
    print(f"  records/exp1b_templates.jsonl -> {len(prop_templates)} records")
    cal_tmpl, cal_exprs, cal_fillings = make_calibration_template_and_items()
    write_json(OUT / "exp2_calibration_template.json", strip_rkey([cal_tmpl])[0])
    print("  records/exp2_calibration_template.json -> 1 record")
    write_jsonl(OUT / "exp2_calibration_expressions.jsonl", strip_rkey(cal_exprs))
    print(f"  records/exp2_calibration_expressions.jsonl -> {len(cal_exprs)} records")
    write_jsonl(OUT / "exp2_calibration_fillings.jsonl", strip_rkey(cal_fillings))
    print(f"  records/exp2_calibration_fillings.jsonl -> {len(cal_fillings)} records")

    # per-stimulus fillings for Exp 1a (one per expression, condition-routed)
    cloze_fillings, cloze_expr_to_filling_uri = make_cloze_fillings(rows, exprs)
    write_jsonl(OUT / "exp1a_fillings.jsonl", strip_rkey(cloze_fillings))
    print(f"  records/exp1a_fillings.jsonl -> {len(cloze_fillings)} records")

    # per-unique-trial fillings for Exp 1b (one per (sentence, prep, num, dur))
    prop_fillings, prop_trial_to_filling_uri = make_proportion_fillings(expr_lookup_by_text)
    write_jsonl(OUT / "exp1b_fillings.jsonl", strip_rkey(prop_fillings))
    print(f"  records/exp1b_fillings.jsonl -> {len(prop_fillings)} records")

    # Lookups from calibration text-pair -> filling URI and -> expression URI
    # (so similarity judgmentSets can resolve calibration trials to records).
    calibration_filling_by_pair = {}
    calibration_expression_by_pair = {}
    cal_expr_by_rkey = {e["_rkey"]: e for e in cal_exprs}
    for f in cal_fillings:
        slot_map = {sf["slotName"]: sf["literalValue"] for sf in f["slotFillings"]}
        key = tuple(sorted([slot_map["sentence1"], slot_map["sentence2"]]))
        calibration_filling_by_pair[key] = aturi(COLL_RES_FILLING, f["_rkey"])
        # filling._rkey is "fill-<slugified-item_id>"; corresponding expression
        # rkey is "cal-<slugified-item_id>"
        cal_rk = "cal-" + f["_rkey"].removeprefix("fill-")
        if cal_rk in cal_expr_by_rkey:
            calibration_expression_by_pair[key] = aturi(COLL_EXPRESSION, cal_rk)

    write_json(OUT / "eprint_link.json", make_eprint_link())
    print("  records/eprint_link.json -> 1 record")

    # ---- gap-filling additions ----
    verbs, verb_coll, verb_entries, verb_memberships = make_verb_resources()
    write_json(OUT / "verb_collection.json", verb_coll)
    print("  records/verb_collection.json -> 1 record")
    write_jsonl(OUT / "verb_entries.jsonl", strip_rkey(verb_entries))
    print(f"  records/verb_entries.jsonl -> {len(verb_entries)} records")
    write_jsonl(OUT / "verb_memberships.jsonl", strip_rkey(verb_memberships))
    print(f"  records/verb_memberships.jsonl -> {len(verb_memberships)} records")

    write_json(OUT / "verb_pair_clusterset.json",
               make_verb_pair_clusterset(verbs))
    print("  records/verb_pair_clusterset.json -> 1 record")

    sense_coll, sense_entries, sense_memberships, sense_uris = make_sense_resources(rows)
    write_json(OUT / "sense_collection.json", sense_coll)
    print("  records/sense_collection.json -> 1 record")
    write_jsonl(OUT / "sense_entries.jsonl", strip_rkey(sense_entries))
    print(f"  records/sense_entries.jsonl -> {len(sense_entries)} records")
    write_jsonl(OUT / "sense_memberships.jsonl", strip_rkey(sense_memberships))
    print(f"  records/sense_memberships.jsonl -> {len(sense_memberships)} records")

    write_json(OUT / "variant_clusterset.json", make_variant_clusterset(rows))
    print("  records/variant_clusterset.json -> 1 record")

    # Exp 2 multi-item structure via template + filling chain
    # (replaces the prior sentence_pair_clusterset workaround)
    write_json(OUT / "exp2_pair_template.json", make_pair_template())
    print("  records/exp2_pair_template.json -> 1 record")

    exp2_pool, exp2_pool_entries, exp2_pool_memberships, text_to_entry_uri = \
        make_exp2_stimulus_pool(expr_lookup_by_text)
    write_json(OUT / "exp2_stimulus_pool.json", exp2_pool)
    print("  records/exp2_stimulus_pool.json -> 1 record")
    write_jsonl(OUT / "exp2_stimulus_entries.jsonl", strip_rkey(exp2_pool_entries))
    print(f"  records/exp2_stimulus_entries.jsonl -> {len(exp2_pool_entries)} records")
    write_jsonl(OUT / "exp2_stimulus_memberships.jsonl", strip_rkey(exp2_pool_memberships))
    print(f"  records/exp2_stimulus_memberships.jsonl -> {len(exp2_pool_memberships)} records")

    pair_fillings, text_pair_to_filling_uri = make_pair_fillings(text_to_entry_uri)
    write_jsonl(OUT / "exp2_pair_fillings.jsonl", strip_rkey(pair_fillings))
    print(f"  records/exp2_pair_fillings.jsonl -> {len(pair_fillings)} records")

    memberships = make_corpus_memberships(exprs)
    write_jsonl(OUT / "corpus_memberships.jsonl", strip_rkey(memberships))
    print(f"  records/corpus_memberships.jsonl -> {len(memberships)} records")

    data_links = make_data_links()
    write_jsonl(OUT / "data_links.jsonl", data_links)
    print(f"  records/data_links.jsonl -> {len(data_links)} records")

    judgment_sets = make_judgment_sets(
        expr_lookup_by_text,
        text_pair_to_filling_uri,
        cloze_expr_to_filling_uri,
        prop_trial_to_filling_uri,
        calibration_filling_by_pair,
        calibration_expression_by_pair,
    )
    write_jsonl(OUT / "judgment_sets.jsonl", strip_rkey(judgment_sets))
    print(f"  records/judgment_sets.jsonl -> {len(judgment_sets)} records")

if __name__ == "__main__":
    main()
