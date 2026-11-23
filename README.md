# DSCI-41 — Traffic Volume Estimation and Short-Term Congestion Forecasting from Roadside Video

KL University two-semester engineering capstone. Specification (single source of truth):
[docs/UseCase.pdf](docs/UseCase.pdf).

> **Status (2026-11-23): Phase 5 of 15.** A working O2-A vertical slice (ingestion → YOLO11n detection →
> ByteTrack → line counting → volume baselines → Streamlit dashboard) runs on real Barbados video. Counts are
> **estimates not yet validated against reference counts**; no KPI has been measured. See
> [DEVELOPMENT_ROADMAP.md](DEVELOPMENT_ROADMAP.md).

## What this project builds

Roadside video → detection → classification → tracking → (perspective-aware) counting → interval traffic volumes
→ short-term congestion forecast → operator dashboard. Every result goes through an acceptance and negative-test
harness that checks it against reference counts across occlusion, rain and night conditions.

| Objective | Meaning |
|-----------|---------|
| O2 | Reference: mixed vehicle types and oblique perspective |
| O3 | Contribution: sustain accuracy under occlusion, rain and low light (separately switchable) |
| O4 | Integrated system: forecast near-term congestion from estimated volumes |
| O5 | Independent acceptance across conditions (AC-1…AC-4, NT-1…NT-5, KPI-1…KPI-6) |

## Planning documents

[PROJECT_ANALYSIS](PROJECT_ANALYSIS.md) · [REQUIREMENTS](REQUIREMENTS.md) · [DATASET_RESEARCH](DATASET_RESEARCH.md) ·
[SYSTEM_ARCHITECTURE](SYSTEM_ARCHITECTURE.md) · [DEVELOPMENT_ROADMAP](DEVELOPMENT_ROADMAP.md) ·
[RISK_REGISTER](RISK_REGISTER.md)

## Setup (Windows)

Prerequisites: Windows 10/11, the Python Install Manager (`py`), [uv](https://docs.astral.sh/uv/), FFmpeg on PATH,
Git.

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_env.ps1
```

This script:
1. installs the signed python.org Python 3.11 if it is missing,
2. creates a virtual environment at `%USERPROFILE%\dsci41\venv`, outside OneDrive,
3. installs the exact locked dependencies from `uv.lock` (CPU PyTorch),
4. runs `scripts/check_env.py`.

The script uses signed python.org Python because Windows Smart App Control blocks uv's unsigned interpreter and
launcher. If you have no Smart App Control restriction, `uv sync` alone also works.

Run the tests:

```powershell
& "$HOME\dsci41\venv\Scripts\python.exe" -m pytest -q
```

Environment report:

```powershell
& "$HOME\dsci41\venv\Scripts\python.exe" scripts\check_env.py
```

Using pip instead of uv: `requirements.txt` is exported from `uv.lock`. The torch wheels come from the CPU index:
`pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu`.

Process a video end to end (detect → track → count), e.g. a 23-minute Barbados window from camera 1:

```powershell
& "$HOME\dsci41env\Scripts\python.exe" scripts\process_video.py --glob "normanniles1_2025-10-21-13-*.mp4" --camera normanniles1 --name cam1_morning
```

Open the operator dashboard (http://localhost:8501):

```powershell
& "$HOME\dsci41env\Scripts\python.exe" -m streamlit run dashboardpp.py
```

Docker (clean-environment test run, CPU):

```powershell
docker compose run --rm tests
```

## Configuration

* Machine settings: environment variables or `.env`. See [.env.example](.env.example).
  Large data, model weights and logs live under `DSCI41_DATA_ROOT`, `DSCI41_MODELS_ROOT` and `DSCI41_LOG_DIR`.
* Experiment settings: [configs/](configs). They are validated YAML, unknown keys are rejected, and each config has a
  stable hash. `o2_a.yaml` and `o2_b.yaml` are the two O2 reference candidates.

## Repository layout

```
src/common/        shared types, config, provenance, hardware, logging     (implemented)
src/ingestion, detection, tracking, counting, monitoring, forecasting (baselines),
    pipeline, services, datasets, evaluation                               (implemented, O2-A slice)
src/perspective, enhancement, classification, api                          (skeleton only)
dashboard/         Streamlit app, 8 pages                                    (reads pipeline runs)
configs/           validated YAML experiment configs
scripts/           setup_env.ps1, check_env.py
tests/             unit / integration / acceptance / negative
data/              manifests and tiny samples only (raw data under DSCI41_DATA_ROOT)
reports/           committed experiment and acceptance reports
```

## Licences

Code licence: to be decided by the team. Ultralytics YOLO is AGPL-3.0, which constrains distribution (RISK R-09).
The datasets have their own licences (CC BY-SA 4.0 for Barbados; research-only for UA-DETRAC and AI City). See
DATASET_RESEARCH.md. Raw data is never committed.
