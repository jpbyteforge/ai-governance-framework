"""Immutable, append-only audit trail.

The audit trail is the single source of truth for all governance activity.
It records proposals, decisions, and action results — and does not permit
deletion or modification of existing entries.

This implements Principle 5 (Evidence, not persuasion) and Principle 7 (Ownership)
by ensuring every action is traceable to a human owner and decision authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class AuditEntry:
    """A single immutable record in the audit trail.

    Each entry is hash-chained to the previous entry, forming a tamper-evident
    log similar to a blockchain. If any entry is modified, the chain breaks.
    """

    sequence: int
    event_type: str
    actor: str
    action: str
    target: str
    outcome: str
    details: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    previous_hash: str = ""

    @property
    def content_hash(self) -> str:
        """SHA-256 hash of the entry's content, chained to the previous entry."""
        payload = json.dumps(
            {
                "sequence": self.sequence,
                "event_type": self.event_type,
                "actor": self.actor,
                "action": self.action,
                "target": self.target,
                "outcome": self.outcome,
                "details": self.details,
                "timestamp": self.timestamp.isoformat(),
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode()).hexdigest()


class AuditTrail:
    """Append-only, hash-chained audit trail.

    Guarantees:
    - Entries cannot be deleted or modified after creation.
    - Each entry is hash-chained to the previous one (tamper-evident).
    - The trail can be verified for integrity at any point.
    """

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    def append(
        self,
        event_type: str,
        actor: str,
        action: str,
        target: str,
        outcome: str,
        details: dict[str, Any] | None = None,
    ) -> AuditEntry:
        """Append a new entry to the audit trail.

        Returns the created entry (frozen/immutable).
        """
        previous_hash = self._entries[-1].content_hash if self._entries else ""

        entry = AuditEntry(
            sequence=len(self._entries),
            event_type=event_type,
            actor=actor,
            action=action,
            target=target,
            outcome=outcome,
            details=details or {},
            previous_hash=previous_hash,
        )

        self._entries.append(entry)
        return entry

    def verify_integrity(self) -> tuple[bool, str]:
        """Verify the hash chain integrity of the entire trail.

        Returns:
            A tuple of (is_valid, message).
        """
        if not self._entries:
            return (True, "Audit trail is empty — nothing to verify.")

        # First entry must have empty previous_hash
        if self._entries[0].previous_hash != "":
            return (False, "First entry has non-empty previous_hash — chain is broken.")

        for i in range(1, len(self._entries)):
            expected_hash = self._entries[i - 1].content_hash
            actual_hash = self._entries[i].previous_hash
            if expected_hash != actual_hash:
                return (
                    False,
                    f"Chain broken at entry {i}: "
                    f"expected previous_hash={expected_hash!r}, "
                    f"got {actual_hash!r}.",
                )

        return (True, f"Audit trail verified: {len(self._entries)} entries, chain intact.")

    def query(
        self,
        event_type: str | None = None,
        actor: str | None = None,
        action: str | None = None,
    ) -> tuple[AuditEntry, ...]:
        """Query audit entries by filters. All filters are AND-combined."""
        results: list[AuditEntry] = []
        for entry in self._entries:
            if event_type is not None and entry.event_type != event_type:
                continue
            if actor is not None and entry.actor != actor:
                continue
            if action is not None and entry.action != action:
                continue
            results.append(entry)
        return tuple(results)

    @property
    def entries(self) -> tuple[AuditEntry, ...]:
        """Return all entries as an immutable tuple."""
        return tuple(self._entries)

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"AuditTrail(entries={len(self._entries)})"
