#!/usr/bin/env python3
"""Place ~1 km buoy loop in Aunelanlahti (western Hepojarvi bay)."""
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

OSM = Path(__file__).resolve().parent / "_hepo.osm"
# Перед первым запуском скачать полигон озера (см. docs/new-route-and-app.md):
# curl.exe -s "https://www.openstreetmap.org/api/0.6/relation/1445795/full" -o scripts\_hepo.osm
OUT_JSON = Path(__file__).resolve().parents[1] / "routes" / "toksovo_aunelanlahti.buoy_route.json"
TARGET_M = 1000.0


def haversine(lat1, lon1, lat2, lon2):
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def point_in_polygon(lat, lon, polygon):
    x, y = lon, lat
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i][1], polygon[i][0]
        xj, yj = polygon[j][1], polygon[j][0]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi + 1e-15) + xi):
            inside = not inside
        j = i
    return inside


def load_lake_polygon(path):
    root = ET.parse(path).getroot()
    nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
    ways = {w.get("id"): w for w in root.findall("way")}
    rel = next(r for r in root.findall("relation") if r.find("tag[@k='name:fi']") is not None)
    outer_refs = [
        m.get("ref") for m in rel.findall("member") if m.get("type") == "way" and m.get("role") == "outer"
    ]
    ring = []
    for ref in outer_refs:
        w = ways[ref]
        coords = [nodes[nd.get("ref")] for nd in w.findall("nd") if nd.get("ref") in nodes]
        if ring and coords and ring[-1] == coords[0]:
            ring.extend(coords[1:])
        else:
            ring.extend(coords)
    return ring


def loop_length(coords):
    return sum(
        haversine(coords[i][0], coords[i][1], coords[(i + 1) % len(coords)][0], coords[(i + 1) % len(coords)][1])
        for i in range(len(coords))
    )


def offset_m(lat, lon, bearing_deg, dist_m):
    br = math.radians(bearing_deg)
    dlat = (dist_m * math.cos(br)) / 111320.0
    dlon = (dist_m * math.sin(br)) / (111320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def nudge_inside(lat, lon, poly):
    if point_in_polygon(lat, lon, poly):
        return lat, lon
    for step in range(1, 50):
        for dlat, dlon in [(0.0001, 0.0001), (0.00015, 0), (0, 0.00015), (-0.0001, 0.0001)]:
            tlat, tlon = lat + step * dlat, lon + step * dlon
            if point_in_polygon(tlat, tlon, poly):
                return tlat, tlon
    return lat, lon


def regular_loop(center_lat, center_lon, radius_m, rotation_deg, poly):
    coords = []
    for i in range(5):
        bearing = rotation_deg + i * 72
        lat, lon = offset_m(center_lat, center_lon, bearing, radius_m)
        lat, lon = nudge_inside(lat, lon, poly)
        coords.append((lat, lon))
    return coords


def main():
    poly = load_lake_polygon(OSM)
    west_lon = min(lon for _, lon in poly)
    # Aunelanlahti: western bay, beach у «Северный склон» (~60.156, 30.547)
    center_lat, center_lon = 60.1608, west_lon + 0.0058

    best = None
    for radius in range(120, 260, 5):
        for rot in range(0, 360, 10):
            coords = regular_loop(center_lat, center_lon, radius, rot, poly)
            if not all(point_in_polygon(lat, lon, poly) for lat, lon in coords):
                continue
            legs = [
                haversine(coords[i][0], coords[i][1], coords[(i + 1) % 5][0], coords[(i + 1) % 5][1])
                for i in range(5)
            ]
            if min(legs) < 120:
                continue
            length = sum(legs)
            err = abs(length - TARGET_M)
            if best is None or err < best[0]:
                best = (err, radius, rot, length, coords)

    if best is None:
        raise SystemExit("Could not place loop")

    _, radius, rot, length, coords = best
    # Rotate so P1 is closest to beach (Severny Sklon)
    beach = (60.1560, 30.5475)
    start_i = min(range(5), key=lambda i: haversine(coords[i][0], coords[i][1], beach[0], beach[1]))
    coords = coords[start_i:] + coords[:start_i]

    names = ["Старт", "Буй 2", "Буй 3", "Буй 4", "Финиш"]
    points = {
        f"P{i + 1}": {"lat": round(lat, 7), "lon": round(lon, 7), "name": names[i]}
        for i, (lat, lon) in enumerate(coords)
    }

    route = {
        "routeId": "toksovo_aunelanlahti_01",
        "name": "Токсово, залив Аунеланлахти (~1 км)",
        "guidanceMode": "point_proximity",
        "arrivalRadiusM": 20,
        "dwellSec": 4,
        "points": points,
        "session": {
            "orderMode": "fixed",
            "order": ["P1", "P2", "P3", "P4", "P5"],
            "activeIndex": 0,
            "taken": [],
        },
    }
    OUT_JSON.write_text(json.dumps(route, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"radius={radius}m rot={rot} perimeter={length:.0f}m")
    for pid in ["P1", "P2", "P3", "P4", "P5"]:
        p = points[pid]
        print(f"  {pid} {p['lat']}, {p['lon']}")


if __name__ == "__main__":
    main()
