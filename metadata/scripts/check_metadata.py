#!/usr/bin/env python3
"""Check the generated release end to end. Exits non-zero on any failure.

1. Pins: lairs 0.9.0 vendoring Layers lexicons 0.11.0; @atproto/lexicon 0.7.19.
2. lairs validation: every pub.layers.* record decodes into its generated lairs
   model (unknown fields and wrong types are rejected).
3. Strict lexicon validation: scripts/validate_lexicons.mjs over the Layers
   0.11.0 tree vendored in lairs and the chive lexicons (formats, lengths,
   required fields, ranges, blob shape, record-key syntax).
4. References: every at:// string in every record resolves. In-account
   references must name a generated record; references into PropBank and
   VerbNet must be in the pinned index (cache/lexical_refs.json), and with
   --live each one is fetched from the Layers PDS with lairs and its CID
   compared with the pinned CID.
5. Fidelity: the records reproduce every row of the trial-level CSVs (each
   judgment maps back to its participant, stimulus, and response), and every
   count matches data/.
6. Determinism: regenerating produces byte-identical files.

Usage (from metadata/):
    .venv/bin/python scripts/check_metadata.py [--live] [--skip-determinism]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from collections import Counter, defaultdict
from pathlib import Path

import lairs
from lairs.records._generated import (
    acquisition, annotation, catalog, corpus, eprint, expression, graph,
    judgment, ontology, persona, resource,
)

META = Path(__file__).resolve().parent.parent
REPO = META.parent
DATA = REPO / "data"
LAIRS_LEX = Path(lairs.__file__).parent / "lexicons"
CHIVE_LEX = Path(os.environ.get("CHIVE_LEXICONS", Path.home() / "chive" / "lexicons"))
DID = tomllib.loads((META / "release.toml").read_text())["account"]

MODELS = {
    "pub.layers.ontology.ontology": ontology.Ontology,
    "pub.layers.ontology.typeDef": ontology.TypeDef,
    "pub.layers.corpus.corpus": corpus.Corpus,
    "pub.layers.corpus.membership": corpus.Membership,
    "pub.layers.expression.expression": expression.Expression,
    "pub.layers.annotation.annotationLayer": annotation.AnnotationLayer,
    "pub.layers.annotation.clusterSet": annotation.ClusterSet,
    "pub.layers.graph.graphEdge": graph.GraphEdge,
    "pub.layers.resource.collection": resource.Collection,
    "pub.layers.resource.entry": resource.Entry,
    "pub.layers.resource.collectionMembership": resource.CollectionMembership,
    "pub.layers.resource.template": resource.Template,
    "pub.layers.resource.filling": resource.Filling,
    "pub.layers.judgment.experimentDef": judgment.ExperimentDef,
    "pub.layers.judgment.judgmentSet": judgment.JudgmentSet,
    "pub.layers.judgment.agreementReport": judgment.AgreementReport,
    "pub.layers.acquisition.participant": acquisition.Participant,
    "pub.layers.persona.persona": persona.Persona,
    "pub.layers.eprint.eprint": eprint.Eprint,
    "pub.layers.eprint.dataLink": eprint.DataLink,
    "pub.layers.catalog.collection": catalog.Collection,
    "pub.layers.catalog.membership": catalog.Membership,
}

FAIL: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ok    " if cond else "  FAIL  ") + msg)
    if not cond:
        FAIL.append(msg)


def load_records() -> list[dict]:
    out = []
    for sub in ("layers", "chive"):
        for p in sorted((META / sub).glob("*.jsonl")):
            for line in p.read_text().splitlines():
                out.append(json.loads(line))
    return out


def at_uris(v, out: list[str]) -> list[str]:
    if isinstance(v, dict):
        for x in v.values():
            at_uris(x, out)
    elif isinstance(v, list):
        for x in v:
            at_uris(x, out)
    elif isinstance(v, str) and v.startswith("at://"):
        out.append(v)
    return out


def read_csv(name: str) -> list[dict]:
    with (DATA / name).open(newline="") as f:
        return list(csv.DictReader(f))


def tree_hash() -> str:
    h = hashlib.sha256()
    for sub in ("layers", "chive"):
        for p in sorted((META / sub).glob("*.jsonl")):
            h.update(p.name.encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="re-fetch every PropBank/VerbNet target from the Layers PDS")
    ap.add_argument("--skip-determinism", action="store_true")
    args = ap.parse_args()

    print("1. pins")
    manifest = tomllib.loads((LAIRS_LEX / "MANIFEST.toml").read_text())["provenance"]
    from importlib.metadata import version
    check(version("lairs") == "0.9.0", f"lairs {version('lairs')} (pinned 0.9.0)")
    check(manifest["layers_version"] == "0.11.0",
          f"lairs vendors Layers lexicons {manifest['layers_version']} "
          f"(git {manifest['layers_git_sha'][:7]}, tree {manifest['lexicon_tree_hash'][:12]})")
    check(version("libipld").startswith("3."), f"libipld {version('libipld')} (3.x required)")
    pkg = json.loads((META / "node_modules/@atproto/lexicon/package.json").read_text())
    check(pkg["version"] == "0.7.19", f"@atproto/lexicon {pkg['version']} (pinned 0.7.19)")

    records = load_records()
    by_uri = {r["uri"]: r["value"] for r in records}
    check(len(by_uri) == len(records), f"{len(records)} records, all AT-URIs unique")
    check(all(r["uri"].startswith(f"at://{DID}/") for r in records),
          f"every record is in the one release account ({DID})")

    print("2. lairs model validation")
    bad = []
    for r in records:
        v = r["value"]
        model = MODELS.get(v["$type"])
        if model is None:
            continue
        try:
            model.model_validate_json(json.dumps({k: x for k, x in v.items() if k != "$type"}))
        except Exception as exc:  # noqa: BLE001
            bad.append(f"{r['uri']}: {exc}")
    n_layers = sum(1 for r in records if r["value"]["$type"].startswith("pub.layers."))
    check(not bad, f"{n_layers - len(bad)}/{n_layers} pub.layers records decode into lairs models")
    for b in bad[:10]:
        print("        " + b)

    print("3. strict lexicon validation (@atproto/lexicon)")
    proc = subprocess.run(
        ["node", str(META / "scripts/validate_lexicons.mjs"), "--layers", str(LAIRS_LEX),
         "--chive", str(CHIVE_LEX), "--json"], capture_output=True, text=True)
    try:
        res = json.loads(proc.stdout)
    except json.JSONDecodeError:
        res = {"total": 0, "ok": 0, "failed": -1, "errors": [proc.stderr[-2000:]]}
    chive_rev = subprocess.run(["git", "-C", str(CHIVE_LEX), "rev-parse", "--short", "HEAD"],
                               capture_output=True, text=True).stdout.strip() or "?"
    check(res["failed"] == 0 and res["total"] == len(records),
          f"{res['ok']}/{res['total']} records valid against Layers 0.11.0 "
          f"({res.get('lexiconsLoaded', {}).get('layers')} docs) + chive "
          f"({res.get('lexiconsLoaded', {}).get('chive')} docs, git {chive_rev})")
    for e in res.get("errors", [])[:10]:
        print("        " + e)

    print("4. references")
    lex = json.loads((META / "cache/lexical_refs.json").read_text())
    pinned = {}
    for rs in lex["rolesets"].values():
        pinned[rs["uri"]] = rs["cid"]
        for c in rs.get("verbnetClasses", []):
            pinned[c["uri"]] = c["cid"]
    for v in lex["verbs"].values():
        pinned[v["propbankLemmaEntry"]["uri"]] = v["propbankLemmaEntry"]["cid"]
        for m in v["verbnetMembers"]:
            pinned[m["uri"]] = m["cid"]
            if m["classUri"]:
                pinned[m["classUri"]] = m["classCid"]
    acct = {a["did"]: name for name, a in lex["accounts"].items()}
    internal = external = 0
    dangling, unpinned = [], []
    ext_targets: Counter = Counter()
    ext_unique: dict[str, set] = defaultdict(set)
    for r in records:
        for u in at_uris(r["value"], []):
            authority = u.split("/")[2]
            if authority == DID:
                internal += 1
                if u not in by_uri:
                    dangling.append(f"{r['uri']} -> {u}")
            else:
                external += 1
                ext_targets[acct.get(authority, authority)] += 1
                ext_unique[acct.get(authority, authority)].add(u)
                if u not in pinned and u not in (lex["propbankOntology"], lex["verbnetOntology"]):
                    unpinned.append(f"{r['uri']} -> {u}")
    check(not dangling, f"{internal} in-account references, all resolve to generated records")
    for d in dangling[:10]:
        print("        " + d)
    check(not unpinned and set(ext_targets) <= set(lex["accounts"]),
          f"{external} references into PropBank/VerbNet ({len(set().union(*ext_unique.values()))} "
          f"distinct records), all in the pinned index")
    for name, n in sorted(ext_targets.items()):
        print(f"        {name}: {n} references to {len(ext_unique[name])} records")
    if args.live:
        import httpx
        from lairs.atproto.pds import PdsClient
        targets = sorted(set().union(*ext_unique.values()))
        missing, moved = [], []
        with PdsClient("https://repo.layers.pub", client=httpx.Client(timeout=60)) as client:
            for u in targets:
                _, _, did, coll, rk = u.split("/")
                try:
                    env = client.get_record(did, coll, rk)
                except Exception as exc:  # noqa: BLE001
                    missing.append(f"{u}: {exc}")
                    continue
                if u in pinned and env.cid != pinned[u]:
                    moved.append(u)
        check(not missing, f"live: {len(targets) - len(missing)}/{len(targets)} PropBank/VerbNet "
                           "targets fetched from repo.layers.pub with lairs")
        for m in missing[:10]:
            print("        " + m)
        check(not moved, f"live: {len(targets) - len(moved)}/{len(targets)} targets unchanged "
                         "since pinning (CID match)")

    print("5. fidelity to data/")
    types = Counter(r["value"]["$type"] for r in records)
    cloze, prop, sim = read_csv("data-cloze.csv"), read_csv("data-proportion.csv"), read_csv("data-similarity.csv")
    inv, dist = read_csv("manner-result-sentences.csv"), read_csv("propbank-sense-distribution.csv")
    verbs = read_csv("manner-result-verbs.csv")
    exprs = {u: v for u, v in by_uri.items() if v["$type"] == "pub.layers.expression.expression"}
    sentences = {v["text"]: u for u, v in exprs.items() if v["id"].split(":")[0] in
                 ("contentful", "bleached", "templatic")}
    texts = ({r["sentence_contentful_episodic"] for r in inv} | {r["sentence_bleached_episodic"] for r in inv}
             | {r["sentence_templatic_episodic"] for r in inv})
    check(set(sentences) == texts, f"{len(sentences)} sentence expressions == the "
                                   f"{len(texts)} distinct sentences in the inventory")
    fills = {u: v for u, v in by_uri.items() if v["$type"] == "pub.layers.resource.filling"}
    exp_name = {u: v["name"] for u, v in by_uri.items() if v["$type"] == "pub.layers.judgment.experimentDef"}

    def stim_of(j):  # -> tuple describing the stimulus as the CSV does
        e = exprs[j["item"]["recordRef"]]
        f = fills[j["fillingRef"]]
        slots = {s["slotName"]: s for s in f["slotFillings"]}
        return e, slots

    got = {"1a": Counter(), "1b": Counter(), "2": Counter()}
    for u, v in by_uri.items():
        if v["$type"] != "pub.layers.judgment.judgmentSet":
            continue
        ek = exp_name[v["experimentRef"]].split(":")[0].split()[-1]
        pid = v["agent"]["id"]
        for j in v["judgments"]:
            e, slots = stim_of(j)
            feats = {x["key"]: x["value"] for x in j.get("features", {}).get("entries", [])}
            if ek == "1a":
                got[ek][(pid, e["text"], j["categoricalValue"], feats["numeral"], feats["time_unit"])] += 1
            elif ek == "1b":
                ef = {x["key"]: x["value"] for x in e["features"]["entries"]}
                base = exprs[e["parentRef"]]["text"]
                got[ek][(pid, base, ef["preposition"], ef["numeral"], ef["time_unit"],
                         str(j["scalarValue"]), str(j["responseTimeMs"]))] += 1
            else:
                s1, s2 = e["text"].split("\n")
                cv = j["continuousValue"]
                got[ek][(pid, s1, s2, str(cv["coefficient"] * 10 ** cv["exponent"]),
                         str(j["responseTimeMs"]), feats["sentences_reversed"])] += 1
    want = {
        "1a": Counter((r["participant"], r["sentence"], r["preposition"], r["numeral"], r["duration"])
                      for r in cloze),
        "1b": Counter((r["participant"], r["sentence"], r["preposition"], r["numeral"], r["duration"],
                       r["response"], r["rt"]) for r in prop),
        "2": Counter((r["participant"], r["sentence1"], r["sentence2"], r["response"], r["rt"],
                      r["sentences_reversed"].lower()) for r in sim),
    }
    for ek, fn in (("1a", "data-cloze.csv"), ("1b", "data-proportion.csv"), ("2", "data-similarity.csv")):
        check(got[ek] == want[ek], f"{sum(got[ek].values())} judgments reproduce all "
                                   f"{sum(want[ek].values())} rows of {fn} (participant, stimulus, response, rt)")
    # every remaining column of the trial files, rebuilt from the records
    feats_of = {u: {f["key"]: f["value"] for f in v.get("features", {}).get("entries", [])}
                for u, v in exprs.items()}
    args_of = {}
    for v in by_uri.values():
        if v["$type"] == "pub.layers.annotation.annotationLayer" and v.get("subkind") == "argument-head":
            a = {x["label"]: x for x in v["annotations"]}
            af = {k: {f["key"]: f["value"] for f in a[k].get("features", {}).get("entries", [])}
                  for k in a}
            args_of[v["expression"]] = (a["subject"]["value"], a["object"]["value"],
                                        af["subject"].get("plural", "false"), af["object"].get("plural", "false"),
                                        af["subject"].get("mass", "false"), af["object"].get("mass", "false"))

    def row_attrs(text: str) -> tuple:
        u = sentences[text]
        f = feats_of[u]
        gen = f["generality"]
        return (f["verb"], f["verb_type"], gen, f.get("propbank_sense", gen),
                f.get("concreteness", gen), f["clause_type"], *args_of[u])

    cols = ("verb", "verb_type", "contentfulness", "propbank_sense", "concreteness", "clause_type",
            "subject_noun", "object_noun", "subject_noun_plural", "object_noun_plural",
            "subject_noun_mass", "object_noun_mass")
    for fn, rows in (("data-cloze.csv", cloze), ("data-proportion.csv", prop)):
        bad_rows = [r for r in rows if row_attrs(r["sentence"]) != tuple(
            r[c].lower() if c.endswith(("_plural", "_mass")) else r[c] for c in cols)
            or r["condition"] != f"{r['contentfulness']}_{r['clause_type']}"]
        check(not bad_rows, f"{fn}: verb, verb_type, contentfulness, propbank_sense, concreteness, "
                            f"clause_type, condition, and the six noun columns follow from the "
                            f"sentence records for all {len(rows)} rows")
    pair_feats = {tuple(v["text"].split("\n")): feats_of[u] for u, v in exprs.items()
                  if v.get("kind") == "sentence-pair"}
    pcols = ("verb", "verb_type", "contentfulness1", "contentfulness2", "propbank_sense1",
             "propbank_sense2", "concreteness1", "concreteness2")
    bad_rows = [r for r in sim if tuple(pair_feats[(r["sentence1"], r["sentence2"])].get(
        c if c == "verb" else f"csv.{c}") for c in pcols) != tuple(r[c] for c in pcols)]
    check(not bad_rows, f"data-similarity.csv: verb, verb_type, contentfulness1/2, propbank_sense1/2, "
                        f"concreteness1/2 follow from the pair records for all {len(sim)} rows")
    sim_test = [r for r in sim if r["verb_type"] != "calibration"]
    bad_rows = [r for r in sim_test if (r["contentfulness1"], r["contentfulness2"]) != (
        feats_of[sentences[r["sentence1"]]]["generality"],
        feats_of[sentences[r["sentence2"]]]["generality"])]
    check(not bad_rows, f"data-similarity.csv: contentfulness1/2 match the generality of "
                        f"sentence1/2 for all {len(sim_test)} test rows")
    lists = Counter()
    for v in by_uri.values():
        if v["$type"] == "pub.layers.judgment.judgmentSet":
            f = {x["key"]: x["value"] for x in v["features"]["entries"]}
            lists[(v["agent"]["id"], exp_name[v["experimentRef"]].split(":")[0].split()[-1], f["list_num"])] += 1
    want_lists = Counter({(r["participant"], ek, r["list_num"]): 1 for ek, rows in
                          (("1a", cloze), ("1b", prop), ("2", sim)) for r in rows})
    check(set(lists) == set(want_lists), f"list_num of all {len(lists)} judgment sets matches the data")
    jsets = Counter(exp_name[v["experimentRef"]].split(":")[0].split()[-1]
                    for v in by_uri.values() if v["$type"] == "pub.layers.judgment.judgmentSet")
    pp = {k: len({r["participant"] for r in rows}) for k, rows in (("1a", cloze), ("1b", prop), ("2", sim))}
    check(dict(jsets) == pp, f"judgment sets per experiment {dict(jsets)} == participants per file {pp}")
    allpp = {r["participant"] for rows in (cloze, prop, sim) for r in rows}
    check(types["pub.layers.acquisition.participant"] == len(allpp),
          f"{types['pub.layers.acquisition.participant']} participant records == {len(allpp)} distinct UUIDs")
    check(len({(r["sentence"], r["preposition"], r["numeral"], r["duration"]) for r in prop})
          + len({(r["sentence1"], r["sentence2"]) for r in sim}) + len(texts) == types["pub.layers.expression.expression"],
          f"{types['pub.layers.expression.expression']} expressions == sentences + Exp 1b stimuli + Exp 2 pairs")
    dist_entries = [v for v in by_uri.values() if v["$type"] == "pub.layers.resource.entry"
                    and any(k.get("label", "").startswith(("OntoNotes", "PropBank")) for k in v.get("knowledgeRefs", []))
                    and any(f["key"] == "count" for f in v.get("features", {}).get("entries", []))]
    check(len(dist_entries) == len(dist), f"{len(dist_entries)} distribution entries == {len(dist)} rows "
                                         "of propbank-sense-distribution.csv")
    got_dist = {(v["lemma"], v["form"]): {f["key"]: f["value"] for f in v["features"]["entries"]}
                for v in dist_entries}
    check(all(got_dist[(r["verb"], r["sense"])]["count"] == r["count"]
              and got_dist[(r["verb"], r["sense"])]["logp_sense_given_verb"] == r["logp_sense_given_verb"]
              for r in dist), "distribution counts and log-probabilities match the CSV verbatim")
    verb_entries = {v["lemma"] for v in by_uri.values() if v["$type"] == "pub.layers.resource.entry"
                    and v.get("form") == v.get("lemma") and v.get("features")
                    and any(f["key"] == "verb_past" for f in v["features"]["entries"])}
    check(verb_entries == {r["verb"] for r in verbs}, f"{len(verb_entries)} verb entries == "
                                                      "manner-result-verbs.csv")
    sense_layers = [v for v in by_uri.values() if v["$type"] == "pub.layers.annotation.annotationLayer"
                    and v.get("subkind") == "sense" and v.get("sourceMethod") == "manual-native"]
    contentful_ok = all(
        len(v["annotations"]) == 1 for v in sense_layers
        if exprs[v["expression"]]["id"].startswith("contentful:"))
    check(len(sense_layers) == len(texts) and contentful_ok,
          f"{len(sense_layers)} sense layers; each contentful sentence carries exactly one roleset")
    mismatch = sorted(r["verb"] for r in verbs
                      if r["verb_type"] != next(x["verb_type"] for x in inv if x["verb"] == r["verb"]))
    print(f"  note  verb_type disagreements between manner-result-verbs.csv and the other files: "
          f"{mismatch or 'none'} (carried on the entry as verb_type_in_manner_result_verbs_csv)")

    if not args.skip_determinism:
        print("6. determinism")
        before = tree_hash()
        subprocess.run([sys.executable, str(META / "scripts/generate_metadata.py")],
                       check=True, capture_output=True)
        after = tree_hash()
        check(before == after, f"regeneration is byte-identical (tree sha256 {after[:16]})")

    print()
    if FAIL:
        print(f"{len(FAIL)} check(s) FAILED")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
