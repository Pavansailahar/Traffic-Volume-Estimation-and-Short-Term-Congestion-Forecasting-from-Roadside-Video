"""Integration: full pipeline on a few seconds of a real clip (skipped without data/weights)."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from src.common.config import PROJECT_ROOT, Settings, load_config
from src.counting.line_counter import CameraGeometry

pytestmark = [pytest.mark.slow, pytest.mark.needs_data]
SETTINGS = Settings()
CLIPS = sorted((SETTINGS.data_root / "raw" / "barbados_traffic" / "normanniles1").glob("*13-0*.mp4"))
WEIGHTS = SETTINGS.models_root / "detection" / "yolo11n.pt"


@pytest.mark.skipif(not CLIPS or not WEIGHTS.is_file(), reason="needs a camera-1 clip and detector weights")
def test_process_clips_writes_all_outputs(tmp_path) -> None:  # noqa: ANN001
    from src.detection.detector import UltralyticsDetector
    from src.pipeline.runner import process_clips

    config = load_config(PROJECT_ROOT / "configs" / "o2_a.yaml")
    detector = UltralyticsDetector(config.detection, SETTINGS.models_root, device="cpu")
    geometry = CameraGeometry.load(PROJECT_ROOT / "configs" / "cameras" / "normanniles1.yaml")
    summary = process_clips(
        CLIPS[:1],
        config,
        detector,
        tmp_path,
        geometry=geometry,
        camera_id="normanniles1",
        stride=2,
        max_frames=60,
        run_name="it",
    )
    assert summary.frames == 60
    for name in (
        "frames.csv",
        "detections.csv",
        "tracks.csv",
        "track_points.csv",
        "events.csv",
        "intervals.csv",
        "annotated.mp4",
        "run.json",
    ):
        assert (tmp_path / name).is_file(), name
    record = json.loads((tmp_path / "run.json").read_text(encoding="utf-8"))
    assert record["results"]["annotated_video_h264"] is True
    assert record["results"]["validation_status"].startswith("NOT VALIDATED")
    frames = pd.read_csv(tmp_path / "frames.csv")
    assert len(frames) == 60 and set(frames["reliability"]) <= {"ok", "degraded"}
    intervals = pd.read_csv(tmp_path / "intervals.csv")
    assert set(intervals["source"]) <= {"estimated"}
