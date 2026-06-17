#!/usr/bin/env python3
"""GPS noise budget for minimal corridor (not swimmer path envelope)."""
from __future__ import annotations

import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _analyze_haptic_trend import parse_gpx  # noqa: E402
from analyze_corridor_shuchye import (  # noqa: E402
    ENDPOINT_BUFFER_M,
    build_legs,
    buoy_visit_indices,
    cross_track_and_along,
    percentile,
)

PATHS = [
    ("Коля", Path(r"c:\Users\Смирнов Николай\Downloads\activity_23234924123.gpx")),
    ("Рома", Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614" / "Рома.gpx"),
]


def xte_series(pts, i0: int, i1: int, leg) -> list[float]:
    xs: list[float] = []
    lo, hi = min(i0, i1), max(i0, i1)
    for i in range(lo, hi + 1):
        _, lat, lon = pts[i]
        xte, along, ln = cross_track_and_along(lat, lon, leg.lat1, leg.lon1, leg.lat2, leg.lon2)
        if ENDPOINT_BUFFER_M <= along <= ln - ENDPOINT_BUFFER_M:
            xs.append(xte)
    return xs


def main() -> None:
    legs = build_legs(False)
    leg_p1p2, leg_p2p3 = legs[1], legs[2]
    pool_d: list[float] = []

    print("=== |dXTE| per GPS step (mid-leg) — proxy for GPS jitter ===\n")
    for name, path in PATHS:
        pts = parse_gpx(path)
        for label, leg, visit in [
            ("P2->P3", leg_p2p3, ["P2", "P3"]),
            ("P1->P2", leg_p1p2, ["P1", "P2"]),
        ]:
            i0, i1 = buoy_visit_indices(pts, visit)
            xs = xte_series(pts, i0, i1, leg)
            deltas = [abs(xs[i] - xs[i - 1]) for i in range(1, len(xs))]
            abs_x = [abs(x) for x in xs]
            if label == "P2->P3":
                pool_d.extend(deltas)
            print(
                f"{name} {label}: n={len(xs)} "
                f"|XTE| med={st.median(abs_x):.1f} p95={percentile(abs_x, 95):.1f} | "
                f"|dXTE| med={st.median(deltas):.2f} p90={percentile(deltas, 90):.2f} "
                f"p99={percentile(deltas, 99):.2f} max={max(deltas):.1f}"
            )

    print("\n=== Pooled P2->P3 (best chord leg) ===")
    print(
        f"|dXTE|/step: med={st.median(pool_d):.2f} p90={percentile(pool_d, 90):.2f} "
        f"p99={percentile(pool_d, 99):.2f} max={max(pool_d):.1f}"
    )

    # Step jitter from _gps_noise_table: ~0.7-1.0m p90 between GPS points
    p99 = percentile(pool_d, 99)
    print("\n=== Minimal half-width candidates (anti-false-alarm, not path fit) ===")
    print(f"  A) static ±15m + 3s sustain outside (no wide path envelope)")
    print(f"  B) static ±20m + hysteresis 5m")
    print(f"  C) static ±{round(p99 + 12)}m (= p99|dXTE| + ~12m absolute GPS bias)")
    print(f"  D) static ±{round(p99 * 2 + 10)}m (= 2× p99 step jitter + bias)")


if __name__ == "__main__":
    main()
