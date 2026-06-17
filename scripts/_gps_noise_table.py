#!/usr/bin/env python3
"""GPS noise comparison table for Shuchye swim participants."""
from __future__ import annotations

import statistics as stats
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _analyze_haptic_trend import BUOYS, haversine, parse_gpx, simulate_buoy_progress  # noqa: E402


def detect_device(path: Path) -> str:
    head = path.read_text(encoding="utf-8", errors="ignore")[:800]
    if "Garmin" in head:
        return "Garmin FR955"
    if "COROS" in head:
        return "COROS"
    return "?"


def track_step_stats(pts: list) -> dict:
    deltas: list[float] = []
    speeds: list[float] = []
    intervals: list[float] = []
    for i in range(1, len(pts)):
        dt = (pts[i][0] - pts[i - 1][0]).total_seconds()
        if dt <= 0:
            continue
        seg = haversine(pts[i - 1][1], pts[i - 1][2], pts[i][1], pts[i][2])
        deltas.append(seg)
        intervals.append(dt)
        if 0.5 <= dt <= 5.0:
            speeds.append(seg / dt)
    abs_d = sorted(deltas)
    abs_i = sorted(intervals)
    return {
        "step_median": stats.median(deltas) if deltas else 0.0,
        "step_p90": abs_d[int(0.9 * len(abs_d))] if abs_d else 0.0,
        "step_p99": abs_d[int(0.99 * len(abs_d))] if abs_d else 0.0,
        "interval_median": stats.median(intervals) if intervals else 0.0,
        "interval_p90": abs_i[int(0.9 * len(abs_i))] if abs_i else 0.0,
        "speed_median": stats.median(speeds) if speeds else 0.0,
    }


def dist_to_buoy_jitter(rows: list[tuple[float, str, float, bool]]) -> dict:
    """1s-like |delta distance to active buoy| while swimming."""
    ts = [r[0] for r in rows]
    dist = [r[2] for r in rows]
    in_r = [r[3] for r in rows]
    deltas: list[float] = []
    for i in range(1, len(rows)):
        if in_r[i] or in_r[i - 1]:
            continue
        dt = ts[i] - ts[i - 1]
        if 0.5 <= dt <= 2.0:
            deltas.append(abs(dist[i] - dist[i - 1]))
    abs_d = sorted(deltas)
    return {
        "buoy_delta_median": stats.median(deltas) if deltas else 0.0,
        "buoy_delta_p90": abs_d[int(0.9 * len(abs_d))] if abs_d else 0.0,
    }


def p2_credit_analysis(pts: list) -> dict:
    p2 = BUOYS["P2"]
    t0 = pts[0][0]
    dists = [haversine(lat, lon, p2[0], p2[1]) for _, lat, lon in pts]
    times = [(t - t0).total_seconds() for t, _, _ in pts]

    best_i = min(range(len(dists)), key=lambda i: dists[i])
    # longest run inside radius
    best_run = 0
    cur = 0
    for d, t_prev, t_cur in zip(dists, [times[0]] + times[:-1], times):
        _ = t_prev
        if d <= 20:
            cur += 1
            best_run = max(best_run, cur)
        else:
            cur = 0

    # dwell-capable: 4+ consecutive points with <=20m and span >=4s
    dwell_ok = False
    i = 0
    while i < len(pts):
        if dists[i] > 20:
            i += 1
            continue
        j = i
        while j < len(pts) and dists[j] <= 20:
            j += 1
        span = pts[j - 1][0] - pts[i][0] if j > i else pts[0][0] - pts[0][0]
        if (j - i) >= 2 and span.total_seconds() >= 4:
            dwell_ok = True
            break
        i = j if j > i else i + 1

    return {
        "min_p2_m": dists[best_i],
        "min_p2_min": times[best_i] / 60,
        "sec_inside_20m": sum(1 for d in dists if d <= 20),
        "sec_inside_25m": sum(1 for d in dists if d <= 25),
        "gpx_would_credit_p2": dwell_ok,
        "gp_interval_at_closest": (
            (pts[best_i][0] - pts[best_i - 1][0]).total_seconds()
            if best_i > 0
            else 0
        ),
    }


def main() -> None:
    files = [
        ("Коля", Path(r"c:\Users\Смирнов Николай\Downloads\activity_23234924123.gpx")),
        ("Сафар", Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614" / "Сафар.gpx"),
        ("Тюки", Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614" / "Тюки.gpx"),
        ("Рома", Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614" / "Рома.gpx"),
    ]

    print("GPS noise & track stats — Shuchye 2026-06-12/14")
    print()

    rows_out: list[dict] = []
    for name, path in files:
        if not path.exists():
            continue
        pts = parse_gpx(path)
        dur = (pts[-1][0] - pts[0][0]).total_seconds()
        track_m = sum(
            haversine(pts[i - 1][1], pts[i - 1][2], pts[i][1], pts[i][2])
            for i in range(1, len(pts))
        )
        step = track_step_stats(pts)
        sim = simulate_buoy_progress(pts)
        buoy_j = dist_to_buoy_jitter(sim)
        p2 = p2_credit_analysis(pts)
        buoy_min = {
            pid: min(haversine(lat, lon, BUOYS[pid][0], BUOYS[pid][1]) for _, lat, lon in pts)
            for pid in BUOYS
        }

        rows_out.append({
            "name": name,
            "device": detect_device(path),
            "points": len(pts),
            "dur_min": dur / 60,
            "track_km": track_m / 1000,
            "pace_100": (100 / (track_m / dur)) / 60 if dur else 0,
            **step,
            **buoy_j,
            **p2,
            **{f"min_{k}": v for k, v in buoy_min.items()},
        })

    # Table 1: GPS noise
    hdr = (
        "Участник | Часы | Точек | Интервал мед. | "
        "Шаг GPS мед. | шаг p90 | шаг p99 | "
        "ddist k buyu med. | ddist p90 | Skorost med."
    )
    print(hdr)
    print("-" * len(hdr))
    for r in rows_out:
        print(
            f"{r['name']} | {r['device']} | {r['points']} | {r['interval_median']:.1f}s | "
            f"{r['step_median']:.2f}m | {r['step_p90']:.2f}m | {r['step_p99']:.2f}m | "
            f"{r['buoy_delta_median']:.2f}m | {r['buoy_delta_p90']:.2f}m | {r['speed_median']:.2f}m/s"
        )

    print()
    print("P2: GPX vs засчитывание (радиус 20m, dwell 4s)")
    print("Участник | мин до P2 | внутри 20m (точек) | GPX засчитал бы P2? | sim финальный буй")
    for r in rows_out:
        fin = simulate_buoy_progress(parse_gpx(files[[x[0] for x in files].index(r['name'])][1]))[-1][1]
        print(
            f"{r['name']} | {r['min_p2_m']:.0f}m @ {r['min_p2_min']:.0f}мин | "
            f"{r['sec_inside_20m']} | {r['gpx_would_credit_p2']} | {fin}"
        )

    k = rows_out[0]
    print()
    print(f"Коля у ближайшего к P2: интервал между точками GPX = {k['gp_interval_at_closest']:.0f}s")


if __name__ == "__main__":
    main()
