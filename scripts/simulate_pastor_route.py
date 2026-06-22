#!/usr/bin/env python3
"""Prepare Shchuchye (2026-06-14) sim: Kolya GPX + corridor haptic dry-run."""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTE_JSON = ROOT / "routes" / "komarovo_shuchye.buoy_route.json"
TRACK_GPX = ROOT / "routes" / "Щучье20260614" / "Коля.gpx"
OUT_GPX = Path(r"C:\Temp\shuchye_sim.gpx")
OUT_TCX = Path(r"C:\Temp\shuchye_sim.tcx")

# Beach start (ЩучьеОзеро.gpx / field walk 2026-06-14)
START_DEFAULT = (60.209446, 29.789698)

GPX_NS = "http://www.topografix.com/GPX/1/1"
GPX_PT_NS = "{http://www.topografix.com/GPX/1/1}"
GPXDATA_NS = "http://www.cluetrust.com/XML/GPXDATA/1/0"
TCX_NS = "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"
TCX_EXT_NS = "http://www.garmin.com/xmlschemas/ActivityExtension/v2"

# Haptic defaults (match HapticNavigator.mc / properties.xml)
CORRIDOR_HALF_M = 20.0
HYSTERESIS_M = 5.0
ENTER_SEC = 3
CLEAR_SEC = 2
APPROACH_WIN_SEC = 15
APPROACH_PROGRESS_M = 3.0
EMA_ALPHA = 0.3
PULSE_MIN_INTERVAL_SEC = 6
LEG_ENDPOINT_BUFFER_M = 50.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    y = math.sin(dlon) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dlon)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def cross_track_and_along(
    lat: float, lon: float, lat1: float, lon1: float, lat2: float, lon2: float
) -> tuple[float, float, float]:
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


def parse_gpx(path: Path) -> list[tuple[datetime, float, float]]:
    root = ET.parse(path).getroot()
    pts: list[tuple[datetime, float, float]] = []
    for trkpt in root.iter(GPX_PT_NS + "trkpt"):
        lat = float(trkpt.get("lat"))
        lon = float(trkpt.get("lon"))
        t_el = trkpt.find(GPX_PT_NS + "time")
        if t_el is None or not t_el.text:
            continue
        t = datetime.fromisoformat(t_el.text.replace("Z", "+00:00"))
        pts.append((t, lat, lon))
    return pts


@dataclass
class RouteConfig:
    start: tuple[float, float]
    buoys: dict[str, tuple[float, float]]
    order: list[str]
    radius_m: float
    dwell_sec: int


def load_route() -> RouteConfig:
    data = json.loads(ROUTE_JSON.read_text(encoding="utf-8"))
    start_data = data.get("start")
    if start_data:
        start = (start_data["lat"], start_data["lon"])
    else:
        start = START_DEFAULT
    buoys = {pid: (p["lat"], p["lon"]) for pid, p in data["points"].items()}
    order = list(data["session"]["order"])
    radius_m = float(data.get("arrivalRadiusM", 20))
    dwell_sec = int(data.get("dwellSec", 4))
    return RouteConfig(start, buoys, order, radius_m, dwell_sec)


