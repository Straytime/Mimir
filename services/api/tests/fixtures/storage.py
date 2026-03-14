from pathlib import Path

import pytest


@pytest.fixture
def temp_artifact_dir(tmp_path: Path) -> Path:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    return artifact_dir
