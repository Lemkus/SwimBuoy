#!/usr/bin/env python3
"""Compare haptic trend window sizes on real GPX."""
from __future__ import annotations

import statistics as stats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _analyze_haptic_trend import (  # noqa: E402
    analyze_haptic,
    ema_with_buoy_reset,
    parse_gpx,
    simulate_buoy_progress,
)


def progress_stats(rows: list, win: float) -> dict:
    ts = [r[0] for r in rows]
    raw = [r[2] for r in rows]
    bids = [r[1] for r in rows]
    in_radius = [r[3] for r in rows]
    smooth = ema_with_buoy_reset(raw, bids)

    progresses: list[float] = []
    for i in range(len(rows)):
        if in_radius[i]:
            continue
        j = i
        t_back = ts[i] - win
        while j > 0 and ts[j] > t_back:
            j -= 1
        if ts[i] - ts[j] < win * 0.8:
            continue
        progresses.append(smooth[i] - smooth[j])

    if not progresses:
        return {"n": 0, "med": 0.0, "le3_pct": 0.0, "le_scaled_pct": 0.0}

    scaled_thresh = -3.0 * win / 10.0
    return {
        "n": len(progresses),
        "med": stats.median(progresses),
        "le3_pct": 100 * sum(1 for p in progresses if p <= -3) / len(progresses),
        "le_scaled_pct": 100 * sum(1 for p in progresses if p <= scaled_thresh) / len(progresses),
    }


def main() -> None:
    files = [
        ("Kolya", Path(r"c:\Users\Смирнов Николай\Downloads\activity_23234924123.gpx")),
        ("Safar", Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614" / "Сафар.gpx"),
        ("Tyuki", Path(__file__).resolve().parents[1] / "routes" / "Щучье20260614" / "Тюки.gpx"),
    ]
    speed = 0.65  # m/s typical

    print("Window sweep (scaled threshold: -3m per 10s, OFF at +60% of ON)")
    print(f"At {speed} m/s: expected progress = speed * window")
    print()
    print(
        "win | exp_prog | ---- Kolya ---- | metrON% | tgl || "
        "Safar med | ON% | tgl || Tyuki ON%"
    )

    for win in [5, 6, 7, 8, 10, 12, 15]:
        on_th = -3.0 * win / 10.0
        off_th = -on_th * 0.6

        parts: list[str] = [f"{win:2d}s | {speed * win:5.1f}m  |"]
        on_pcts: list[str] = []

        for name, path in files:
            rows = simulate_buoy_progress(parse_gpx(path))
            ps = progress_stats(rows, win)
            r = analyze_haptic(
                rows,
                window_s=win,
                on_thresh=on_th,
                off_thresh=off_th,
                recheck_s=win,
            )
            if name == "Kolya":
                parts.append(f" med {ps['med']:+.2f}m scaled<={on_th:.1f}m:{ps['le_scaled_pct']:.0f}% |")
                parts.append(f" ON {r['on_pct']:4.0f}% tgl {r['toggles']:2d} |")
            elif name == "Safar":
                parts.append(f" med {ps['med']:+.2f}m | ON {r['on_pct']:4.0f}% tgl {r['toggles']:2d} |")
            else:
                on_pcts.append(f" ON {r['on_pct']:4.0f}%")

        parts.append(on_pcts[0] if on_pcts else "")
        print("".join(parts))


if __name__ == "__main__":
    main()
