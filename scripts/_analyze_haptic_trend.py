#!/usr/bin/env python3
"""Simulate distance-trend haptic logic on GPX swim tracks."""
from __future__ import annotations

import math
import statistics as stats
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

GPX_NS = "{http://www.topografix.com/GPX/1/1}"

BUOYS = {
    "P1": (60.211561, 29.787201),
    "P2": (60.215848, 29.77617),
    "P3": (60.213478, 29.777234),
    "P4": (60.214213, 29.787839),
    "P5": (60.21054, 29.782264),
}
ORDER = ["P1", "P2", "P3", "P4", "P5"]
RADIUS_M = 20
DWELL_SEC = 4


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_gpx(path: Path) -> list[tuple[datetime, float, float]]:
    root = ET.parse(path).getroot()
    pts: list[tuple[datetime, float, float]] = []
    for trkpt in root.iter(GPX_NS + "trkpt"):
        lat = float(trkpt.get("lat"))
        lon = float(trkpt.get("lon"))
        t_el = trkpt.find(GPX_NS + "time")
        if t_el is None or not t_el.text:
            continue
        t = datetime.fromisoformat(t_el.text.replace("Z", "+00:00"))
        pts.append((t, lat, lon))
    return pts


def ema_with_buoy_reset(
    raw_d: list[float],
    bids: list[str],
    alpha: float = 0.3,
) -> list[float]:
    """EMA that resets when active buoy changes (required in real app)."""
    out: list[float] = []
    s: float | None = None
    prev_bid: str | None = None
    for v, bid in zip(raw_d, bids):
        if bid != prev_bid:
            s = v
            prev_bid = bid
        else:
            s = v if s is None else (1 - alpha) * s + alpha * v
        out.append(s)
    return out


def simulate_buoy_progress(
    pts: list[tuple[datetime, float, float]],
) -> list[tuple[float, str, float, bool]]:
    """Return rows: (t_sec, active_buoy, dist_m, in_radius)."""
    if not pts:
        return []
    t0 = pts[0][0]
    active_i = 0
    dwell_start: datetime | None = None
    rows: list[tuple[float, str, float, bool]] = []

    for t, lat, lon in pts:
        t_sec = (t - t0).total_seconds()
        bid = ORDER[min(active_i, len(ORDER) - 1)]
        blat, blon = BUOYS[bid]
        dist = haversine(lat, lon, blat, blon)
        in_radius = dist <= RADIUS_M

        if active_i < len(ORDER):
            if in_radius:
                if dwell_start is None:
                    dwell_start = t
                elif (t - dwell_start).total_seconds() >= DWELL_SEC:
                    active_i += 1
                    dwell_start = None
            else:
                dwell_start = None

        rows.append((t_sec, bid, dist, in_radius))
    return rows


def analyze_haptic(
    rows: list[tuple[float, str, float, bool]],
    window_s: float = 10.0,
    on_thresh: float = -5.0,
    off_thresh: float = 3.0,
    ema_alpha: float = 0.3,
    recheck_s: float = 10.0,
) -> dict:
    if not rows:
        return {}

    ts = [r[0] for r in rows]
    raw_d = [r[2] for r in rows]
    bids = [r[1] for r in rows]
    in_radius = [r[3] for r in rows]
    smooth = ema_with_buoy_reset(raw_d, bids, ema_alpha)

    raw_deltas: list[float] = []
    for i in range(1, len(rows)):
        if in_radius[i] or in_radius[i - 1]:
            continue
        dt = ts[i] - ts[i - 1]
        if 0.5 <= dt <= 2.0:
            raw_deltas.append(raw_d[i] - raw_d[i - 1])

    state = False
    last_recheck = -recheck_s
    on_sec = 0
    swim_sec = 0
    toggles = 0
    t_end = int(ts[-1])
    prev_bid: str | None = None

    for t_cur in range(t_end + 1):
        idx = 0
        while idx + 1 < len(ts) and ts[idx + 1] <= t_cur:
            idx += 1

        if bids[idx] != prev_bid:
            state = False
            last_recheck = t_cur
            prev_bid = bids[idx]

        if in_radius[idx]:
            continue

        swim_sec += 1

        if t_cur - last_recheck >= recheck_s:
            last_recheck = t_cur
            t_back = t_cur - window_s
            j = idx
            while j > 0 and ts[j] > t_back:
                j -= 1
            progress = smooth[idx] - smooth[j]
            old = state
            if state:
                if progress >= off_thresh:
                    state = False
            elif progress <= on_thresh:
                state = True
            if old != state:
                toggles += 1

        if state:
            on_sec += 1

    naive_on = 0
    naive_swim = 0
    for i in range(1, len(rows)):
        if in_radius[i]:
            continue
        dt = ts[i] - ts[i - 1]
        if 0.5 <= dt <= 1.5:
            naive_swim += 1
            if raw_d[i] - raw_d[i - 1] < -0.3:
                naive_on += 1

    def pct(a: int, b: int) -> float:
        return 100.0 * a / b if b else 0.0

    abs_d = [abs(x) for x in raw_deltas]
    p90 = sorted(abs_d)[int(0.9 * len(abs_d))] if abs_d else 0.0

    return {
        "swim_sec": swim_sec,
        "on_pct": pct(on_sec, swim_sec),
        "toggles": toggles,
        "ticks": on_sec,
        "jitter_median": stats.median(abs_d) if abs_d else 0.0,
        "jitter_p90": p90,
        "naive_on_pct": pct(naive_on, naive_swim),
    }


