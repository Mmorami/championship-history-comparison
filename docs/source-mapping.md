# Source Mapping and Access Policy

## Approved Sources

- Primary: [football-data.co.uk](https://www.football-data.co.uk/)
  - Entity: match-level CSV for English second tier (`E1`)
  - Coverage: historical seasons from `1993-94` onward (validated)
  - Access: no API key required
- Secondary fallback checks:
  - [WorldFootball.net](https://www.worldfootball.net/)
  - [Soccerway](https://int.soccerway.com/)
  - [Wikipedia](https://en.wikipedia.org/)
  - Access: no API key required (HTML fetch; attribution required where applicable)

## Deferred Paid APIs (Optional)

- [Football-Data.org](https://www.football-data.org/)
- [API-Football](https://www.api-football.com/)

Paid APIs are optional and currently not required for core warehouse runs.

## Source Priority

1. `football_data` (A confidence for core standings fields)
2. `worldfootball` / `soccerway` / `wikipedia` (B/C confidence backup context)
3. internal fallback stub (D confidence, dev-only)

## Legal and Operational Constraints

- Respect robots/terms and avoid aggressive request rates.
- Keep immutable raw payload snapshots with source URL and timestamp.
- Include source attribution in documentation and UI metadata.
