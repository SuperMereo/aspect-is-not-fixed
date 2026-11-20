"""Map raw Prolific IDs to stable pseudonymous UUIDs.

Every script in this directory writes participant identifiers through
`pseudonym()`, so a raw `PROLIFIC_PID` never reaches a CSV. Because a Prolific
ID is stable across studies, publishing one would allow cross-study linkage.
The substituted UUIDs do not encode that identifier.

The map lives outside this repository. A persistent raw-ID-to-UUID map keeps
pseudonyms stable across reruns and experiments. Because the map can re-identify
participants, it is not tracked. Point `PARTICIPANT_ID_MAP` at its location:

    export PARTICIPANT_ID_MAP=~/private/supertelicity-participant-id-map.json

If the variable is unset, the fallback is `participant-id-map.json` beside the
raw JATOS dump, which `.gitignore` already excludes. An unknown ID receives a
fresh UUID appended to the map, so re-running after collecting more participants
extends the map rather than renumbering everyone.

One map is shared across all three experiments. A few people took part in more
than one study, and one UUID preserves that cross-study identity.
"""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

DEFAULT_MAP_NAME = "participant-id-map.json"


class ParticipantAnonymizer:
    """A persistent raw-ID to UUID map, loaded once and saved on close."""

    def __init__(self, map_path: Path | str | None = None):
        if map_path is None:
            map_path = os.environ.get("PARTICIPANT_ID_MAP", DEFAULT_MAP_NAME)
        self.map_path = Path(map_path).expanduser()
        if self.map_path.exists():
            self._map = json.loads(self.map_path.read_text())
        else:
            self._map = {}
        self._minted = 0

    def pseudonym(self, raw_id: str) -> str:
        """Return this participant's UUID, minting one if we haven't seen them."""
        raw_id = str(raw_id).strip()
        if raw_id not in self._map:
            self._map[raw_id] = str(uuid.uuid4())
            self._minted += 1
        return self._map[raw_id]

    def save(self) -> None:
        """Persist the map, including any UUIDs minted during this run."""
        self.map_path.parent.mkdir(parents=True, exist_ok=True)
        self.map_path.write_text(json.dumps(self._map, indent=2, sort_keys=True))
        print(
            f"participant map: {len(self._map)} people "
            f"({self._minted} new this run) -> {self.map_path}"
        )
