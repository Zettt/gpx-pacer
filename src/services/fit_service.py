from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from typing import Any

import fitdecode

from src.model.data import TrackPoint, Waypoint
from src.lib.geo_utils import haversine_distance


FIT_SESSION_FIELDS = [
    "sport_profile_name",
    "total_elapsed_time",
    "total_timer_time",
    "total_moving_time",
    "time_standing",
    "total_distance",
    "avg_speed",
    "enhanced_avg_speed",
    "max_speed",
    "enhanced_max_speed",
    "avg_heart_rate",
    "max_heart_rate",
    "min_heart_rate",
    "avg_running_cadence",
    "max_running_cadence",
    "avg_vertical_oscillation",
    "avg_stance_time_percent",
    "avg_stance_time",
    "avg_vertical_ratio",
    "avg_stance_time_balance",
    "avg_step_length",
    "enhanced_avg_respiration_rate",
    "enhanced_max_respiration_rate",
    "enhanced_min_respiration_rate",
    "avg_power",
    "max_power",
    "normalized_power",
    "training_load_peak",
    "total_training_effect",
    "total_anaerobic_training_effect",
    "avg_spo2",
    "avg_stress",
    "sdrr_hrv",
    "rmssd_hrv",
    "total_calories",
    "total_ascent",
    "total_descent",
    "avg_temperature",
    "max_temperature",
    "min_temperature",
]

FIT_LAP_FIELDS = [
    "message_index",
    "start_time",
    "timestamp",
    "total_elapsed_time",
    "total_timer_time",
    "total_moving_time",
    "time_standing",
    "total_distance",
    "avg_speed",
    "enhanced_avg_speed",
    "max_speed",
    "enhanced_max_speed",
    "avg_heart_rate",
    "max_heart_rate",
    "avg_running_cadence",
    "max_running_cadence",
    "avg_vertical_oscillation",
    "avg_stance_time_percent",
    "avg_stance_time",
    "avg_vertical_ratio",
    "avg_stance_time_balance",
    "avg_step_length",
    "enhanced_avg_respiration_rate",
    "enhanced_max_respiration_rate",
    "avg_power",
    "max_power",
    "normalized_power",
    "total_calories",
    "total_ascent",
    "total_descent",
    "avg_temperature",
    "max_temperature",
    "min_temperature",
]

FIT_TIME_IN_ZONE_FIELDS = [
    "reference_mesg",
    "reference_index",
    "time_in_hr_zone",
    "time_in_power_zone",
    "hr_zone_high_boundary",
    "power_zone_high_boundary",
    "threshold_heart_rate",
    "functional_threshold_power",
    "hr_calc_type",
    "pwr_calc_type",
]

FIT_WORKOUT_FIELDS = [
    "wkt_name",
    "wkt_description",
    "num_valid_steps",
    "sport",
    "sub_sport",
]

FIT_WORKOUT_STEP_FIELDS = [
    "message_index",
    "duration_type",
    "duration_distance",
    "target_type",
    "custom_target_speed_low",
    "custom_target_speed_high",
    "notes",
    "intensity",
]

FIT_COURSE_POINT_FIELDS = [
    "message_index",
    "timestamp",
    "distance",
    "name",
    "type",
    "position_lat",
    "position_long",
]


