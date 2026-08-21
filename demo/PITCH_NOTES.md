# KHOJ — Pitch Notes

Autonomous drone **swarm** for search & rescue. Leaderless, resilient, and it
never confirms a survivor on one sensor.

---

## The one-liner
> KHOJ finds and confirms survivors **faster than naive search — with no pilots
> and no single point of failure.** A market-style auction spreads the swarm out,
> and a second drone confirms every sighting before we ever raise an alert.

## The problem (open with this)
- Disasters scatter people across vast, hazardous, GPS-degraded terrain. The
  **first 72 hours** decide who survives.
- Today's tools don't scale: ground search is slow and dangerous; tele-operated
  drones need **one pilot per drone**; and a centrally-controlled fleet goes
  blind the moment comms or the leader drops — a single point of failure.

## The solution (our novelty)
1. **Leaderless auction** — every drone bids `expected-survivors/sec`; highest
   wins, ties to lowest ID. No leader, no referee, no single point of failure.
2. **Cooperative re-observation** — one sensor is never enough. A second drone
   from a *different bearing* confirms or rejects every sighting (Bayesian
   log-odds fusion).
3. **Trust & quarantine** — a faulty or spoofed sensor loses trust and is benched
   automatically; the swarm keeps working.
4. **Cheap, scalable hardware** — runs on an ESP32 mesh; scale by adding nodes,
   not re-architecting.

---

## The numbers (the proof — memorize these)

| Metric | Value | Why it matters |
|---|---|---|
| Survivors confirmed (equal time budget) | **4.23** vs ≤2.6 for baselines | ~2–3× more than greedy / lawnmower / random |
| False alarms | **0 across 600 Monte-Carlo runs** | the swarm never cries wolf |
| Coverage vs rescue | lawnmower covers 100% but confirms **1.4** | *coverage ≠ rescue* — you need the second look |
| Detector accuracy | **mAP50 0.934**, recall 0.875 | trained on real aerial SAR imagery |
| On-device speed | **~N ms/frame** on the Jetson (fill in from the live run) | runs on the drone's own compute |
| ESP-NOW mesh | **0.0% packet loss** @ 5 Hz, 5 boards | measured on the bench, not estimated |
| Failure detection | peer dead in **< 2 s**, no election | pull a board's power live |
| RF localization | converges to **0.3 grid cells** | finds a transmitter no drone can see |

> Ablations prove each piece earns its place: remove re-observation → confirmations
> collapse (~4 → ~1). Turn off trust against a faulty sensor → wasted work triples.

---

## Demo runbook (three live demos)

**1. The swarm, thinking (laptop dashboard)**
```
uvicorn backend.main:app --host 127.0.0.1 --port 8000
python -m http.server 3000 --bind 127.0.0.1 --directory frontend
```
Open `http://127.0.0.1:3000/`. Point at: coverage sweeping the map, a sighting
going **candidate → confirmed** when a 2nd drone agrees, a drone turning
**QUARANTINED** when its sensor misbehaves. *Say: "no drone here is being told
what to do — they're bidding against each other in real time."*

**2. The drone's eye (Jetson + camera)**
On the Jetson: `python3 ~/jetson_stream.py --engine ~/best.engine --source 0`
On the laptop browser: `http://192.168.55.1:8090`. Hover the camera over a phone
showing `demo/images/sample_01.jpg` (two people, 0.95/0.94). *Say: "this is the
real trained detector running on the drone's own compute — N ms per frame."*

**3. The real mesh (5 ESP32 boards)**
Show the boards reaching the **same auction winner with no referee**, and pull
one board's power → the others re-auction its task in under 2 seconds.

> **Fallback if any hardware misbehaves:** the laptop dashboard + Jetson camera
> demo are fully self-contained. Lead with those; the mesh is the encore.

---

## Q&A prep (likely judge questions)

- **"Isn't this just multiple drones?"** No — it's *leaderless coordination*. Kill
  any drone or the comms and the rest reallocate automatically. There's no
  controller to take out.
- **"How do you avoid false rescues?"** Confirmation is *structural* — a single
  sensor can never confirm, by construction. Two independent agents from
  different angles must agree. 0 false alarms in 600 runs.
- **"Does it scale?"** The auction is decentralized, so adding drones needs no
  re-architecting and no extra pilots. It runs on \$5 ESP32s.
- **"Real or simulated?"** Both. Detector is trained on real aerial imagery and
  runs on a real Jetson; the mesh + auction run on 5 real ESP32 boards; the sim
  is how we stress-test failures we can't safely stage.
- **"What's not done yet?"** On-device belief/frontier search — routine coverage
  is still laptop-assisted. Honest, and on the roadmap.

---

## Asset index (`demo/`)
- `images/sample_0N.jpg` — 6 high-confidence aerial images to show on a phone
  (share these to your phone). `images/annotated/` shows what the model detects.
- `screenshots/dashboard_live.png` — the live mission console.
- `screenshots/engine_run_complete.png` — a completed mission (4/5 confirmed).
- `diagrams/architecture.png` · `mission_loop.png` · `benchmark_results.png`.
- **Deck:** `khoj/docs/ppt/KHOJ_INNOHACK.pptx` (Rishit's, with SVG diagrams).
  *Note: there is a second draft deck in the scratchpad — reconcile to one before
  the pitch.*
