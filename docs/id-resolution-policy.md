# ID Resolution Policy

## Team IDs

- Deterministic format: `team:<slug>`
- Canonicalization:
  - trim whitespace
  - normalize repeated spaces
  - apply alias map before slug creation
- Alias table stores original source names.

## Player IDs

- Deterministic format: `player:<slug>`
- Current scope uses name-based IDs.
- Future enhancement: add date-of-birth/source ID to resolve collisions.

## Manager IDs

- Managers are currently stored by name in `managers_by_season`.
- Future enhancement: add `manager_id` table for long-term disambiguation.

## Conflict Resolution

1. Keep primary-source value when confidence is `A`.
2. If primary missing, use backup source (`B`).
3. If backups disagree:
   - for core standings fields: flag warning and keep value from higher-priority source
   - for context fields: keep both with lower confidence where needed
4. Persist all source snapshots and lineage for auditability.
