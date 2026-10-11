"""Plain data types shared by decide (needs jsonschema) and post submit (must stay stdlib-only)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Review:
    event: str
    body: str
    comments: list[dict] = field(default_factory=list)
