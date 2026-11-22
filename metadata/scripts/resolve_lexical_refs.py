#!/usr/bin/env python3
"""Resolve every PropBank and VerbNet reference the release makes, live.

The dataset's sense information points INTO the PropBank and VerbNet records
that already live in the Layers repository (repo.layers.pub); it never copies
them. This script finds those records and writes the pinned index
``metadata/cache/lexical_refs.json`` that ``generate_metadata.py`` reads, so
generation itself needs no network and is deterministic.

For each of the five Layers accounts below it resolves the handle to a DID with
lairs, downloads the account's repository archive once with lairs'
``PdsClient.get_repo_car``, decodes it with ``decode_repo_car``, and records the
commit it read (DID, commit CID, revision), so every reference in the index is
pinned to an exact repository state:

    ontology.propbank.repo.layers.pub  roleset typeDefs (situation-type)
    resource.propbank.repo.layers.pub  lemma entries
    graph.propbank.repo.layers.pub     lemma -instance-of-> roleset edges, and
                                       PropBank's own roleset -> VerbNet class
                                       lexlinks (same-as edges)
    ontology.verbnet.repo.layers.pub   VerbNet class typeDefs (situation-type)
    resource.verbnet.repo.layers.pub   VerbNet member entries (ontologyTypeRef
                                       -> class typeDef)

Every URI in the index is DID-based (``at://did:plc:.../<nsid>/<rkey>``) and
carries the CID of the record revision that was read.

Usage (from metadata/):
    .venv/bin/python scripts/resolve_lexical_refs.py            # refresh
    .venv/bin/python scripts/resolve_lexical_refs.py --offline  # reuse .remote-cache/
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import httpx
import libipld
from lairs.atproto.identity import resolve_handle, resolve_pds
from lairs.atproto.pds import PdsClient, decode_repo_car

META = Path(__file__).resolve().parent.parent
REPO = META.parent
DATA = REPO / "data"
SNAPSHOTS = META / ".remote-cache"
OUT = META / "cache" / "lexical_refs.json"

ACCOUNTS = {
    "ontology.propbank": "ontology.propbank.repo.layers.pub",
    "resource.propbank": "resource.propbank.repo.layers.pub",
    "graph.propbank": "graph.propbank.repo.layers.pub",
    "ontology.verbnet": "ontology.verbnet.repo.layers.pub",
    "resource.verbnet": "resource.verbnet.repo.layers.pub",
}

ROLESET_RE = re.compile(r"^[a-z][a-z0-9_-]*\.\d+$")


def roleset_id(label: str) -> str:
    """'hit.01: strike;' -> 'hit.01' (the data's sense column carries a gloss)."""
    return label.split(":", 1)[0].strip()


def commit_info(car: bytes) -> dict[str, str]:
    """The signed commit a CAR archive was cut from: its CID and revision."""
    header, blocks = libipld.decode_car(car)
    root = header["roots"][0]
    commit = blocks[root]
    cid = root if isinstance(root, str) else libipld.encode_cid(root)
    return {"commitCid": cid, "rev": str(commit.get("rev", ""))}


def snapshot(name: str, handle: str, offline: bool) -> tuple[dict, tuple]:
    """Resolve one account and return its identity record and its records."""
    did = resolve_handle(handle)
    pds = resolve_pds(did)
    path = SNAPSHOTS / f"{name}.car"
    if not offline or not path.exists():
        SNAPSHOTS.mkdir(parents=True, exist_ok=True)
        with PdsClient(pds, client=httpx.Client(timeout=900)) as client:
            path.write_bytes(client.get_repo_car(did))
    car = path.read_bytes()
    records = decode_repo_car(car)
    if not records:
        sys.exit(
            f"{handle}: the archive decoded to zero records. lairs 0.9.0 needs "
            "libipld 3.x (see requirements.lock); libipld 4 breaks its decoder."
        )
    info = {"handle": handle, "did": did, "pds": pds, **commit_info(car),
            "records": len(records)}
    return info, records


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--offline", action="store_true",
                    help="reuse archives already in .remote-cache/")
    args = ap.parse_args()

    accounts, recs = {}, {}
    for name, handle in ACCOUNTS.items():
        accounts[name], recs[name] = snapshot(name, handle, args.offline)
        print(f"  {handle}: {accounts[name]['records']} records "
              f"(rev {accounts[name]['rev']})")

    # ---- PropBank -----------------------------------------------------------
    onto_pb = accounts["ontology.propbank"]["did"]
    rolesets = {}            # roleset id -> {uri, cid, gloss}
    roleset_by_uri = {}
    for e in recs["ontology.propbank"]:
        v = e.value
        if (e.uri.split("/")[3] == "pub.layers.ontology.typeDef"
                and v.get("typeKind") == "situation-type"
                and ROLESET_RE.match(v.get("name", ""))):
            rolesets[v["name"]] = {"uri": e.uri, "cid": e.cid,
                                   "gloss": v.get("gloss") or ""}
            roleset_by_uri[e.uri] = v["name"]
    lemma_entries = {}       # lemma -> {uri, cid}
    for e in recs["resource.propbank"]:
        v = e.value
        if e.uri.split("/")[3] == "pub.layers.resource.entry":
            lemma_entries[v["lemma"]] = {"uri": e.uri, "cid": e.cid}
    lemma_by_uri = {d["uri"]: lem for lem, d in lemma_entries.items()}

    vn_classes = {}          # class typeDef uri -> {id, cid}
    for e in recs["ontology.verbnet"]:
        v = e.value
        if (e.uri.split("/")[3] == "pub.layers.ontology.typeDef"
                and v.get("typeKind") == "situation-type"):
            vn_classes[e.uri] = {"id": v["name"], "cid": e.cid}

    lemma_rolesets = defaultdict(set)     # lemma -> roleset ids (instance-of)
    roleset_vn = defaultdict(dict)        # roleset id -> class uri -> versions
    for e in recs["graph.propbank"]:
        v = e.value
        src = (v.get("source") or {}).get("recordRef")
        tgt = (v.get("target") or {}).get("recordRef")
        if v.get("edgeType") == "instance-of" and src in lemma_by_uri \
                and tgt in roleset_by_uri:
            lemma_rolesets[lemma_by_uri[src]].add(roleset_by_uri[tgt])
        elif v.get("edgeType") == "same-as" and src in roleset_by_uri \
                and tgt in vn_classes:
            props = {f["key"]: f["value"]
                     for f in ((v.get("properties") or {}).get("entries") or [])}
            versions = roleset_vn[roleset_by_uri[src]].setdefault(tgt, set())
            versions.add(f"{props.get('version', '?')} ({props.get('src', '?')})")
            roleset_vn[roleset_by_uri[src]][tgt] = versions
            # keep the edge itself too: it is PropBank's own assertion
            roleset_vn[roleset_by_uri[src]].setdefault("_edges", set()).add(e.uri)

    # ---- VerbNet members ----------------------------------------------------
    vn_members = defaultdict(list)        # lemma -> member entries
    for e in recs["resource.verbnet"]:
        v = e.value
        if e.uri.split("/")[3] != "pub.layers.resource.entry":
            continue
        cls = vn_classes.get(v.get("ontologyTypeRef") or "")
        vn_members[v["lemma"]].append({
            "uri": e.uri, "cid": e.cid,
            "class": cls["id"] if cls else None,
            "classUri": v.get("ontologyTypeRef"),
            "classCid": cls["cid"] if cls else None,
        })

    # ---- what the dataset needs ---------------------------------------------
    with (DATA / "manner-result-verbs.csv").open() as f:
        verbs = [r["verb"] for r in csv.DictReader(f)]
    with (DATA / "manner-result-sentences.csv").open() as f:
        stim_senses = sorted({roleset_id(r["propbank_sense"])
                              for r in csv.DictReader(f)})
    with (DATA / "propbank-sense-distribution.csv").open() as f:
        dist_senses = sorted({r["sense"] for r in csv.DictReader(f)})

    def roleset_record(rid: str) -> dict | None:
        rs = rolesets.get(rid)
        if rs is None:
            return None
        vn = roleset_vn.get(rid, {})
        classes = [
            {"class": vn_classes[u]["id"], "uri": u, "cid": vn_classes[u]["cid"],
             "lexlinks": sorted(vers)}
            for u, vers in sorted(vn.items(), key=lambda kv: vn_classes.get(kv[0], {}).get("id", "")
                                  if kv[0] != "_edges" else "")
            if u != "_edges"
        ]
        return {**rs, "verbnetClasses": classes,
                "lexlinkEdges": sorted(vn.get("_edges", set()))}

    needed = set(stim_senses) | set(dist_senses)
    for v in verbs:
        needed |= lemma_rolesets.get(v, set())
    # Rolesets of the 40 study verbs carry their VerbNet lexlinks; rolesets
    # needed only to link the full OntoNotes distribution carry URI + CID.
    detailed = set(stim_senses)
    for v in verbs:
        detailed |= lemma_rolesets.get(v, set())
    index_rolesets = {}
    unresolved = {"stimulusSenses": [], "distributionSenses": [],
                  "verbLemmas": [], "verbnetLemmas": []}
    for rid in sorted(needed):
        rec = roleset_record(rid)
        if rec is None:
            if rid in stim_senses:
                unresolved["stimulusSenses"].append(rid)
            if rid in dist_senses:
                unresolved["distributionSenses"].append(rid)
            continue
        if rid not in detailed:
            rec = {k: rec[k] for k in ("uri", "cid", "gloss")}
        index_rolesets[rid] = rec

    index_verbs = {}
    for v in verbs:
        if v not in lemma_entries:
            unresolved["verbLemmas"].append(v)
        if not vn_members.get(v):
            unresolved["verbnetLemmas"].append(v)
        index_verbs[v] = {
            "propbankLemmaEntry": lemma_entries.get(v),
            "rolesets": sorted(lemma_rolesets.get(v, set())),
            "verbnetMembers": sorted(vn_members.get(v, []),
                                     key=lambda m: (m["class"] or "", m["uri"])),
        }

    out = {
        "description": (
            "Pinned index of the PropBank and VerbNet records in the Layers "
            "repository (repo.layers.pub) that this release points into. "
            "Written by scripts/resolve_lexical_refs.py; read by "
            "scripts/generate_metadata.py."
        ),
        "accounts": accounts,
        "propbankOntology": next(e.uri for e in recs["ontology.propbank"]
                                 if e.uri.split("/")[3] == "pub.layers.ontology.ontology"),
        "verbnetOntology": next(e.uri for e in recs["ontology.verbnet"]
                                if e.uri.split("/")[3] == "pub.layers.ontology.ontology"),
        "verbs": index_verbs,
        "rolesets": index_rolesets,
        "unresolved": unresolved,
        "counts": {
            "verbs": len(verbs),
            "stimulusSenses": len(stim_senses),
            "stimulusSensesResolved": len(stim_senses) - len(unresolved["stimulusSenses"]),
            "distributionSenses": len(dist_senses),
            "distributionSensesResolved": len(dist_senses) - len(unresolved["distributionSenses"]),
            "verbLemmasResolved": len(verbs) - len(unresolved["verbLemmas"]),
            "verbsWithVerbnetMembers": len(verbs) - len(unresolved["verbnetLemmas"]),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    print(json.dumps(out["counts"], indent=1))
    for k, v in unresolved.items():
        if v:
            print(f"  unresolved {k} ({len(v)}): {', '.join(v[:20])}{' ...' if len(v) > 20 else ''}")
    print(f"wrote {OUT.relative_to(REPO)}")


if __name__ == "__main__":
    main()
