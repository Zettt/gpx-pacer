# GPX Pacer

A CLI tool to generate pacing spreadsheets from GPX files for ultra running.

## Features

- Split by fixed distance (1km, 5km, 1mi, etc.)
- Split by waypoints (aid stations from GPX)
- Post-race analysis mode from recorded activity GPX files
- Calculates elevation gain/loss and grade per segment
- Calculates net elevation change per split (Gain - Loss)
- Optional: Detects road surface type (Asphalt, Gravel, etc.) using OpenStreetMap data
- Multiple output formats: CSV (default) or JSON

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

### Post-Race Analysis

Use a recorded activity GPX to generate compact split summaries with actual elapsed time,
pace, and watch metrics such as heart rate, cadence, and temperature.

```bash
# Analyze a recorded activity in 1km splits
uv run gpx-pacer data/Freiburg_Marathon_2026_Recording.gpx -m analysis

# Analyze a recorded activity in 100m splits
uv run gpx-pacer data/Freiburg_Marathon_2026_Recording.gpx -m analysis -d 0.1
```

### Surface Detection (Optional)

To automatically detect surface types for each split (requires internet connection):

```bash
uv run gpx-pacer course.gpx --surface
```

This queries the OpenStreetMap Overpass API for each split midpoint.

> **Note:** This uses a free, public Overpass API instance which is rate-limited. Processing may be slower than usual due to these limits and network latency.

### JSON Output

Export as structured JSON instead of CSV:

```bash
uv run gpx-pacer course.gpx -f json
```

The JSON output uses the structure `{ "metadata": {...}, "splits": [...] }`, making it easy to consume programmatically.

### Options

| Flag           | Short | Default              | Description                            |
| -------------- | ----- | -------------------- | -------------------------------------- |
| `--output`     | `-o`  | `<input>_pacing.csv` | Output file path                       |
| `--split-mode` | `-m`  | `distance`           | `distance`, `waypoint`, or `analysis`  |
| `--split-dist` | `-d`  | `1.0`                | Distance per split                     |
| `--unit`       | `-u`  | `km`                 | `km` or `mi`                           |
| `--format`     | `-f`  | `csv`                | Output format: `csv` or `json`         |
| `--surface`    |       | `False`              | Query surface type (requires internet) |

## Output

### CSV (default)

The generated CSV contains:

**Route Data (calculated)**

- Segment Name
- Distance (cumulative)
- Split Length
- Gain / Loss (elevation in meters)
- Net Change (elevation in meters)
- Surface (optional)
- Grade %

**Planning Columns (empty for you to fill)**

- Target Pace
- Split Time
- Arrival Time
- Station Delay

Open in Excel or Google Sheets to complete your race plan.

### JSON

The JSON output contains:

```json
{
  "metadata": {
    "filename": "course.gpx",
    "total_dist": 73932.71
  },
  "splits": [
    {
      "segment_name": "1.0 km",
      "distance_km": 1.0,
      "split_length_km": 1.0,
      "gain_m": 40,
      "loss_m": 8,
      "net_change_m": 32,
      "cumulative_elevation_m": 32,
      "grade_pct": 3.2
    }
  ]
}
```

The `surface` field is included in each split only when `--surface` is used.

### Analysis Output

When `-m analysis` is used, the output contains split summaries only. CSV and JSON include:

- Start and end distance
- Start and end time
- Elapsed time and pace
- Average and max heart rate
- Average cadence
- Average temperature
- Elevation gain, loss, net change, and grade

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy src/
```

## License

MIT
