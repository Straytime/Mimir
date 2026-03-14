from pathlib import Path

from tests.fixtures import FakeClock, FakeIdGenerator


def test_fixtures_package_exports_stage_zero_building_blocks(
    temp_artifact_dir: Path,
) -> None:
    clock = FakeClock()
    id_generator = FakeIdGenerator(prefix="tsk")

    assert clock.now().isoformat() == "2026-01-01T00:00:00+00:00"
    assert id_generator.next() == "tsk_0001"
    assert temp_artifact_dir.name == "artifacts"
