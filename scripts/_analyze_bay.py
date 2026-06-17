import xml.etree.ElementTree as ET
from pathlib import Path

root = ET.parse(Path(__file__).parent / "_hepo.osm").getroot()
nodes = {n.get("id"): (float(n.get("lat")), float(n.get("lon"))) for n in root.findall("node")}
ways = {w.get("id"): w for w in root.findall("way")}
rel = next(r for r in root.findall("relation") if r.find("tag[@k='name:fi']") is not None)
ring = []
for m in rel.findall("member"):
    if m.get("type") != "way" or m.get("role") != "outer":
        continue
    w = ways[m.get("ref")]
    coords = [nodes[nd.get("ref")] for nd in w.findall("nd") if nd.get("ref") in nodes]
    if ring and coords and ring[-1] == coords[0]:
        ring.extend(coords[1:])
    else:
        ring.extend(coords)

west = min(lon for _, lon in ring)
south = min(lat for lat, _ in ring)
print(f"lake west_lon={west:.6f} south_lat={south:.6f}")

# SW corner / Aunelanlahti mouth
sw = [p for p in ring if p[1] < west + 0.014 and p[0] < 60.162]
print(f"SW vertices: {len(sw)}, lat {min(p[0] for p in sw):.6f}-{max(p[0] for p in sw):.6f}, lon {min(p[1] for p in sw):.6f}-{max(p[1] for p in sw):.6f}")
for p in sorted(sw, key=lambda x: (-x[1], x[0]))[:25]:
    print(f"  {p[0]:.6f}, {p[1]:.6f}")
