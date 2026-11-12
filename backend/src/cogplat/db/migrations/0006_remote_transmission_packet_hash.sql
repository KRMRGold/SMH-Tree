-- M7 makes remote authorization retries idempotent against the exact packet.
ALTER TABLE remote_transmissions ADD COLUMN packet_sha256 TEXT;

CREATE UNIQUE INDEX idx_remote_transmissions_run_unique
    ON remote_transmissions(run_id);
