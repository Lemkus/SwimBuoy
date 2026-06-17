#!/usr/bin/env python3
"""Detect and collapse GPS jitter while standing still in a GPX track.

When you pause (or GPS wanders in a small area), the track accumulates zigzag
segments. This script finds such clusters and replaces each with one point.

Usage:
  python scripts/dedupe_gps_jitter_gpx.py activity.gpx
  python scripts/dedupe_gps_jitter_gpx.py activity.gpx -o cleaned.gpx --dry-run
"""
from __future__ import annotations

import argparse
import copy
import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

GPX_NS = "http://www.topografix.com/GPX/1/1"
NS = {"gpx": GPX_NS}


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


@dataclass
class TrackPoint:
    element: ET.Element
    lat: float
    lon: float
    time: datetime | None


@dataclass
class JitterCluster:
    start: int
    end: int  # exclusive
    path_m: float
    displacement_m: float
    spread_m: float
    centroid_lat: float
    centroid_lon: float
    duration_s: float | None


def parse_gpx(path: Path) -> tuple[ET.ElementTree, list[TrackPoint]]:
    tree = ET.parse(path)
    root = tree.getroot()
    points: list[TrackPoint] = []
    for trkpt in root.findall(".//gpx:trkpt", NS):
        lat = float(trkpt.get("lat"))
        lon = float(trkpt.get("lon"))
        t_el = trkpt.find("gpx:time", NS)
        t = None
        if t_el is not None and t_el.text:
            t = datetime.fromisoformat(t_el.text.replace("Z", "+00:00"))
        points.append(TrackPoint(trkpt, lat, lon, t))
    return tree, points


def segment_path_m(points: list[TrackPoint], start: int, end: int) -> float:
    return sum(
        haversine(points[i].lat, points[i].lon, points[i + 1].lat, points[i + 1].lon)
        for i in range(start, end - 1)
    )


def segment_centroid(points: list[TrackPoint], start: int, end: int) -> tuple[float, float]:
    n = end - start
    lat = sum(points[i].lat for i in range(start, end)) / n
    lon = sum(points[i].lon for i in range(start, end)) / n
    return lat, lon


def segment_spread_m(points: list[TrackPoint], start: int, end: int, clat: float, clon: float) -> float:
    return max(haversine(clat, clon, points[i].lat, points[i].lon) for i in range(start, end))


def max_segment_speed_mps(points: list[TrackPoint], start: int, end: int) -> float:
    peak = 0.0
    for i in range(start, end - 1):
        dt = 1.0
        if points[i].time and points[i + 1].time:
            dt = max((points[i + 1].time - points[i].time).total_seconds(), 0.1)
        d = haversine(points[i].lat, points[i].lon, points[i + 1].lat, points[i + 1].lon)
        peak = max(peak, d / dt)
    return peak


def expand_cluster(
    points: list[TrackPoint],
    start: int,
    end: int,
    expand_radius_m: float,
) -> tuple[int, int, float, float]:
    clat, clon = segment_centroid(points, start, end)
    changed = True
    while changed:
        changed = False
        while start > 0:
            prev = points[start - 1]
            if haversine(clat, clon, prev.lat, prev.lon) <= expand_radius_m:
                start -= 1
                changed = True
            else:
                break
        while end < len(points):
            nxt = points[end]
            if haversine(clat, clon, nxt.lat, nxt.lon) <= expand_radius_m:
                end += 1
                changed = True
            else:
                break
        if changed:
            clat, clon = segment_centroid(points, start, end)
    return start, end, clat, clon


def find_local_zigzag_clusters(
    points: list[TrackPoint],
    *,
    max_window: int = 20,
    max_spread_m: float = 8.0,
    min_points: int = 4,
    min_path_m: float = 4.0,
    min_path_to_disp_ratio: float = 2.5,
) -> list[JitterCluster]:
    """Find short embedded zigzags (do not grow segment — avoids swallowing whole laps)."""
    clusters: list[JitterCluster] = []
    i = 0
    n = len(points)
    while i < n:
        best: JitterCluster | None = None
        max_size = min(max_window, n - i)
        for size in range(min_points, max_size + 1):
            end = i + size
            clat, clon = segment_centroid(points, i, end)
            spread = segment_spread_m(points, i, end, clat, clon)
            if spread > max_spread_m:
                break
            path_m = segment_path_m(points, i, end)
            disp_m = haversine(points[i].lat, points[i].lon, points[end - 1].lat, points[end - 1].lon)
            ratio = path_m / max(disp_m, 0.2)
            if path_m >= min_path_m and ratio >= min_path_to_disp_ratio:
                t0, t1 = points[i].time, points[end - 1].time
                dur = (t1 - t0).total_seconds() if t0 and t1 else None
                best = JitterCluster(i, end, path_m, disp_m, spread, clat, clon, dur)
        if best is not None:
            clusters.append(best)
            i = best.end
        else:
            i += 1
    return clusters


