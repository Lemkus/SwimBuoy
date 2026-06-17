#!/usr/bin/env python3
"""Cross-track corridor analysis for Shchuchye swims + GPX export for maps."""
from __future__ import annotations

import math
import statistics as stats
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _analyze_haptic_trend import (  # noqa: E402
    BUOYS,
    ORDER,
    haversine,
    parse_gpx,
)

ROOT = Path(__file__).resolve().parents[1]
SHUCHYE_DIR = ROOT / "routes" / "Щучье20260614"
KOLYA_GPX = Path(r"c:\Users\Смирнов Николай\Downloads\activity_23234924123.gpx")
START = (60.209446, 29.789698)  # from ЩучьеОзеро.gpx / spec

# Skip P2 — known field behaviour (GPX sim confirms no P2 credit).
SKIP_P2 = {"Сафар", "Тюки"}

SWIMMERS: list[tuple[str, Path, bool]] = [
    ("Коля", KOLYA_GPX, False),
    ("Рома", SHUCHYE_DIR / "Рома.gpx", False),
    ("Сафар", SHUCHYE_DIR / "Сафар.gpx", True),
    ("Тюки", SHUCHYE_DIR / "Тюки.gpx", True),
]

ENDPOINT_BUFFER_M = 50.0  # ignore XTE near leg ends (GPS cone)
SAFETY_MARGIN_M = 5.0
# GPS bias budget for map GPX / haptic (not swimmer path envelope). See docs discussion.
GPS_CORRIDOR_HALF_WIDTH_M = 20.0


@dataclass(frozen=True)
class Leg:
    leg_id: str
    from_id: str
    to_id: str
    lat1: float
    lon1: float
    lat2: float
    lon2: float

    @property
    def length_m(self) -> float:
        return haversine(self.lat1, self.lon1, self.lat2, self.lon2)


def build_legs(skip_p2: bool) -> list[Leg]:
    sequence = ["start", *ORDER]
    if skip_p2:
        sequence = ["start", "P1", "P3", "P4", "P5"]
    coords = {"start": START, **BUOYS}
    legs: list[Leg] = []
    for i in range(len(sequence) - 1):
        a, b = sequence[i], sequence[i + 1]
        lat1, lon1 = coords[a]
        lat2, lon2 = coords[b]
        legs.append(Leg(f"{a}->{b}", a, b, lat1, lon1, lat2, lon2))
    return legs


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def destination(lat: float, lon: float, brg_deg: float, dist_m: float) -> tuple[float, float]:
    r = 6371000.0
    p1 = math.radians(lat)
    l1 = math.radians(lon)
    brg = math.radians(brg_deg)
    p2 = math.asin(
        math.sin(p1) * math.cos(dist_m / r)
        + math.cos(p1) * math.sin(dist_m / r) * math.cos(brg)
    )
    l2 = l1 + math.atan2(
        math.sin(brg) * math.sin(dist_m / r) * math.cos(p1),
        math.cos(dist_m / r) - math.sin(p1) * math.sin(p2),
    )
    return math.degrees(p2), math.degrees(l2)


