# KHOJ — a leaderless drone swarm for GPS-denied search & rescue

> *Khoj* (खोज) — "the search."

KHOJ is an autonomous drone swarm built to find survivors inside **collapsed
buildings**, where there is **no GPS**, no pilot, and no central controller. The
drones coordinate through a **leaderless market auction**, and no survivor is
ever reported until **two independent drones confirm it**. Kill any drone
mid-mission and the rest re-coordinate in under two seconds.

**Three ideas in one line:** *Leaderless. GPS-denied. Self-confirming.*

---

## Why it works this way

> **The laptop owns reality. The boards own the decisions. They never swap roles.**

In our hardware-in-the-loop (HIL) rig, the laptop *simulates the world* — each
drone's body, what its camera sees, the radio it hears — and streams that to each
board over a private USB link. It **never assigns work**. Every goal you see move
on screen was decided on a separate $5 microcontroller, from that board's own
private belief, and agreed by radio. That is what makes this a swarm and not a
puppet show.

---

## The algorithms

| Component | What it does |
|---|---|
| **Leaderless auction** | Each board bids `expected information ÷ time-to-reach` on every open task. Highest bid wins; ties break to the lowest agent ID. Every board runs the identical rule on the same broadcast data, so they all converge on the same winner — no auctioneer, no round-trips. *(Task class ST-SR-IA, Gerkey & Matarić.)* |
| **Log-odds belief fusion** | Each survivor hypothesis is a belief in log-odds; independent detections add evidence. Confirmation requires posterior ≥ 0.80 **and ≥ 2 distinct agents** — a single sensor can never self-confirm, by construction. |
| **Trust & quarantine** | Per-agent Beta reliability prior. A sensor whose claims keep getting dismissed is auto-benched; the swarm keeps working. |
| **RF localization** | Distributed RSSI gradient-ascent. Drones hill-climb toward the strongest signal instead of trilaterating (which hallucinates through concrete), converging on a victim's phone no camera can see. |
| **Failure detection** | 5 Hz heartbeat over the mesh; a peer is declared dead in < 2 s and its tasks re-auction automatically. |

---

## Proven performance (simulation + bench)

| Metric | Result |
|---|---|
| Survivors confirmed (equal time budget) | **4.23** vs. greedy 1.67 / lawnmower 1.40 / random 2.63 |
| False alarms | **0** across 600 Monte-Carlo runs |
| Detector accuracy | mAP50 **0.934**, recall 0.875 (YOLO11, real SAR imagery) |
| Mesh reliability | **0%** packet loss @ 5 Hz, 5 boards |
| Failure detection | dead peer recognized in **< 2 s** |
| RF localization | converges to **±0.3 grid cells** |

Reproduce the search numbers:

```bash
python -m scripts.metrics --seeds 30 --budget 60
```

---

## Quickstart

The **core engine is pure Python 3 stdlib** — no install needed to run the
simulation. Everything else installs from `requirements.txt`.

```bash
python -m pip install -r requirements.txt
```

**1. Live dashboard** (backend + frontend in two terminals):

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
```bash
python -m http.server 3000 --bind 127.0.0.1 --directory frontend
```
Open <http://127.0.0.1:3000/>.

The backend has three state sources, selected by the `KHOJ_ENGINE` env var:

| `KHOJ_ENGINE` | Source |
|---|---|
| `real` *(default)* | the pure-Python swarm engine — no hardware |
| `fake` | a mock generator for standalone frontend work |
| `hardware` | live ESP32 boards, fed over `/ingest` by the bridge |

**2. Headless simulation & tools:**

```bash
python -m engine.run_sim --ticks 400        # run the swarm, no dashboard
python -m scripts.viewer                     # matplotlib playback
python -m scripts.metrics --seeds 30 --budget 60   # benchmark vs baselines
```

**3. Real detector on the Jetson** (separate GPU env — see
`detector/requirements.txt`):

```bash
python3 detector/jetson_stream.py --engine ~/best.engine --source 0
# then open  http://192.168.55.1:8090  for the live annotated feed
```

**4. Hardware-in-the-loop** (5 flashed boards + the bridge, then run the
dashboard in `hardware` mode):

```bash
python khoj/sim/feeder_real.py --ports COM3 COM13 COM14 COM16
```

---

## Repository layout

```
KHOJ/
├── engine/       swarm auction, log-odds belief fusion, world sim, perception  (stdlib only)
├── detector/     YOLO11 training, Jetson TensorRT export, live camera stream
├── khoj/         hardware: ESP32 mesh firmware + byte-exact USB wire contract
│   ├── firmware/     ESP-NOW mesh + on-device auction (C / PlatformIO)
│   └── sim/          feeder_real.py bridge, protocol.py, wire test
├── backend/      FastAPI + WebSocket state service (fake / real / hardware)
├── frontend/     Canvas dashboard (index.html, app.js, styles.css)
├── dashboard/    simulator state adapters and models
├── scripts/      metrics harness, matplotlib viewer, perception demo
├── tests/        backend & WebSocket checks
└── docs/         state-contract documentation
```

**The wire contract** is byte-exact between firmware and Python:
`khoj/firmware/lib/quorum_proto/quorum_proto.h` ↔ `khoj/sim/protocol.py` —
packed little-endian structs (mesh 23 B, USB sensor 28 B down, goal 17 B up).

---

## Hardware

| Role | Board | Job |
|---|---|---|
| Mother drone | Jetson Orin + ArduCam | runs the YOLO TensorRT model — the only heavy brain |
| Scouts | ESP32 ×5 (ESP-NOW mesh) | on-device auction, belief, RF localization |
| Data mule / cam scout | Raspberry Pi + camera | store-and-forward when the mesh severs |

---

## Status

Working today: the swarm engine, the live dashboard, the metrics harness, and
the Jetson detector all run. The 5-board mesh — auction, belief, and failure
detection — runs on the bench. Full end-to-end HIL integration (boards + Jetson
+ dashboard together) is in final assembly.

Built for **INNOHACK 2.0**.