def find_jitter_clusters(
    points: list[TrackPoint],
    *,
    max_spread_m: float = 20.0,
    expand_radius_m: float = 30.0,
    min_points: int = 4,
    min_path_m: float = 4.0,
    min_path_to_disp_ratio: float = 2.0,
    max_speed_mps: float | None = 0.8,
    expand: bool = True,
) -> list[JitterCluster]:
    clusters: list[JitterCluster] = []
    i = 0
    n = len(points)
    while i < n:
        j = i + 1
        while j < n:
            clat, clon = segment_centroid(points, i, j + 1)
            spread = segment_spread_m(points, i, j + 1, clat, clon)
            if spread > max_spread_m:
                break
            j += 1

        seg_end = j
        seg_len = seg_end - i
        if seg_len >= min_points:
            path_m = segment_path_m(points, i, seg_end)
            disp_m = haversine(points[i].lat, points[i].lon, points[seg_end - 1].lat, points[seg_end - 1].lon)
            clat, clon = segment_centroid(points, i, seg_end)
            spread = segment_spread_m(points, i, seg_end, clat, clon)
            ratio = path_m / max(disp_m, 0.3)

            slow_enough = True
            if max_speed_mps is not None:
                slow_enough = max_segment_speed_mps(points, i, seg_end) <= max_speed_mps * 2

            if path_m >= min_path_m and ratio >= min_path_to_disp_ratio and slow_enough:
                start, end, clat, clon = (
                    expand_cluster(points, i, seg_end, expand_radius_m)
                    if expand
                    else (i, seg_end, *segment_centroid(points, i, seg_end))
                )
                path_m = segment_path_m(points, start, end)
                disp_m = haversine(points[start].lat, points[start].lon, points[end - 1].lat, points[end - 1].lon)
                spread = segment_spread_m(points, start, end, clat, clon)
                t0, t1 = points[start].time, points[end - 1].time
                dur = (t1 - t0).total_seconds() if t0 and t1 else None
                clusters.append(JitterCluster(start, end, path_m, disp_m, spread, clat, clon, dur))
                i = end
                continue

        i += 1
    return clusters


def collapse_duplicates(points: list[TrackPoint], tolerance_m: float = 0.2) -> tuple[list[TrackPoint], int]:
    if not points:
        return points, 0
    result = [points[0]]
    removed = 0
    for p in points[1:]:
        prev = result[-1]
        if haversine(prev.lat, prev.lon, p.lat, p.lon) <= tolerance_m:
            removed += 1
            continue
        result.append(p)
    return result, removed


def collapse_cluster(points: list[TrackPoint], cluster: JitterCluster) -> list[TrackPoint]:
    if cluster.end - cluster.start <= 1:
        return points

    result: list[TrackPoint] = []
    for idx, p in enumerate(points):
        if cluster.start <= idx < cluster.end:
            if idx != cluster.start:
                continue
            el = copy.deepcopy(p.element)
            el.set("lat", f"{cluster.centroid_lat:.8f}")
            el.set("lon", f"{cluster.centroid_lon:.8f}")
            result.append(TrackPoint(el, cluster.centroid_lat, cluster.centroid_lon, p.time))
        else:
            result.append(p)
    return result


def apply_all_collapses(points: list[TrackPoint], clusters: list[JitterCluster]) -> list[TrackPoint]:
    result = points
    for cluster in sorted(clusters, key=lambda c: c.start, reverse=True):
        result = collapse_cluster(result, cluster)
    return result


def clean_track(
    points: list[TrackPoint],
    *,
    max_spread_m: float,
    expand_radius_m: float,
    min_points: int,
    min_path_m: float,
    min_ratio: float,
    max_speed_mps: float | None,
    max_passes: int,
) -> tuple[list[TrackPoint], list[JitterCluster]]:
    all_clusters: list[JitterCluster] = []
    current = points
    for pass_no in range(1, max_passes + 1):
        current, dup_removed = collapse_duplicates(current)
        if dup_removed:
            print(f"  pass {pass_no}: removed {dup_removed} duplicate points")

        clusters = find_jitter_clusters(
            current,
            max_spread_m=max_spread_m,
            expand_radius_m=expand_radius_m,
            min_points=min_points,
            min_path_m=min_path_m,
            min_path_to_disp_ratio=min_ratio,
            max_speed_mps=max_speed_mps,
            expand=True,
        )
        local = find_local_zigzag_clusters(
            current,
            max_window=20,
            max_spread_m=min(max_spread_m, 8.0),
            min_points=min_points,
            min_path_m=min_path_m,
            min_path_to_disp_ratio=max(min_ratio, 2.5),
        )
        merged = clusters + [c for c in local if not any(not (c.end <= o.start or c.start >= o.end) for o in clusters)]
        if not merged:
            break

        print(f"  pass {pass_no}: {len(clusters)} large + {len(merged) - len(clusters)} local cluster(s)")
        all_clusters.extend(merged)
        current = apply_all_collapses(current, merged)

    return current, all_clusters