def segment_examples(rows: list[tuple[float, str, float, bool]], window_s: float = 10.0) -> None:
    """Print a few concrete windows for Safar."""
    ts = [r[0] for r in rows]
    raw_d = [r[2] for r in rows]
    bids = [r[1] for r in rows]
    in_radius = [r[3] for r in rows]
    smooth = ema_with_buoy_reset(raw_d, bids, 0.3)

    print("  Concrete windows (smoothed dist to active buoy):")
    shown = 0
    for target_t in [300, 600, 900, 1200, 1800]:
        idx = min(range(len(ts)), key=lambda i: abs(ts[i] - target_t))
        if in_radius[idx]:
            continue
        j = idx
        t_back = ts[idx] - window_s
        while j > 0 and ts[j] > t_back:
            j -= 1
        progress = smooth[idx] - smooth[j]
        raw_prog = raw_d[idx] - raw_d[j]
        print(
            f"    t={ts[idx]:.0f}s buoy={bids[idx]} "
            f"raw {raw_d[j]:.0f}->{raw_d[idx]:.0f}m ({raw_prog:+.1f}m) "
            f"smooth {smooth[j]:.0f}->{smooth[idx]:.0f}m ({progress:+.1f}m)"
        )
        shown += 1
        if shown >= 5:
            break


def per_leg_analysis(rows: list[tuple[float, str, float, bool]]) -> None:
    """Per buoy leg: how often distance trend says approaching."""
    if not rows:
        return
    ts = [r[0] for r in rows]
    raw_d = [r[2] for r in rows]
    bids = [r[1] for r in rows]
    in_radius = [r[3] for r in rows]
    smooth = ema_with_buoy_reset(raw_d, bids, 0.3)

    print("  Per-leg (outside radius, 10s window progress):")
    for leg in ORDER:
        idxs = [i for i, b in enumerate(bids) if b == leg and not in_radius[i]]
        if len(idxs) < 20:
            continue
        progresses = []
        for i in idxs:
            t_back = ts[i] - 10
            j = i
            while j > 0 and ts[j] > t_back:
                j -= 1
            if ts[i] - ts[j] < 8:
                continue
            progresses.append(smooth[i] - smooth[j])
        if not progresses:
            continue
        approaching = sum(1 for p in progresses if p <= -5)
        drifting = sum(1 for p in progresses if p >= 3)
        flat = len(progresses) - approaching - drifting
        print(
            f"    {leg}: samples {len(progresses)}, "
            f"approaching {100*approaching/len(progresses):.0f}%, "
            f"flat {100*flat/len(progresses):.0f}%, "
            f"drifting {100*drifting/len(progresses):.0f}%"
        )


def main() -> None:
    base = Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614"
    files = ["Сафар.gpx", "Тюки.gpx", "Рома.gpx"]

    print("=== Haptic trend simulation ===")
    print(f"Buoys: Komarovo Shuchye P1..P5, radius={RADIUS_M}m, dwell={DWELL_SEC}s")
    print("Trend: EMA alpha=0.3, window=10s, recheck=10s, ON if progress<=-5m, OFF if>=+3m")
    print()

    for fname in files:
        path = base / fname
        pts = parse_gpx(path)
        if len(pts) < 10:
            print(f"{fname}: too few points")
            continue

        dist_total = sum(
            haversine(pts[i - 1][1], pts[i - 1][2], pts[i][1], pts[i][2])
            for i in range(1, len(pts))
        )
        dur = (pts[-1][0] - pts[0][0]).total_seconds()
        pace_100 = (100 / (dist_total / dur)) / 60 if dur else 0

        rows = simulate_buoy_progress(pts)
        r = analyze_haptic(rows)
        name = path.stem

        print(f"--- {name} ---")
        print(f"  {dur/60:.1f} min, {dist_total/1000:.2f} km track, ~{pace_100:.1f} min/100m")
        print(
            f"  1s GPS noise |delta dist|: median {r['jitter_median']:.2f}m, "
            f"p90 {r['jitter_p90']:.2f}m"
        )
        print(f"  Naive 1s (drop>0.3m): ON {r['naive_on_pct']:.1f}% of swim seconds")
        print(
            f"  Trend+hysteresis: ON {r['on_pct']:.1f}% swim, "
            f"{r['toggles']} toggles, {r['ticks']} metronome ticks"
        )
        if name == "Сафар":
            segment_examples(rows)
            per_leg_analysis(rows)
        print()

    print("=== Safar parameter sweep ===")
    pts = parse_gpx(base / "Сафар.gpx")
    rows = simulate_buoy_progress(pts)
    for win in [8, 10, 15]:
        for on_t in [-3, -5, -8]:
            r = analyze_haptic(rows, window_s=win, on_thresh=on_t)
            print(
                f"  win={win:2d}s ON<={on_t:3.0f}m -> "
                f"ON {r['on_pct']:5.1f}% toggles {r['toggles']:3d}"
            )


if __name__ == "__main__":
    main()
