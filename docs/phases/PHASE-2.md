# Phase 2

Tag: `phase-2`

## Delivered

- ResPlan restricted pickle loader and organiser JSON adapter.
- Geometry repair, scale conversion, room modelling, and pole-based node placement.
- Area/node lower bound, exact subset zone search, and a Phase 2 axis-aligned L router.
- Independent structural/rule validation, scoring, schema-v2 JSON, and SVG overlay.
- `solve`, `validate`, and `config` CLI commands.

## Validation and security

Configuration rejects non-finite values, negative bounds, booleans in numeric fields, and unknown choices. Structural validation rejects malformed schema-v2 documents. The dataset fetcher requires HTTPS on the pinned GitHub host, a positive timeout, a 200 MB cap, atomic replacement, and a matching SHA-256 digest.

## Known limits

The Phase 2 solver does not build a door graph. V05 and V13 are reported as not checked. The stand-in router ignores walls and windows, so V10-V12 can fail on real plans. Phase 3 replaces that router.