def write_gpx(tree: ET.ElementTree, points: list[TrackPoint], out_path: Path) -> None:
    root = tree.getroot()
    for trkseg in root.findall(".//gpx:trkseg", NS):
        for trkpt in list(trkseg.findall("gpx:trkpt", NS)):
            trkseg.remove(trkpt)
        for pt in points:
            trkseg.append(pt.element)

    for trk in root.findall(".//gpx:trk", NS):
        name_el = trk.find("gpx:name", NS)
        label = "SwimBuoy jitter-cleaned"
        if name_el is None:
            name_el = ET.SubElement(trk, f"{{{GPX_NS}}}name")
        name_el.text = label

    ET.register_namespace("", GPX_NS)
    tree.write(out_path, encoding="UTF-8", xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collapse GPS jitter clusters in GPX tracks")
    parser.add_argument("input", type=Path, help="Input GPX file")
    parser.add_argument("-o", "--output", type=Path, help="Output GPX (default: <input>_cleaned.gpx)")
    parser.add_argument("--dry-run", action="store_true", help="Only report clusters, do not write")
    parser.add_argument("--max-spread", type=float, default=20.0, help="Max radius from centroid (m)")
    parser.add_argument("--expand-radius", type=float, default=30.0, help="Absorb approach/departure drift (m)")
    parser.add_argument("--min-points", type=int, default=4, help="Min points in a jitter cluster")
    parser.add_argument("--min-path", type=float, default=4.0, help="Min zigzag path length (m)")
    parser.add_argument("--min-ratio", type=float, default=2.0, help="Min path/displacement ratio")
    parser.add_argument("--max-speed", type=float, default=0.8, help="Max segment speed (m/s); 0 = disable")
    parser.add_argument("--passes", type=int, default=5, help="Max cleaning passes")
    args = parser.parse_args()

    if not args.input.exists():
        print(f"error: file not found: {args.input}", file=sys.stderr)
        return 1

    tree, points = parse_gpx(args.input)
    print(f"trackpoints: {len(points)}")

    max_speed = args.max_speed if args.max_speed > 0 else None
    clusters = find_jitter_clusters(
        points,
        max_spread_m=args.max_spread,
        expand_radius_m=args.expand_radius,
        min_points=args.min_points,
        min_path_m=args.min_path,
        min_path_to_disp_ratio=args.min_ratio,
        max_speed_mps=max_speed,
        expand=True,
    )

    if not clusters and args.dry_run:
        print("No jitter clusters found.")
        return 0

    if args.dry_run:
        print(f"\n=== JITTER CLUSTERS (first pass): {len(clusters)} ===")
        for k, c in enumerate(clusters, 1):
            n = c.end - c.start
            t0 = points[c.start].time
            print(
                f"  {k}: idx {c.start}-{c.end - 1} ({n} pts, {c.duration_s:.0f}s)\n"
                f"      path={c.path_m:.1f}m  disp={c.displacement_m:.1f}m  spread={c.spread_m:.1f}m\n"
                f"      centroid {c.centroid_lat:.7f}, {c.centroid_lon:.7f}  @ {t0}"
            )
        return 0

    print("Cleaning...")
    cleaned, all_clusters = clean_track(
        points,
        max_spread_m=args.max_spread,
        expand_radius_m=args.expand_radius,
        min_points=args.min_points,
        min_path_m=args.min_path,
        min_ratio=args.min_ratio,
        max_speed_mps=max_speed,
        max_passes=args.passes,
    )

    removed = len(points) - len(cleaned)
    print(f"\nTotal: {len(points)} -> {len(cleaned)} points ({removed} removed, {len(all_clusters)} clusters)")

    if not all_clusters:
        print("No jitter clusters found.")
        return 0

    out = args.output or args.input.with_name(args.input.stem + "_cleaned.gpx")
    write_gpx(tree, cleaned, out)
    print(f"Wrote {out}")
    print("Track name in GPX: 'SwimBuoy jitter-cleaned' — check this label in your map app.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