def _normalize_scalar(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, tuple):
        return [_normalize_scalar(item) for item in value]
    if isinstance(value, list):
        return [_normalize_scalar(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "value"):
        return _normalize_scalar(value.value)
    if hasattr(value, "name"):
        return value.name
    return str(value)


def _semicircles_to_degrees(value: int | float | None) -> float | None:
    if value is None:
        return None
    return float(value) * (180.0 / 2**31)


def _to_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _to_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _message_to_dict(message: fitdecode.FitDataMessage, fields: Iterable[str]) -> dict[str, Any]:
    values_by_name = {field.name: field.value for field in message.fields}
    entry: dict[str, Any] = {}
    for name in fields:
        value = values_by_name.get(name)
        if value is None:
            continue
        if name in {"position_lat", "position_long"}:
            entry[name] = _semicircles_to_degrees(value)
        else:
            entry[name] = _normalize_scalar(value)
    return entry


def _course_point_name(message_values: dict[str, Any]) -> str | None:
    name = message_values.get("name")
    if name:
        return str(name)
    point_type = message_values.get("type")
    if point_type:
        return str(_normalize_scalar(point_type)).replace("_", " ").title()
    return None


def parse_fit(file_path: str) -> tuple[list[TrackPoint], list[Waypoint], dict[str, Any]]:
    track_points: list[TrackPoint] = []
    waypoints: list[Waypoint] = []
    metadata: dict[str, Any] = {}

    fit_session: dict[str, Any] | None = None
    fit_laps: list[dict[str, Any]] = []
    fit_time_in_zone: list[dict[str, Any]] = []
    fit_workout: dict[str, Any] | None = None
    fit_workout_steps: list[dict[str, Any]] = []
    fit_course_points: list[dict[str, Any]] = []

    last_track_point: TrackPoint | None = None

    with fitdecode.FitReader(file_path) as fit:
        for frame in fit:
            if not isinstance(frame, fitdecode.FitDataMessage):
                continue

            values_by_name = {field.name: field.value for field in frame.fields}

            if frame.name == "record":
                lat = _semicircles_to_degrees(values_by_name.get("position_lat"))
                lon = _semicircles_to_degrees(values_by_name.get("position_long"))
                if lat is None or lon is None:
                    continue

                distance_from_start = _to_optional_float(values_by_name.get("distance"))
                if distance_from_start is None:
                    if last_track_point is None:
                        distance_from_start = 0.0
                    else:
                        distance_from_start = last_track_point.distance_from_start + haversine_distance(
                            last_track_point.lat,
                            last_track_point.lon,
                            lat,
                            lon,
                        )

                track_point = TrackPoint(
                    lat=lat,
                    lon=lon,
                    ele=_to_optional_float(
                        values_by_name.get("enhanced_altitude", values_by_name.get("altitude"))
                    ),
                    distance_from_start=distance_from_start,
                    timestamp=values_by_name.get("timestamp"),
                    heart_rate_bpm=_to_optional_int(values_by_name.get("heart_rate")),
                    cadence=_to_optional_int(values_by_name.get("cadence")),
                    temperature_c=_to_optional_float(values_by_name.get("temperature")),
                    speed_mps=_to_optional_float(
                        values_by_name.get("enhanced_speed", values_by_name.get("speed"))
                    ),
                    power_w=_to_optional_int(values_by_name.get("power")),
                    respiration_rate_brpm=_to_optional_float(
                        values_by_name.get("enhanced_respiration_rate")
                    ),
                    vertical_oscillation_mm=_to_optional_float(values_by_name.get("vertical_oscillation")),
                    stance_time_ms=_to_optional_float(values_by_name.get("stance_time")),
                    stance_time_percent=_to_optional_float(values_by_name.get("stance_time_percent")),
                    vertical_ratio_pct=_to_optional_float(values_by_name.get("vertical_ratio")),
                    stance_time_balance_pct=_to_optional_float(values_by_name.get("stance_time_balance")),
                    step_length_mm=_to_optional_float(values_by_name.get("step_length")),
                )
                track_points.append(track_point)
                last_track_point = track_point
                continue

            if frame.name == "course_point":
                entry = _message_to_dict(frame, FIT_COURSE_POINT_FIELDS)
                if entry:
                    fit_course_points.append(entry)

                lat = _semicircles_to_degrees(values_by_name.get("position_lat"))
                lon = _semicircles_to_degrees(values_by_name.get("position_long"))
                name = _course_point_name(values_by_name)
                if lat is not None and lon is not None and name:
                    waypoints.append(Waypoint(name=name, lat=lat, lon=lon))
                continue

            if frame.name == "session" and fit_session is None:
                fit_session = _message_to_dict(frame, FIT_SESSION_FIELDS)
                continue

            if frame.name == "lap":
                entry = _message_to_dict(frame, FIT_LAP_FIELDS)
                if entry:
                    fit_laps.append(entry)
                continue

            if frame.name == "time_in_zone":
                entry = _message_to_dict(frame, FIT_TIME_IN_ZONE_FIELDS)
                if entry:
                    fit_time_in_zone.append(entry)
                continue

            if frame.name == "workout" and fit_workout is None:
                fit_workout = _message_to_dict(frame, FIT_WORKOUT_FIELDS)
                continue

            if frame.name == "workout_step":
                entry = _message_to_dict(frame, FIT_WORKOUT_STEP_FIELDS)
                if entry:
                    fit_workout_steps.append(entry)

    if fit_session:
        metadata["fit_session"] = fit_session
    if fit_laps:
        metadata["fit_laps"] = fit_laps
    if fit_time_in_zone:
        metadata["fit_time_in_zone"] = fit_time_in_zone
    if fit_workout:
        metadata["fit_workout"] = fit_workout
    if fit_workout_steps:
        metadata["fit_workout_steps"] = fit_workout_steps
    if fit_course_points:
        metadata["fit_course_points"] = fit_course_points

    return track_points, waypoints, metadata
