import pytest
import os
from src.services.gpx_service import parse_gpx

@pytest.fixture
def sample_gpx_path():
    # Return absolute path to sample.gpx
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, 'data', 'sample.gpx')

@pytest.fixture
def sample_track_data(sample_gpx_path):
    return parse_gpx(sample_gpx_path)
