# GPX Pacer

A CLI tool to generate pacing spreadsheets from GPX files for ultra running.

## Features

- Split by fixed distance (1km, 5km, 1mi, etc.)
- Split by waypoints (aid stations from GPX)
- Calculates elevation gain/loss and grade per segment
- Outputs CSV with planning columns for race strategy

## Installation

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repo-url>
cd gpx-pacer
uv sync
```

## Usage

### Fixed Distance Splits (default)

```bash
# 1km splits (default)
uv run gpx-pacer course.gpx

# 5km splits
uv run gpx-pacer course.gpx -d 5

# 1 mile splits
uv run gpx-pacer course.gpx -u mi -d 1
```

### Waypoint Splits (Aid Stations)

If your GPX file contains `<wpt>` elements for aid stations:

```bash
uv run gpx-pacer course.gpx -m waypoint
```

> **Note:** Waypoints more than 100m from the track will trigger a warning.

### Options

| Flag           | Short | Default              | Description              |
| -------------- | ----- | -------------------- | ------------------------ |
| `--output`     | `-o`  | `<input>_pacing.csv` | Output file path         |
| `--split-mode` | `-m`  | `distance`           | `distance` or `waypoint` |
| `--split-dist` | `-d`  | `1.0`                | Distance per split       |
| `--unit`       | `-u`  | `km`                 | `km` or `mi`             |

## Output

The generated CSV contains:

**Route Data (calculated)**

- Segment Name
- Distance (cumulative)
- Split Length
- Gain / Loss (elevation in meters)
- Grade %

**Planning Columns (empty for you to fill)**

- Target Pace
- Split Time
- Arrival Time
- Station Delay

Open in Excel or Google Sheets to complete your race plan.

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/
```

## License

MIT
