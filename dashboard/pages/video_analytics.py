from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

import streamlit as st

from dashboard.common import select_run, setup, source_note
from src.common.config import PROJECT_ROOT, Settings, load_config
from src.common.hardware import select_device
from src.counting.line_counter import CameraGeometry
from src.pipeline.runner import process_clips

setup("Video Analytics", "Process a sample window or your own video, then watch and download the results.")
settings = Settings()
CAMERAS = sorted(p.stem for p in (PROJECT_ROOT / "configs" / "cameras").glob("*.yaml"))


@st.cache_resource(show_spinner="Loading detector…")
def detector(model: str):  # noqa: ANN201
    from src.detection.detector import UltralyticsDetector

    cfg = load_config(PROJECT_ROOT / "configs" / "o2_a.yaml")
    return UltralyticsDetector(cfg.detection, settings.models_root, device=select_device(settings.device))


tab_run, tab_view = st.tabs(["Process video", "View results"])

with tab_run:
    source = st.radio("Input", ["Sample clips (Barbados, local copy)", "Upload a video"], horizontal=True)
    clips: list[Path] = []
    camera_id = "uploaded"
    if source.startswith("Sample"):
        raw = settings.data_root / "raw" / "barbados_traffic"
        cams = sorted(p.name for p in raw.iterdir() if p.is_dir()) if raw.is_dir() else []
        if not cams:
            st.warning("No sample clips found under the data folder.")
        else:
            c1, c2, c3 = st.columns(3)
            camera_id = c1.selectbox("Camera", cams)
            files = sorted((raw / camera_id).glob("*.mp4"))

            def local(p: Path) -> str:
                ts = datetime.strptime(
                    re.search(r"_(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", p.name).group(1), "%Y-%m-%d-%H-%M-%S"
                )
                return (ts - timedelta(hours=4)).strftime("%d %b %H:%M")

            start = c2.selectbox("Start (local time)", files, format_func=local)
            n = c3.number_input("Minutes", 1, 23, 2)
            i = files.index(start)
            clips = files[i : i + int(n)]
    else:
        up = st.file_uploader("MP4 or AVI", type=["mp4", "avi"])
        if up is not None:
            dest = settings.data_root / "uploads" / up.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(up.getbuffer())
            clips = [dest]
            st.caption(f"Saved to {dest}")

    c1, c2, c3 = st.columns(3)
    geometry_choice = c1.selectbox(
        "Counting lines", ["none (detect + track only)", *CAMERAS], index=1 if camera_id in CAMERAS else 0
    )
    stride = c2.select_slider("Frame stride", [1, 2, 3, 4], value=2, help="Process every n-th frame")
    name = c3.text_input("Run name", value=f"{camera_id}_{datetime.now():%H%M%S}")

    st.caption(
        "Processing runs inside this page: stay on it until it finishes. Switching pages or changing a "
        "setting stops the run. For long windows use scripts/process_video.py."
    )
    if st.button("Process", type="primary", disabled=not clips):
        geometry = (
            None
            if geometry_choice.startswith("none")
            else CameraGeometry.load(PROJECT_ROOT / "configs" / "cameras" / f"{geometry_choice}.yaml")
        )
        bar = st.progress(0.0, text="Starting…")

        def progress(done: int, total: int, message: str) -> None:
            bar.progress(min(done / max(total, 1), 1.0), text=f"{done:,}/{total:,} frames · {message}")

        try:
            summary = process_clips(
                clips,
                load_config(PROJECT_ROOT / "configs" / "o2_a.yaml"),
                detector("yolo11n"),
                settings.data_root / "runs" / "pipeline" / name,
                geometry=geometry,
                camera_id=camera_id,
                stride=stride,
                progress=progress,
                run_name=name,
            )
        except ValueError as exc:
            bar.empty()
            st.error(f"Could not process the video: {exc}")
        else:
            bar.progress(1.0, text="Done")
            st.success(
                f"{summary.frames:,} frames, {summary.tracks:,} tracks, {summary.events:,} vehicles counted "
                f"in {summary.wall_s:.0f} s. Select **{name}** in the sidebar to explore it."
            )
            st.session_state["selected_run"] = name
            st.cache_data.clear()

with tab_view:
    run = select_run("va")
    if run is not None:
        if run.video:
            st.video(str(run.video))
            source_note("annotated.mp4 · boxes, track IDs, trails, counting lines and running totals")
        else:
            st.info("This run has no annotated video.")
        st.subheader("Downloads")
        cols = st.columns(5)
        for col, fname in zip(
            cols, ["intervals.csv", "events.csv", "tracks.csv", "detections.csv", "run.json"], strict=True
        ):
            p = run.path / fname
            if p.is_file():
                col.download_button(fname, p.read_bytes(), file_name=f"{run.name}_{fname}", width="stretch")
        st.caption("Barbados video carries an IWCP re-use notice: keep annotated videos local, do not publish them.")
