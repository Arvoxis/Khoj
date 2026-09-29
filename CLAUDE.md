# KHOJ — leaderless drone swarm for collapsed-building search

INNOHACK 2.0 build. A swarm of drones searches for survivors with **no GPS, no pilot and no
central controller**. Each drone runs the same logic and coordinates over an ESP-NOW mesh.

Repo: `github.com/Arvoxis/Khoj`

## The one invariant that matters

**`engine/` is pure Python 3 stdlib. It has zero third-party dependencies, deliberately.**

That is what lets the same code run in simulation on a laptop and headless on the drone.
Do not import numpy, torch, fastapi or anything else into `engine/`. If you need a dependency
for something, that something belongs in `backend/`, `detector/` or `scripts/` instead.

## Layout

| Path | What lives there | Deps |
|---|---|---|
| `engine/` | Swarm logic: `swarm.py`, `belief.py`, `perception.py`, `world.py`, `protocol.py` | **stdlib only** |
| `backend/` | FastAPI dashboard server, WebSocket state push | fastapi, uvicorn |
| `detector/` | YOLOv11 survivor detection, Jetson/TensorRT export | torch (own `requirements.txt`) |
| `khoj/sim/` | Simulation harness + hardware-in-the-loop feeder | pyserial |
| `khoj/firmware/` | ESP32 ESP-NOW mesh firmware | — |
| `scripts/` | `viewer.py`, `metrics.py` — run analysis plots | numpy, matplotlib |

Dependencies are split across three requirement files on purpose. `requirements.txt` is the
laptop stack; `detector/requirements.txt` is CUDA-specific and separate.

## Conda envs

Three layers, three answers:

- `engine/` — **stdlib only**, runs under any interpreter. That's the whole point.
- `backend/`, `khoj/sim/` — conda **`back`** (fastapi, uvicorn, numpy).
  `matplotlib` for `scripts/viewer.py` lives in `ml`, so run plotting tools from `ml`.
- `detector/` — conda **`ml`** (torch+cu121, ultralytics). Never mix this into `back`.

## Two grids — not a contradiction

Docs quote both 60×40 and 32×32. They are different things; say which one you mean:

| Grid | Size | Where |
|---|---|---|
| Sim **world** grid | **60×40** | `WorldConfig.grid_w/grid_h` in `engine/world.py` — the laptop's terrain |
| **SimState / board** grid | **32×32** | fixed by `docs/SIMSTATE_CONTRACT.md`; `GRID_N` in the mesh firmware clamps goals to it |

`BeliefStore.prob_grid(w, h)` is parameterised and renders into whichever the caller passes.

## Rules

- Detection model config is `detector/khoj_indoor.yaml`, which points at the Kaggle **C2A**
  disaster-scenario dataset (single class `person`). The `SARD_YOLO.v1-original.yolov11/`
  folder is the earlier aerial-SAR training set — C2A is the current indoor fine-tune.
- Export for the drone goes through `detector/export_jetson.py` (TensorRT FP16).
- `runs/` is YOLO training output — artifacts, never commit.
- Prefer extending the simulation in `khoj/sim/` over testing against real hardware.
- `khoj/HANDOFF.md` and `khoj/docs/` are the teammate-facing docs — keep them accurate.

## Running

```bash
python engine/run_sim.py                # headless swarm simulation
./khoj/run_dashboard.ps1                # dashboard (PowerShell)
python scripts/viewer.py                # replay a run visually
```
