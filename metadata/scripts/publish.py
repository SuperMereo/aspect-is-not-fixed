#!/usr/bin/env python3
"""Plan, and on request apply, the publication of every generated record.

Dry run by default: prints the create/update plan against the target PDS and
sends nothing. With ``--yes`` it writes, through lairs' write path, to the ONE
account in ``release.toml``:

  1. uploads paper/main.pdf with ``WriteClient.upload_blob`` and checks that
     the CID the PDS returns equals the blob CID in the chive submission;
  2. applies the plan with ``WriteClient.apply_writes`` (dependency-ordered,
     chunked applyWrites with per-record putRecord retry), sending each record
     exactly as generated and validated.

Why not ``lairs publish --repo``: lairs 0.9.0's Repository stages only records
that have a generated lairs model (so the two pub.chive.* collections cannot be
staged), re-serializes values through the model, and its PDS diff enumerates
only 26 of the 30 Layers record collections (not catalog.* or acquisition.*),
so a re-publish would re-create those records instead of skipping them. This
script uses the same lairs building blocks (WriteOp, WriteClient, its CID
function, its session store) over the exact generated values and diffs every
collection the release uses. See README, "Known issues".

Usage (from metadata/, after `lairs login <handle>`):
    .venv/bin/python scripts/publish.py              # dry run: show the plan
    .venv/bin/python scripts/publish.py --yes        # write to the PDS
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from collections import Counter
from pathlib import Path

import httpx
from lairs.atproto import auth
from lairs.atproto.identity import resolve_pds
from lairs.atproto.pds import PdsClient
from lairs.author.publish import WriteClient, WriteOp, _record_cid, order_writes

META = Path(__file__).resolve().parent.parent
REPO = META.parent
DID = tomllib.loads((META / "release.toml").read_text())["account"]
PLACEHOLDER = "did:plc:placeholderfactslabioaaa"


def load() -> list[dict]:
    out = []
    for sub in ("layers", "chive"):
        for p in sorted((META / sub).glob("*.jsonl")):
            out += [json.loads(line) for line in p.read_text().splitlines()]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--yes", action="store_true", help="actually write to the PDS")
    ap.add_argument("--endpoint", help="PDS base URL (default: resolved from the DID)")
    ap.add_argument("--layers-only", action="store_true",
                    help="skip the pub.chive.* paper records (e.g. to submit the paper to "
                         "chive from a personal account instead)")
    args = ap.parse_args()

    if DID == PLACEHOLDER:
        sys.exit("release.toml still holds the placeholder DID; set `account` to the new "
                 "factslab.io account's DID and regenerate first (README, Publishing).")
    records = load()
    if args.layers_only:
        records = [r for r in records if not r["value"]["$type"].startswith("pub.chive.")]
    endpoint = args.endpoint or resolve_pds(DID)
    print(f"target: {DID} on {endpoint} ({len(records)} records)")

    # current state of every collection the release writes (public reads)
    on_pds: dict[str, str] = {}
    collections = sorted({r["value"]["$type"] for r in records})
    with PdsClient(endpoint, client=httpx.Client(timeout=120)) as reader:
        for coll in collections:
            try:
                for env in reader.list_records(DID, coll):
                    on_pds[env.uri] = env.cid
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code not in (400, 404):
                    raise
    ops, plan = [], Counter()
    local = {r["uri"] for r in records}
    for r in records:
        _, _, did, coll, rk = r["uri"].split("/")
        cid = _record_cid(r["value"])
        action = "create" if r["uri"] not in on_pds else ("update" if on_pds[r["uri"]] != cid else None)
        if action:
            ops.append(WriteOp(action=action, collection=coll, rkey=rk, uri=r["uri"], cid=cid,
                               value=r["value"]))
        plan[(coll, action or "unchanged")] += 1
    stray = sorted(u for u in on_pds if u not in local)
    for (coll, action), n in sorted(plan.items()):
        print(f"  {action:9s} {n:6d}  {coll}")
    if stray:
        print(f"  {len(stray)} record(s) on the PDS in these collections are not in the release "
              "(left untouched):")
        for u in stray[:10]:
            print("    " + u)
    if not args.yes:
        print("dry run: nothing written (pass --yes to publish)")
        return

    session = auth.SessionStore().load()
    if session is None or session.did != DID:
        sys.exit(f"no lairs session for {DID}: run `lairs login <handle>` first")
    store = auth.SessionStore()
    with WriteClient(endpoint, DID, client=auth.authed_client(session, store=store)) as wc:
        sub = next((r["value"] for r in records
                    if r["value"]["$type"] == "pub.chive.eprint.submission"), None)
        if sub is not None:
            blob = wc.upload_blob((REPO / "paper" / "main.pdf").read_bytes(), "application/pdf")
            got = blob["ref"]["$link"] if isinstance(blob.get("ref"), dict) else str(blob.get("ref"))
            want = sub["document"]["ref"]["$link"]
            if got != want:
                sys.exit(f"uploaded paper CID {got} != submission blob CID {want}; regenerate")
        results = wc.apply_writes(order_writes(ops))
    status = Counter(res.status for res in results)
    print(f"applied: {dict(status)}")
    failed = [res for res in results if res.status == "failed"]
    for res in failed[:20]:
        print(f"  failed {res.uri}: {res.reason}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
