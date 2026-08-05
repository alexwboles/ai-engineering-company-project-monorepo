"""Typed memory proposal and confirmation contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class MemoryProposal:
    proposal_id: str
    action: Literal["upsert"]
    fact: str
    reason: str
    keys: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["keys"] = list(self.keys)
        return result


@dataclass(frozen=True)
class ConfirmationDecision:
    decision: Literal["approve", "reject", "edit", "unclear"]
    edited_fact: str | None = None
    remainder: str = ""
    reason: str = ""
