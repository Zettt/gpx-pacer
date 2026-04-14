from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

@dataclass
class TrackPoint:
    lat: float
    lon: float
    ele: Optional[float] = None
    distance_from_start: float = 0.0
    timestamp: Optional[datetime] = None
    heart_rate_bpm: Optional[int] = None
    cadence: Optional[int] = None
    temperature_c: Optional[float] = None

@dataclass
class Waypoint:
    name: str
    lat: float
    lon: float
    distance_from_start: float = 0.0

@dataclass
class SplitSegment:
    start_distance: float
    end_distance: float
    length: float
    elevation_gain: float
    elevation_loss: float
    name: Optional[str] = None
    surface: Optional[str] = None
    
    @property
    def grade(self) -> float:
        if self.length == 0:
            return 0.0
        return ((self.elevation_gain - self.elevation_loss) / self.length) * 100

    @property
    def net_change(self) -> float:
        return self.elevation_gain - self.elevation_loss


@dataclass
class AnalysisSplitSegment(SplitSegment):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    elapsed_seconds: Optional[float] = None
    pace_seconds_per_km: Optional[float] = None
    average_heart_rate_bpm: Optional[float] = None
    max_heart_rate_bpm: Optional[int] = None
    average_cadence: Optional[float] = None
    average_temperature_c: Optional[float] = None
    point_count: int = 0

@dataclass
class PacingPlan:
    metadata: Dict[str, Any]
    splits: List[SplitSegment | AnalysisSplitSegment] = field(default_factory=list)
