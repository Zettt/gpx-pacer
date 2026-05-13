# GPX Pacer

GPX Pacer turns recorded activity tracks into pacing and analysis outputs. This context defines the route and split terms that shape those outputs.

## Language

**Activity track**:
An ordered sequence of recorded geographic points from a parsed input activity.
_Avoid_: GPX route, GPX track, file geometry

**Surface lookup failure**:
The route-level surface acquisition step could not obtain usable OSM data for the activity track.
_Avoid_: unmatched split, unknown surface

**Unknown surface**:
A split-level result used when the route data was available but no usable way match or normalized surface value existed for that split.
_Avoid_: request failure, API error

**Normalized surface**:
A user-facing surface label assigned to a split.
_Avoid_: raw OSM tag value, surface taxonomy

**Surface cache**:
The stored raw route-level Overpass response reused by `--surface` runs for the same activity track extent and query shape.
_Avoid_: optional mode, user-facing feature flag

**Surface bbox buffer**:
The fixed distance added around an activity track extent before route-level OSM data acquisition.
_Avoid_: user preference, match radius

**Split polyline**:
The portion of the activity track geometry reconstructed for one split segment from its distance bounds.
_Avoid_: midpoint, straight chord, point sample

**Surface match**:
The OSM way selected for a split polyline using route-local geometry.
_Avoid_: nearest point lookup, midpoint query

**Surface pipeline**:
The route-level surface workflow composed of acquisition, geometry preparation, matching, and normalization.
_Avoid_: single lookup function, output formatter

## Relationships

- An **Activity track** produces one or more **Split segments**
- One CLI input yields one **Activity track** for surface lookup purposes
- A **Surface lookup failure** aborts `--surface` processing for the whole activity track
- An **Unknown surface** belongs to a **Split segment** after successful route data acquisition
- A **Normalized surface** keeps the existing public label vocabulary
- A **Surface cache** is part of `--surface` behavior, not a separate CLI mode
- A **Surface cache** can satisfy route data acquisition when a fresh Overpass request fails
- A **Surface bbox buffer** is internal and fixed at 250 m for now
- A **Split polyline** is the geometry used to match a **Split segment** to OSM ways
- A **Surface match** prefers longest overlap with the split polyline before using distance as a tie-breaker
- A **Surface pipeline** keeps acquisition, geometry preparation, matching, and normalization as separate implementation responsibilities

## Example dialogue

> **Dev:** "Should `--surface` run against the GPX file format or the **Activity track**?"
> **Domain expert:** "Run it against the **Activity track** so GPX and FIT inputs behave the same."

## Flagged ambiguities

- "GPX route" was used to mean the parsed input geometry — resolved: use **Activity track** for the parsed point sequence regardless of file format.
- "One route" could mean each contiguous recording section — resolved: surface lookup uses one **Activity track** per CLI input, even if the recording has pauses.
- "Unknown" could mean request failure or a legitimate no-match case — resolved: request failure aborts the run; **Unknown surface** is only a split-level result after successful acquisition.
- "Surface" could mean raw OSM tag or output label — resolved: user output uses **Normalized surface** labels, preserving the existing vocabulary.
- "Surface cache" could sound like an advanced toggle — resolved: cache stays internal for now, with no `--surface-cache` flag.
- "Strict failure" could imply bypassing cached data — resolved: cached route data is valid acquisition output and may be used when a fresh request fails.
- "Buffer" could refer to user configuration or matching radius — resolved: **Surface bbox buffer** is internal route acquisition padding.
- "Split geometry" could mean a midpoint or straight segment — resolved: matching uses a reconstructed **Split polyline** from the activity track.
- "Best match" could mean closest OSM way — resolved: **Surface match** means overlap-first, then distance.
- "Surface service" could mean one large module — resolved: **Surface pipeline** responsibilities should stay separate.
