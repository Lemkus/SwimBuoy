#!/usr/bin/env python3
"""Analyze Kolya GPX vs Shuchye buoys."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _analyze_haptic_trend import (  # noqa: E402
    BUOYS,
    DWELL_SEC,
    ORDER,
    RADIUS_M,
    analyze_haptic,
    ema_with_buoy_reset,
    haversine,
    parse_gpx,
    per_leg_analysis,
    simulate_buoy_progress,
)


def simulate_custom_order(
    pts: list[tuple[datetime, float, float]],
    sequence: list[str],
) -> list[tuple[float, str, float, bool]]:
    t0 = pts[0][0]
    active_i = 0
    dwell_start: datetime | None = None
    rows: list[tuple[float, str, float, bool]] = []

    for t, lat, lon in pts:
        bid = sequence[min(active_i, len(sequence) - 1)]
        blat, blon = BUOYS[bid]
        dist = haversine(lat, lon, blat, blon)
        in_radius = dist <= RADIUS_M

        if active_i < len(sequence):
            if in_radius:
                if dwell_start is None:
                    dwell_start = t
                elif (t - dwell_start).total_seconds() >= DWELL_SEC:
                    active_i += 1
                    dwell_start = None
            else:
                dwell_start = None

        rows.append(((t - t0).total_seconds(), bid, dist, in_radius))
    return rows


def p2_bands(rows: list[tuple[float, str, float, bool]]) -> None:
    ts = [r[0] for r in rows]
    raw = [r[2] for r in rows]
    bids = [r[1] for r in rows]
    in_radius = [r[3] for r in rows]
    smooth = ema_with_buoy_reset(raw, bids)

    print("  P2 progress by distance band:")
    for lo, hi in [(0, 100), (100, 300), (300, 600), (600, 9999)]:
        progresses: list[float] = []
        for i in range(len(rows)):
            if bids[i] != "P2" or in_radius[i] or not (lo <= smooth[i] < hi):
                continue
            j = i
            t_back = ts[i] - 10
            while j > 0 and ts[j] > t_back:
                j -= 1
            if ts[i] - ts[j] < 8:
                continue
            progresses.append(smooth[i] - smooth[j])
        if not progresses:
            continue
        approaching = sum(1 for p in progresses if p <= -5)
        med = sorted(progresses)[len(progresses) // 2]
        print(
            f"    {lo}-{hi}m: n={len(progresses)}, "
            f"approaching {100 * approaching / len(progresses):.0f}%, median {med:+.1f}m"
        )


def main() -> None:
    path = Path(r"c:\Users\Смирнов Николай\Downloads\activity_23234924123.gpx")
    pts = parse_gpx(path)
    if not pts:
        print("No track points")
        return

    dist_total = sum(
        haversine(pts[i - 1][1], pts[i - 1][2], pts[i][1], pts[i][2])
        for i in range(1, len(pts))
    )
    dur = (pts[-1][0] - pts[0][0]).total_seconds()
    pace_100 = (100 / (dist_total / dur)) / 60 if dur else 0.0

    print("=== Kolya (Garmin FR955, Open Water Swim) ===")
    print(f"Points: {len(pts)}")
    print(f"Duration {dur / 60:.1f} min, track {dist_total / 1000:.2f} km, pace ~{pace_100:.1f} min/100m")
    print(f"Buoy sim: radius={RADIUS_M}m dwell={DWELL_SEC}s")
    print()
    print("Min distance to each buoy over whole swim:")
    for pid in ORDER:
        blat, blon = BUOYS[pid]
        md = min(haversine(lat, lon, blat, blon) for _, lat, lon in pts)
        print(f"  {pid}: {md:.0f} m")

    print()
    print("--- App order P1 -> P2 -> P3 -> P4 -> P5 ---")
    rows = simulate_buoy_progress(pts)
    r = analyze_haptic(rows)
    visited = sorted(set(b for b, _, _, _ in rows))
    print(f"Final active buoy: {rows[-1][1]}, visited: {visited}")
    print(
        f"GPS 1s jitter: median {r['jitter_median']:.2f}m, p90 {r['jitter_p90']:.2f}m"
    )
    print(f"Naive 1s metronome: ON {r['naive_on_pct']:.1f}%")
    print(
        f"Trend+hysteresis (-5m/10s): ON {r['on_pct']:.1f}%, "
        f"{r['toggles']} toggles, {r['ticks']} ticks"
    )
    per_leg_analysis(rows)
    p2_bands(rows)

    print()
    print("--- If skipped P2 like others: P1 -> P3 -> P4 -> P5 ---")
    rows_skip = simulate_custom_order(pts, ["P3", "P4", "P5"])
    r3 = analyze_haptic(rows_skip)
    print(f"Final buoy: {rows_skip[-1][1]}")
    print(f"Trend ON {r3['on_pct']:.1f}%, toggles {r3['toggles']}")
    per_leg_analysis(rows_skip)

    print()
    print("--- Compare swimmers (app order, trend ON %) ---")
    base = Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614"
    for fname in ["Сафар.gpx", "Тюки.gpx", "Рома.gpx"]:
        p = base / fname
        if not p.exists():
            continue
        rr = analyze_haptic(simulate_buoy_progress(parse_gpx(p)))
        print(f"  {p.stem}: jitter {rr['jitter_median']:.2f}m, trend ON {rr['on_pct']:.1f}%")
    print(f"  Kolya: jitter {r['jitter_median']:.2f}m, trend ON {r['on_pct']:.1f}%")


if __name__ == "__main__":
    main()
