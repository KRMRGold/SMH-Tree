"""Fail-closed remote transmission authorization and audit."""
from __future__ import annotations
import hashlib
import json
import sqlite3
from collections.abc import Sequence
from cogplat.domain.chat import ChatMessage
from cogplat.providers.base import ModelProvider
from cogplat.repos import transmissions as transmission_repo

class RemoteNotAllowed(Exception):
    """A remote provider was selected without explicit per-run consent."""

def authorize_and_audit(connection: sqlite3.Connection, run: dict[str, object], provider: ModelProvider, messages: Sequence[ChatMessage], item_refs: Sequence[str]) -> None:
    """Authorize and durably audit the canonical role/content packet before network I/O.

    byte_count is the UTF-8 byte length of compact JSON role/content messages;
    HTTP headers and provider/model transport-envelope fields are excluded.
    """
    if not provider.is_remote:
        return
    if not bool(run.get("allow_remote", False)):
        raise RemoteNotAllowed("Remote transmission is disabled for this run.")
    packet = json.dumps([message.model_dump() for message in messages], ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    run_id = str(run["id"])
    refs = [str(ref) for ref in item_refs]
    packet_hash = hashlib.sha256(packet).hexdigest()
    existing = connection.execute(
        "SELECT provider_label, item_refs_json, byte_count, packet_sha256 FROM remote_transmissions WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if existing is not None:
        if (
            str(existing["provider_label"]) != provider.label
            or json.loads(str(existing["item_refs_json"])) != refs
            or int(existing["byte_count"]) != len(packet)
            or str(existing["packet_sha256"] or "") != packet_hash
        ):
            raise RemoteNotAllowed("A retry attempted to change the previously audited remote packet.")
        return
    transmission_repo.record_transmission(
        connection, run_id, provider.label, refs, len(packet), packet_hash
    )
