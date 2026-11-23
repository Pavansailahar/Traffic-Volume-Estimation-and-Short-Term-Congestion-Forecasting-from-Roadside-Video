from __future__ import annotations

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.common import pill, setup, source_note
from src.common.config import Settings
from src.services.results import RunStore

setup("Model Evaluation", "What has been measured, under which conditions, and what is still open.")
settings = Settings()

st.subheader("Acceptance status")
rows = [
    ("O2 vs O3 comparison", "Not started", "warn", "O3 is built after O2 is frozen (Phase 9)."),
    ("Detection (P, R, mAP50, mAP50-95)", "Development run", "info", "UA-DETRAC subset, pretrained model, by weather."),
    ("Tracking (IDF1, MOTA, ID switches)", "Not measured", "warn", "Needs UA-DETRAC track evaluation (Phase 6)."),
    ("Counting (MAE, RMSE, accuracy)", "Not measured", "bad", "No reference counts yet: hand counts planned."),
    (
        "Forecasting (MAE, RMSE by horizon)",
        "Baselines only",
        "info",
        "Volume backtests per run; congestion labels pending.",
    ),
    ("KPI-1 … KPI-6", "Not measured", "warn", "All targets are relative to the frozen O2 reference."),
]
for name, status, kind, note in rows:
    c1, c2, c3 = st.columns([1.3, 0.7, 2])
    c1.write(f"**{name}**")
    c2.markdown(pill(status, kind), unsafe_allow_html=True)
    c3.caption(note)

st.divider()
st.subheader("Detection on UA-DETRAC, by condition")
reports = sorted((settings.reports_root / "phase5").glob("detection_ua_detrac_*.json"))
if not reports:
    st.info(
        "The UA-DETRAC evaluation has not run yet (its download is still in progress). "
        "Run `python scripts/eval_detection_ua_detrac.py` when the download completes."
    )
else:
    rec = json.loads(reports[-1].read_text(encoding="utf-8"))
    by = pd.DataFrame(rec["results"]["by_condition"]).T.reset_index(names="condition")
    cols = ["condition", "images", "gt_objects", "precision", "recall", "ap50", "ap50_95", "small_recall"]
    st.dataframe(by[cols].round(3), hide_index=True, width="stretch")
    long = by.melt(id_vars="condition", value_vars=["ap50", "ap50_95", "recall"], var_name="metric")
    fig = px.bar(long, x="condition", y="value", color="metric", barmode="group", height=320, range_y=[0, 1])
    st.plotly_chart(fig, width="stretch")
    source_note(f"{reports[-1].name} · development data, not acceptance evidence")

st.divider()
st.subheader("Condition-wise comparison of processed runs")
st.caption(
    "Observational only: these show how the pipeline behaves at night versus by day. They are not accuracy "
    "figures because there are no reference counts yet."
)
runs = [r for r in RunStore().list() if r.name != "smoke"]
if runs:
    table = []
    for r in runs:
        res = r.results
        cond = res.get("condition_share", {})
        table.append(
            {
                "run": r.name,
                "minutes": round(res.get("duration_s", 0) / 60, 1),
                "vehicles counted": res.get("count_events"),
                "tracks": res.get("tracks"),
                "degraded frames": res.get("degraded_frame_share"),
                "night share": round(sum(v for k, v in cond.items() if "night" in k), 3),
                "dense-occlusion share": round(sum(v for k, v in cond.items() if "dense" in k), 3),
                "median confidence": round(r.detections["confidence"].median(), 3) if not r.detections.empty else None,
                "p95 latency ms": round(res["latency_ms"]["total"]["p95_ms"], 1),
            }
        )
    st.dataframe(pd.DataFrame(table), hide_index=True, width="stretch")
