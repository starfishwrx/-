from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DebugLogStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def write(self, event: dict[str, Any]) -> None:
        item = dict(event)
        item.setdefault("ts", datetime.now(timezone.utc).isoformat())
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def tail(self, lines: int = 200) -> list[dict[str, Any]]:
        raw = self.path.read_text(encoding="utf-8").splitlines()
        out = []
        for row in raw[-max(1, lines):]:
            try:
                out.append(json.loads(row))
            except json.JSONDecodeError:
                continue
        return out
