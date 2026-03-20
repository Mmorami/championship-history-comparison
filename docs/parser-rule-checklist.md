# Parser Rule Checklist

## football-data.co.uk (`E1.csv`)

- [x] Fetch season URL by season code (`YYYY` style folder key).
- [x] Validate required columns: `HomeTeam`, `AwayTeam`, `FTHG`, `FTAG`, `FTR`.
- [x] Ignore rows with missing full-time scores.
- [x] Aggregate team-level table stats from match-level rows.
- [x] Rank by points, GD, goals for, team name.
- [x] Derive promotion flags (auto top 2, playoff winner inferred at position 3).
- [x] Persist raw payload and lineage metadata.

## WorldFootball/Soccerway/Wikipedia fallback HTML

- [x] Fetch source home endpoint for resilience fallback.
- [x] Parse first detected table and extract numeric standings rows defensively.
- [x] Mark parsed output at lower confidence than primary source.
- [x] Persist lineage with source URL and checksum.

## Cross-Entity Context

- [x] Managers: support load with confidence and optional date ranges.
- [x] Players: support goals/assists/appearances with coverage flags.
- [x] Assists excluded from scoring unless season coverage marked complete.
