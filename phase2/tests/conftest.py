import pandas as pd
import pytest

from pipeline.config import PipelineConfig


@pytest.fixture
def cfg():
    return PipelineConfig(data_end=pd.Timestamp("2025-12-31"))
