from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

@dataclass
class TrackPoint:
    lat: float
    lon: float
    ele: Optional[float] = None
    distance_from_start: float = 0.0

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
class PacingPlan:
    metadata: Dict[str, Any]
    splits: List['SplitSegment'] = field(default_factory=list)
