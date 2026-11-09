"""List every security block (representative point) and waypoint with coordinates
for the Google Earth check, in the order they'll be looked at.

Usage (repo root): python3 ge_checklist.py --data data --out <json>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import geopandas as gpd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    w = Path(a.data) / "work"
    items = []
    blocks = gpd.read_file(w / "timber_blocks.geojson")
    for _, b in blocks.iterrows():
        g = b.geometry
        # core: the largest part's most-interior point
        part = max(getattr(g, "geoms", [g]), key=lambda p: p.area)
        c = gpd.GeoSeries([part.representative_point()], crs=blocks.crs).to_crs(4326).iloc[0]
        items.append({"kind": "block", "id": str(b["id"]), "lat": round(c.y, 5), "lon": round(c.x, 5),
                      "acres": round(float(b.get("acres", 0) or 0))})
    wps = gpd.read_file(w / "waypoints.geojson").to_crs(4326)
    for _, p in wps.sort_values(["area_rank", "wp_type", "name"]).iterrows():
        items.append({"kind": "wp", "id": str(p["wp_id"]), "name": p["name"], "type": p["wp_type"],
                      "area": int(p["area_rank"]) if p["area_rank"] == p["area_rank"] else None,
                      "lat": round(p.geometry.y, 5), "lon": round(p.geometry.x, 5)})
    Path(a.out).write_text(json.dumps(items, indent=1))
    print(len(blocks), "blocks,", len(wps), "waypoints")
    for it in items:
        print(it["kind"], it.get("name", it["id"]), f'{it["lat"]}, {it["lon"]}', it.get("acres", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