def cross_track_and_along(
    lat: float,
    lon: float,
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> tuple[float, float, float]:
    """Return (cross_track_m signed, along_m, leg_length_m). +XTE = right of leg direction."""
    leg_len = haversine(lat1, lon1, lat2, lon2)
    if leg_len < 1.0:
        return 0.0, 0.0, leg_len

    brg_12 = bearing_deg(lat1, lon1, lat2, lon2)
    brg_1p = bearing_deg(lat1, lon1, lat, lon)
    dist_1p = haversine(lat1, lon1, lat, lon)
    rel = math.radians(brg_1p - brg_12)
    along = dist_1p * math.cos(rel)
    xte = dist_1p * math.sin(rel)
    return xte, along, leg_len


def assign_leg(
    lat: float,
    lon: float,
    legs: list[Leg],
) -> tuple[Leg | None, float, float]:
    best: Leg | None = None
    best_xte = 0.0
    best_along = 0.0
    best_score = float("inf")
    for leg in legs:
        xte, along, leg_len = cross_track_and_along(lat, lon, leg.lat1, leg.lon1, leg.lat2, leg.lon2)
        if along < -ENDPOINT_BUFFER_M or along > leg_len + ENDPOINT_BUFFER_M:
            continue
        score = abs(xte)
        if score < best_score:
            best_score = score
            best = leg
            best_xte = xte
            best_along = along
    return best, best_xte, best_along


def buoy_visit_indices(
    pts: list[tuple[datetime, float, float]],
    visit_order: list[str],
) -> list[int]:
    """Index of closest approach to each buoy, in swim order."""
    indices: list[int] = []
    start = 0
    for bid in visit_order:
        blat, blon = BUOYS[bid]
        best_i = start
        best_d = float("inf")
        for i in range(start, len(pts)):
            d = haversine(pts[i][1], pts[i][2], blat, blon)
            if d < best_d:
                best_d = d
                best_i = i
        indices.append(best_i)
        start = min(best_i + 1, len(pts) - 1)
    return indices


def collect_xte_on_leg(
    pts: list[tuple[datetime, float, float]],
    i0: int,
    i1: int,
    leg: Leg,
) -> list[float]:
    samples: list[float] = []
    lo = min(i0, i1)
    hi = max(i0, i1)
    for i in range(lo, hi + 1):
        _, lat, lon = pts[i]
        xte, along, leg_len = cross_track_and_along(lat, lon, leg.lat1, leg.lon1, leg.lat2, leg.lon2)
        if along < ENDPOINT_BUFFER_M or along > leg_len - ENDPOINT_BUFFER_M:
            continue
        samples.append(abs(xte))
    return samples


def collect_xte_samples(
    pts: list[tuple[datetime, float, float]],
    skip_p2: bool,
) -> tuple[list[float], dict[str, list[float]]]:
    visit_order = ["P1", "P3", "P4", "P5"] if skip_p2 else ORDER
    legs = build_legs(skip_p2)
    per_leg: dict[str, list[float]] = {leg.leg_id: [] for leg in legs}

    visit_idx = buoy_visit_indices(pts, visit_order)

    # start -> P1
    p1_i = visit_idx[0]
    leg0 = legs[0]
    per_leg[leg0.leg_id] = collect_xte_on_leg(pts, 0, p1_i, leg0)

    # between buoys
    for j in range(len(visit_order) - 1):
        leg = legs[j + 1]
        seg = collect_xte_on_leg(pts, visit_idx[j], visit_idx[j + 1], leg)
        per_leg[leg.leg_id] = seg

    all_xte = [x for vals in per_leg.values() for x in vals]
    return all_xte, per_leg


def pct_outside(samples: list[float], half_width: float) -> float:
    if not samples:
        return 0.0
    return 100.0 * sum(1 for x in samples if x > half_width) / len(samples)


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    idx = int(round((p / 100.0) * (len(s) - 1)))
    return s[idx]


def interpolate_leg(leg: Leg, step_m: float = 25.0) -> list[tuple[float, float]]:
    n = max(2, int(leg.length_m / step_m) + 1)
    pts: list[tuple[float, float]] = []
    for i in range(n):
        t = i / (n - 1)
        lat = leg.lat1 + t * (leg.lat2 - leg.lat1)
        lon = leg.lon1 + t * (leg.lon2 - leg.lon1)
        pts.append((lat, lon))
    return pts


def offset_polyline(
    center: list[tuple[float, float]],
    half_width_m: float,
    side: int,
) -> list[tuple[float, float]]:
    if len(center) < 2:
        return center
    out: list[tuple[float, float]] = []
    sign = 1.0 if side > 0 else -1.0
    for i, (lat, lon) in enumerate(center):
        if i < len(center) - 1:
            nlat, nlon = center[i + 1]
        else:
            nlat, nlon = center[i - 1]
            lat, lon = center[i]
        brg = bearing_deg(lat, lon, nlat, nlon)
        off_brg = (brg + sign * 90.0) % 360.0
        out.append(destination(lat, lon, off_brg, half_width_m))
    return out


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def leg_half_width_from_length(leg_len_m: float) -> int:
    """Empirical from Kolya+Roma p95 on Щучье: ~11% of leg length + 5 m."""
    return int(round(max(20.0, min(95.0, leg_len_m * 0.11 + SAFETY_MARGIN_M))))


def recommend_per_leg_widths(good_per_leg: dict[str, list[float]], legs: list[Leg]) -> dict[str, int]:
    widths: dict[str, int] = {}
    for leg in legs:
        vals = good_per_leg.get(leg.leg_id, [])
        if vals:
            widths[leg.leg_id] = int(round(percentile(vals, 95) + SAFETY_MARGIN_M))
        else:
            widths[leg.leg_id] = leg_half_width_from_length(leg.length_m)
    return widths


def write_gpx(
    path: Path,
    leg_widths: dict[str, float],
    swimmer_tracks: dict[str, list[tuple[datetime, float, float]]],
    title: str,
) -> None:
    gpx = ET.Element(
        "gpx",
        {
            "xmlns": "http://www.topografix.com/GPX/1/1",
            "version": "1.1",
            "creator": "SwimBuoy analyze_corridor_shuchye.py",
        },
    )
    meta = ET.SubElement(gpx, "metadata")
    ET.SubElement(meta, "name").text = title
    ET.SubElement(meta, "time").text = iso_now()
    ET.SubElement(meta, "desc").text = (
        f"Коридор ±{min(leg_widths.values()) if leg_widths else GPS_CORRIDOR_HALF_WIDTH_M:.0f}–"
        f"{max(leg_widths.values()) if leg_widths else GPS_CORRIDOR_HALF_WIDTH_M:.0f} m "
        "вокруг хорды плеча — бюджет GPS, не «допустимая дуга». "
        "center = ось; L/R = границы. gpx.studio / MapMagic."
    )

    for pid, (lat, lon) in [("Старт", START), *[(k, BUOYS[k]) for k in ORDER]]:
        wpt = ET.SubElement(gpx, "wpt", {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})
        ET.SubElement(wpt, "name").text = pid
        ET.SubElement(wpt, "type").text = "Buoy" if pid != "Старт" else "Start"

    full_legs = build_legs(skip_p2=False)
    for leg in full_legs:
        half_width_m = leg_widths.get(leg.leg_id, 25.0)
        center = interpolate_leg(leg, step_m=20.0)
        left = offset_polyline(center, half_width_m, side=-1)
        right = offset_polyline(center, half_width_m, side=+1)

        for name, line, color_hint in [
            (f"{leg.leg_id} center", center, "center"),
            (f"{leg.leg_id} L -{half_width_m:.0f}m", left, "left"),
            (f"{leg.leg_id} R +{half_width_m:.0f}m", right, "right"),
        ]:
            trk = ET.SubElement(gpx, "trk")
            ET.SubElement(trk, "name").text = name
            ET.SubElement(trk, "type").text = color_hint
            seg = ET.SubElement(trk, "trkseg")
            for lat, lon in line:
                ET.SubElement(seg, "trkpt", {"lat": f"{lat:.7f}", "lon": f"{lon:.7f}"})

    for name, pts in swimmer_tracks.items():
        if not pts:
            continue
        trk = ET.SubElement(gpx, "trk")
        ET.SubElement(trk, "name").text = f"swim {name}"
        ET.SubElement(trk, "type").text = "swim"
        seg = ET.SubElement(trk, "trkseg")
        for t, lat, lon in pts:
            tp = ET.SubElement(seg, "trkpt", {"lat": f"{lat:.7f}", "lon": f"{lon:.7f}"})
            ET.SubElement(tp, "time").text = t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    tree = ET.ElementTree(gpx)
    ET.indent(tree, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def main() -> None:
    good_xte: list[float] = []
    good_per_leg: dict[str, list[float]] = {}
    skip_xte_on_p2_leg: list[float] = []
    swimmer_tracks: dict[str, list[tuple[datetime, float, float]]] = {}
    report_lines: list[str] = []
    full_legs = build_legs(skip_p2=False)

    report_lines.append("=== Анализ коридора, Щучье 2026-06-14 ===")
    report_lines.append("Треки: Коля, Рома (полный маршрут); Сафар, Тюки (skip P2).")
    report_lines.append("5-й пловец: GPX в репозитории не найден — добавьте в routes/Щучье20260614/.\n")

    for name, path, known_skip in SWIMMERS:
        if not path.exists():
            report_lines.append(f"MISSING: {name} -> {path}")
            continue
        pts = parse_gpx(path)
        swimmer_tracks[name] = pts
        skip = known_skip
        samples, per_leg = collect_xte_samples(pts, skip)

        report_lines.append(f"--- {name} ({path.name}) ---")
        report_lines.append(f"  route: {'P1->P3 skip P2' if skip else 'full P1..P5'}")
        if samples:
            report_lines.append(
                f"  |XTE| all legs: n={len(samples)}, "
                f"med={stats.median(samples):.1f}m, p90={percentile(samples, 90):.1f}m, "
                f"p95={percentile(samples, 95):.1f}m, p99={percentile(samples, 99):.1f}m, "
                f"max={max(samples):.1f}m"
            )
        for leg_id, vals in per_leg.items():
            if not vals:
                continue
            report_lines.append(
                f"    {leg_id}: n={len(vals)}, med={stats.median(vals):.1f}m, "
                f"p95={percentile(vals, 95):.1f}m"
            )

        if not skip:
            good_xte.extend(samples)
            for leg_id, vals in per_leg.items():
                good_per_leg.setdefault(leg_id, []).extend(vals)
        else:
            # Points on P1->P2 leg while swimmer actually goes P1->P3.
            p1_i, p3_i = buoy_visit_indices(pts, ["P1", "P3"])
            p2_leg = build_legs(skip_p2=False)[1]  # P1->P2
            wrong = collect_xte_on_leg(pts, p1_i, p3_i, p2_leg)
            if wrong:
                skip_xte_on_p2_leg.extend(wrong)

    if not good_xte:
        report_lines.append("\nНет данных on-route!")
        print("\n".join(report_lines))
        return

    report_lines.append("\n=== Рекомендация по плечам (Коля+Рома, p95 + 5 м) ===")
    per_leg_widths = recommend_per_leg_widths(good_per_leg, full_legs)
    for leg in full_legs:
        vals = good_per_leg.get(leg.leg_id, [])
        w = per_leg_widths[leg.leg_id]
        scaled = leg_half_width_from_length(leg.length_m)
        if vals:
            report_lines.append(
                f"  {leg.leg_id} ({leg.length_m:.0f} m): "
                f"p50={stats.median(vals):.0f}m p95={percentile(vals, 95):.0f}m -> "
                f"коридор ±{w}m (формула 11% длины: ±{scaled}m)"
            )
        else:
            report_lines.append(f"  {leg.leg_id}: нет данных")

    p95_all = percentile(good_xte, 95)
    global_wide = int(round(p95_all + SAFETY_MARGIN_M))
    report_lines.append(
        f"\nГлобальный «один коридор на всё» (p95 всех плеч): ±{global_wide} m — "
        f"слишком широко для коротких плеч, см. per-leg выше."
    )

    tight_legs = ["P2->P3", "P4->P5"]
    tight_pool = [x for lid in tight_legs for x in good_per_leg.get(lid, [])]
    tight_p95 = percentile(tight_pool, 95) if tight_pool else 25.0
    mvp_default = int(round(tight_p95 + SAFETY_MARGIN_M))
    report_lines.append(
        f"\nMVP default для «хороших» плеч (P2-P3, P4-P5): ±{mvp_default} m "
        f"(на P2-P3 пловцы почти на хорде, med~10 m)."
    )

    report_lines.append("\n=== Компромисс: один порог vs ложные срабатывания ===")
    report_lines.append("(Коля+Рома = ложная тревога; Сафар+Тюки на хорде P1-P2 при плывут на P3)")
    for w in [25, 30, 40, 50, 60, 85, global_wide]:
        good_alarm = pct_outside(good_xte, w)
        wrong_alarm = pct_outside(skip_xte_on_p2_leg, w) if skip_xte_on_p2_leg else 0.0
        report_lines.append(f"  ±{w:>2}m: on-route alarm {good_alarm:5.1f}% | skip-P2 alarm {wrong_alarm:5.1f}%")

    report_lines.append(
        "\nВАЖНО: на плече P1->P2 даже Коля/Рома med |XTE|~58 m к прямой — "
        "пловцы огибают залив, не идут по хорде. Skip P2 (med~48 m) почти не отличить "
        "от «правильного» P1->P2. Коридор тут слабый; нужен skip буя."
    )

    gps_w = float(GPS_CORRIDOR_HALF_WIDTH_M)
    width_uniform = {leg.leg_id: gps_w for leg in full_legs}

    map_gpx = SHUCHYE_DIR / "shuchye_corridor_map.gpx"
    write_gpx(
        map_gpx,
        width_uniform,
        swimmer_tracks,
        f"Щучье: коридор GPS ±{int(gps_w)}m + треки 4 пловцов",
    )
    write_gpx(
        SHUCHYE_DIR / f"shuchye_corridor_{int(gps_w)}m.gpx",
        width_uniform,
        {},
        f"Щучье: коридор GPS ±{int(gps_w)}m (только границы)",
    )

    # Remove obsolete wide-corridor exports if present
    for obsolete in (
        SHUCHYE_DIR / "shuchye_corridor_per_leg.gpx",
        SHUCHYE_DIR / "shuchye_corridor_47m_uniform.gpx",
    ):
        if obsolete.exists():
            obsolete.unlink()

    report_lines.append(f"\n=== GPX для карты (GPS-бюджет ±{int(gps_w)} m, не path p95) ===")
    report_lines.append(f"  {map_gpx.name} — границы + треки пловцов (открывать этот)")
    report_lines.append(f"  shuchye_corridor_{int(gps_w)}m.gpx — только границы")
    report_lines.append("  Слои: *center = хорда плеча; L/R = ±20 m. Импорт: gpx.studio, MapMagic.")

    report_path = SHUCHYE_DIR / "corridor_analysis_report.txt"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    report_lines.append(f"Report: {report_path}")

    print("\n".join(report_lines))


if __name__ == "__main__":
    main()
