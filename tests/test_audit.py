"""Tests for the immutable, hash-chained audit trail."""

from governance.audit import AuditTrail


class TestAuditTrail:
    def test_empty_trail_is_valid(self) -> None:
        trail = AuditTrail()
        is_valid, msg = trail.verify_integrity()
        assert is_valid
        assert "empty" in msg.lower()

    def test_append_creates_entry(self) -> None:
        trail = AuditTrail()
        entry = trail.append(
            event_type="decision",
            actor="agent",
            action="read",
            target="/data/file.txt",
            outcome="approved",
        )
        assert entry.sequence == 0
        assert entry.event_type == "decision"
        assert len(trail) == 1

    def test_hash_chain_integrity(self) -> None:
        trail = AuditTrail()
        trail.append("decision", "agent", "read", "/a", "approved")
        trail.append("execution", "agent", "read", "/a", "success")
        trail.append("decision", "agent", "write", "/b", "denied")

        is_valid, msg = trail.verify_integrity()
        assert is_valid
        assert "3 entries" in msg

    def test_hash_chain_links_entries(self) -> None:
        trail = AuditTrail()
        e0 = trail.append("decision", "agent", "read", "/a", "approved")
        e1 = trail.append("execution", "agent", "read", "/a", "success")

        assert e0.previous_hash == ""
        assert e1.previous_hash == e0.content_hash
        assert e1.previous_hash != ""

    def test_entries_are_immutable(self) -> None:
        trail = AuditTrail()
        entry = trail.append("decision", "agent", "read", "/a", "approved")

        # frozen dataclass — should raise
        import dataclasses

        with __import__("pytest").raises(dataclasses.FrozenInstanceError):
            entry.action = "write"  # type: ignore[misc]

    def test_cannot_delete_entries(self) -> None:
        """The internal list is not exposed for mutation."""
        trail = AuditTrail()
        trail.append("decision", "agent", "read", "/a", "approved")

        # entries property returns a tuple (immutable)
        entries = trail.entries
        assert isinstance(entries, tuple)

    def test_query_by_event_type(self) -> None:
        trail = AuditTrail()
        trail.append("decision", "agent", "read", "/a", "approved")
        trail.append("execution", "agent", "read", "/a", "success")
        trail.append("decision", "agent", "write", "/b", "denied")

        decisions = trail.query(event_type="decision")
        assert len(decisions) == 2

    def test_query_by_actor(self) -> None:
        trail = AuditTrail()
        trail.append("decision", "alice", "read", "/a", "approved")
        trail.append("decision", "bob", "write", "/b", "denied")

        alice_entries = trail.query(actor="alice")
        assert len(alice_entries) == 1
        assert alice_entries[0].actor == "alice"

    def test_query_combined_filters(self) -> None:
        trail = AuditTrail()
        trail.append("decision", "agent", "read", "/a", "approved")
        trail.append("execution", "agent", "read", "/a", "success")
        trail.append("decision", "agent", "write", "/b", "denied")

        results = trail.query(event_type="decision", action="write")
        assert len(results) == 1
        assert results[0].action == "write"