def write_gpx(points: list[tuple[datetime, float, float]], path: Path) -> None:
    """Garmin CIQ simulator expects swim GPX with type + gpxdata extensions."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.register_namespace("", GPX_NS)
    ET.register_namespace("gpxdata", GPXDATA_NS)

    gpx = ET.Element(
        f"{{{GPX_NS}}}gpx",
        {
            "version": "1.1",
            "creator": "SwimBuoy",
            "xmlns": GPX_NS,
            "xmlns:gpxdata": GPXDATA_NS,
        },
    )
    meta = ET.SubElement(gpx, f"{{{GPX_NS}}}metadata")
    ET.SubElement(meta, f"{{{GPX_NS}}}time").text = points[0][0].strftime("%Y-%m-%dT%H:%M:%SZ")

    trk = ET.SubElement(gpx, f"{{{GPX_NS}}}trk")
    ET.SubElement(trk, f"{{{GPX_NS}}}name").text = "Kolya Shchuchye 2026-06-14"
    ET.SubElement(trk, f"{{{GPX_NS}}}type").text = "swim"
    seg_el = ET.SubElement(trk, f"{{{GPX_NS}}}trkseg")

    cum_dist = 0.0
    prev: tuple[float, float] | None = None
    prev_t: datetime | None = None
    for t, lat, lon in points:
        speed = 1.5
        if prev is not None and prev_t is not None:
            dt = (t - prev_t).total_seconds()
            if dt > 0:
                speed = haversine(prev[0], prev[1], lat, lon) / dt
            cum_dist += haversine(prev[0], prev[1], lat, lon)
        prev = (lat, lon)
        prev_t = t
        trkpt = ET.SubElement(
            seg_el,
            f"{{{GPX_NS}}}trkpt",
            {"lat": f"{lat:.7f}", "lon": f"{lon:.7f}"},
        )
        ET.SubElement(trkpt, f"{{{GPX_NS}}}ele").text = "50"
        ET.SubElement(trkpt, f"{{{GPX_NS}}}time").text = t.strftime("%Y-%m-%dT%H:%M:%SZ")
        ext = ET.SubElement(trkpt, f"{{{GPX_NS}}}extensions")
        ET.SubElement(ext, f"{{{GPXDATA_NS}}}distance").text = f"{cum_dist:.2f}"
        ET.SubElement(ext, f"{{{GPXDATA_NS}}}cadence").text = "22"
        ET.SubElement(ext, f"{{{GPXDATA_NS}}}speed").text = f"{speed:.3f}"

    tree = ET.ElementTree(gpx)
    ET.indent(tree, space=" ")
    tree.write(path, encoding="UTF-8", xml_declaration=True)


def write_tcx(points: list[tuple[datetime, float, float]], path: Path) -> None:
    """TCX is the most reliable format for CIQ Activity Data playback."""
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.register_namespace("", TCX_NS)

    root = ET.Element(f"{{{TCX_NS}}}TrainingCenterDatabase")
    acts = ET.SubElement(root, f"{{{TCX_NS}}}Activities")
    act = ET.SubElement(acts, f"{{{TCX_NS}}}Activity", {"Sport": "Other"})
    act_id = points[0][0].strftime("%Y-%m-%dT%H:%M:%S.000Z")
    ET.SubElement(act, f"{{{TCX_NS}}}Id").text = act_id

    lap = ET.SubElement(act, f"{{{TCX_NS}}}Lap", {"StartTime": act_id})
    track = ET.SubElement(lap, f"{{{TCX_NS}}}Track")

    cum_dist = 0.0
    prev: tuple[float, float] | None = None
    prev_t: datetime | None = None
    for t, lat, lon in points:
        speed = 1.5
        if prev is not None and prev_t is not None:
            dt = (t - prev_t).total_seconds()
            if dt > 0:
                speed = haversine(prev[0], prev[1], lat, lon) / dt
            cum_dist += haversine(prev[0], prev[1], lat, lon)
        prev = (lat, lon)
        prev_t = t
        tp = ET.SubElement(track, f"{{{TCX_NS}}}Trackpoint")
        ET.SubElement(tp, f"{{{TCX_NS}}}Time").text = t.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        pos = ET.SubElement(tp, f"{{{TCX_NS}}}Position")
        ET.SubElement(pos, f"{{{TCX_NS}}}LatitudeDegrees").text = f"{lat:.7f}"
        ET.SubElement(pos, f"{{{TCX_NS}}}LongitudeDegrees").text = f"{lon:.7f}"
        ET.SubElement(tp, f"{{{TCX_NS}}}AltitudeMeters").text = "50"
        ET.SubElement(tp, f"{{{TCX_NS}}}DistanceMeters").text = f"{cum_dist:.2f}"
        ext = ET.SubElement(tp, f"{{{TCX_NS}}}Extensions")
        tpx = ET.SubElement(ext, f"{{{TCX_EXT_NS}}}TPX")
        ET.SubElement(tpx, f"{{{TCX_EXT_NS}}}Speed").text = f"{speed:.3f}"

    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(path, encoding="UTF-8", xml_declaration=True)


class HapticSim:
    def __init__(self) -> None:
        self.clear_width = CORRIDOR_HALF_M - HYSTERESIS_M
        self.smoothed_dist: float | None = None
        self.smoothed_xte: float | None = None
        self.dist_history: list[tuple[int, float]] = []
        self.is_outside = False
        self.outside_sec = 0
        self.inside_sec = 0
        self.buoy_changed_at = 0
        self.last_pulse_sec = -100
        self.pulses: list[tuple[int, str, float]] = []

    def reset(self, dist: float, xte: float, sec: int) -> None:
        self.smoothed_dist = dist
        self.smoothed_xte = xte
        self.dist_history = [(sec, dist)]
        self.is_outside = False
        self.outside_sec = 0
        self.inside_sec = 0
        self.buoy_changed_at = sec
        self.last_pulse_sec = -100

    def approaching(self, sec: int) -> bool:
        if self.smoothed_dist is None:
            return False
        target = sec - APPROACH_WIN_SEC
        best = None
        best_delta = 999999
        for s, d in self.dist_history:
            delta = abs(s - target)
            if delta < best_delta:
                best_delta = delta
                best = d
        if best is None or best_delta > APPROACH_WIN_SEC:
            return False
        return (self.smoothed_dist - best) <= -APPROACH_PROGRESS_M

    def update(
        self,
        sec: int,
        raw_dist: float,
        raw_xte: float,
        along_valid: bool,
        inside_radius: bool,
        active_buoy: str,
    ) -> bool:
        if inside_radius or sec - self.buoy_changed_at < ENTER_SEC or not along_valid:
            return False
        if self.smoothed_dist is None:
            self.reset(raw_dist, raw_xte, sec)
            return False

        self.smoothed_dist = (1 - EMA_ALPHA) * self.smoothed_dist + EMA_ALPHA * raw_dist
        self.smoothed_xte = (1 - EMA_ALPHA) * self.smoothed_xte + EMA_ALPHA * raw_xte
        self.dist_history.append((sec, self.smoothed_dist))
        cutoff = sec - APPROACH_WIN_SEC - 2
        self.dist_history = [(s, d) for s, d in self.dist_history if s >= cutoff]

        approaching = self.approaching(sec)
        xte = self.smoothed_xte

        if xte > CORRIDOR_HALF_M:
            self.outside_sec += 1
            self.inside_sec = 0
        elif xte < self.clear_width:
            self.inside_sec += 1
            self.outside_sec = 0
        else:
            self.outside_sec = 0
            self.inside_sec = 0

        if self.is_outside:
            if self.inside_sec >= CLEAR_SEC or approaching:
                self.is_outside = False
                self.outside_sec = 0
                self.inside_sec = 0
        elif self.outside_sec >= ENTER_SEC and not approaching:
            self.is_outside = True

        if self.is_outside and sec - self.last_pulse_sec >= PULSE_MIN_INTERVAL_SEC:
            self.last_pulse_sec = sec
            self.pulses.append((sec, active_buoy, xte))
            return True
        return False


def simulate_route(
    timed_pts: list[tuple[datetime, float, float]],
    route: RouteConfig,
) -> None:
    order = route.order
    active_idx = 0
    dwell_start: int | None = None
    session_start = timed_pts[0][1:]
    haptic = HapticSim()
    prev_buoy: str | None = None

    duration_min = int((timed_pts[-1][0] - timed_pts[0][0]).total_seconds() // 60)
    print("\n=== Corridor haptic simulation (Shchuchye, Kolya) ===")
    print(f"Route: {ROUTE_JSON.name}")
    print(f"Track: {TRACK_GPX.name}")
    print(f"Points: {len(timed_pts)}, ~{duration_min} min, corridor ±{CORRIDOR_HALF_M:.0f} m\n")

    for t, lat, lon in timed_pts:
        sec = int((t - timed_pts[0][0]).total_seconds())
        active_buoy = order[active_idx]

        if active_idx == 0:
            leg_from = session_start
        else:
            leg_from = route.buoys[order[active_idx - 1]]
        leg_to = route.buoys[active_buoy]

        dist = haversine(lat, lon, leg_to[0], leg_to[1])
        xte_signed, along, leg_len = cross_track_and_along(
            lat, lon, leg_from[0], leg_from[1], leg_to[0], leg_to[1]
        )
        abs_xte = abs(xte_signed)
        along_valid = LEG_ENDPOINT_BUFFER_M <= along <= leg_len - LEG_ENDPOINT_BUFFER_M
        inside = dist <= route.radius_m

        if active_buoy != prev_buoy:
            haptic.reset(dist, abs_xte, sec)
            prev_buoy = active_buoy
            dwell_start = None

        pulsed = haptic.update(sec, dist, abs_xte, along_valid, inside, active_buoy)
        if pulsed:
            leg_label = f"{order[active_idx - 1]}->{active_buoy}" if active_idx else f"start->{active_buoy}"
            print(
                f"  t={sec:4d}s  VIBRO  buoy={active_buoy}  "
                f"|XTE|={abs_xte:.1f}m  dist={dist:.0f}m  leg={leg_label}"
            )

        if inside:
            if dwell_start is None:
                dwell_start = sec
            if sec - dwell_start >= route.dwell_sec and active_idx < len(order) - 1:
                active_idx += 1
                dwell_start = None
        else:
            dwell_start = None

    print(f"\nTotal haptic pulses: {len(haptic.pulses)}")
    credited = active_idx
    print(
        f"Buoys credited by dwell: {credited}/{len(order)} "
        f"(last active: {order[min(active_idx, len(order) - 1)]})"
    )


def main() -> None:
    if not TRACK_GPX.is_file():
        raise SystemExit(f"Track not found: {TRACK_GPX}")

    route = load_route()
    timed = parse_gpx(TRACK_GPX)
    if not timed:
        raise SystemExit(f"No track points in {TRACK_GPX}")

    write_gpx(timed, OUT_GPX)
    write_tcx(timed, OUT_TCX)
    duration_min = int((timed[-1][0] - timed[0][0]).total_seconds() // 60)
    print(f"GPX written: {OUT_GPX} ({len(timed)} points, ~{duration_min} min)")
    print(f"TCX written: {OUT_TCX}  <- use this in CIQ Simulator (Activity Data)")
    simulate_route(timed, route)


if __name__ == "__main__":
    main()
