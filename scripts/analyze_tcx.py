#!/usr/bin/env python3
"""Analyze TCX walk track: stops, turns, sample points."""
import math
import sys
import xml.etree.ElementTree as ET
from datetime import datetime

NS = {
    "tcx": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
    "ns3": "http://www.garmin.com/xmlschemas/ActivityExtension/v2",
}


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def parse_tcx(path):
    root = ET.parse(path).getroot()
    points = []
    for tp in root.iter("{http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2}Trackpoint"):
        t_el = tp.find("tcx:Time", NS)
        pos = tp.find("tcx:Position", NS)
        if t_el is None or pos is None:
            continue
        lat = float(pos.find("tcx:LatitudeDegrees", NS).text)
        lon = float(pos.find("tcx:LongitudeDegrees", NS).text)
        t = datetime.fromisoformat(t_el.text.replace("Z", "+00:00"))
        dist_el = tp.find("tcx:DistanceMeters", NS)
        dist = float(dist_el.text) if dist_el is not None else None
        speed = None
        ext = tp.find("tcx:Extensions", NS)
        if ext is not None:
            tpx = ext.find(".//ns3:Speed", NS)
            if tpx is not None:
                speed = float(tpx.text)
        points.append({"t": t, "lat": lat, "lon": lon, "dist": dist, "speed": speed})
    return points


def find_stops(points, speed_thresh=0.35, min_dur=4):
    stops = []
    i = 0
    while i < len(points):
        sp = points[i]["speed"]
        if sp is not None and sp < speed_thresh:
            j = i
            while j < len(points) and points[j]["speed"] is not None and points[j]["speed"] < speed_thresh:
                j += 1
            dur = (points[j - 1]["t"] - points[i]["t"]).total_seconds() if j > i else 0
            if dur >= min_dur and j - i >= 3:
                seg = points[i:j]
                lat = sum(p["lat"] for p in seg) / len(seg)
                lon = sum(p["lon"] for p in seg) / len(seg)
                stops.append(
                    {
                        "dur": dur,
                        "lat": lat,
                        "lon": lon,
                        "dist": seg[-1]["dist"],
                        "t": seg[0]["t"],
                    }
                )
            i = j
        else:
            i += 1
    return stops


def merge_nearby(stops, min_sep_m=25):
    if not stops:
        return stops
    merged = [stops[0]]
    for s in stops[1:]:
        prev = merged[-1]
        if haversine(prev["lat"], prev["lon"], s["lat"], s["lon"]) < min_sep_m:
            if s["dur"] > prev["dur"]:
                merged[-1] = s
        else:
            merged.append(s)
    return merged


def sample_by_distance(points, step_m=100, skip_first_m=0):
    if not points:
        return []
    samples = []
    next_d = skip_first_m + step_m
    for p in points:
        if p["dist"] is None:
            continue
        if p["dist"] >= next_d:
            samples.append({"dist": p["dist"], "lat": p["lat"], "lon": p["lon"]})
            next_d += step_m
    return samples


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else r"c:\Users\Смирнов Николай\Downloads\activity_22998898995 (1).tcx"
    points = parse_tcx(path)
    print(f"trackpoints: {len(points)}")
    if not points:
        return
    print(f"time: {points[0]['t']} -> {points[-1]['t']}")
    print(f"distance: {points[-1]['dist']:.1f} m")
    lats = [p["lat"] for p in points]
    lons = [p["lon"] for p in points]
    print(f"bbox: lat [{min(lats):.6f}, {max(lats):.6f}] lon [{min(lons):.6f}, {max(lons):.6f}]")

    stops = merge_nearby(find_stops(points))
    print(f"\n=== STOPS (pauses >= 4s, speed < 0.35 m/s): {len(stops)} ===")
    for k, s in enumerate(stops):
        print(
            f"  {k+1}: dur={s['dur']:.0f}s dist={s['dist']:.1f}m "
            f"lat={s['lat']:.7f} lon={s['lon']:.7f}"
        )

    # skip first 100m lap if present
    samples = sample_by_distance(points, step_m=100, skip_first_m=100)
    print(f"\n=== EVERY 100m after 100m: {len(samples)} ===")
    for k, s in enumerate(samples):
        print(f"  {k+1}: dist={s['dist']:.1f}m lat={s['lat']:.7f} lon={s['lon']:.7f}")

    start = points[0]
    end = points[-1]
    print(f"\nSTART: lat={start['lat']:.7f} lon={start['lon']:.7f}")
    print(f"END:   lat={end['lat']:.7f} lon={end['lon']:.7f}")


if __name__ == "__main__":
    main()
