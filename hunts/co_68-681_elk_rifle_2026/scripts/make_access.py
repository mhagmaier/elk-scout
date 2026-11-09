"""ACCESS candidates for an OHV day hunter: public trailheads + ends of Forest
Service routes open to OHVs wider than 50 in on every hunt day.

Writes data/manual/osm_trailheads.geojson (the pipeline ranks these by nearby
composite score and keeps the best, same as OSM trailheads). Candidates must
sit on public land (manual ownership layer) inside the units or within
--buffer-mi of them.

Usage (repo root): python3 make_access.py --data data --start 2026-11-18 --end 2026-11-22
  [--trailheads <public OSM trailheads geojson>]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import geopandas as gpd  # noqa: E402
import pandas as pd  # noqa: E402
from shapely.geometry import Point  # noqa: E402

from elkscout import endpoints  # noqa: E402
from elkscout.cache import Cache  # noqa: E402
from elkscout.grid import Grid  # noqa: E402
from elkscout.net import Net  # noqa: E402
from elkscout.paths import Workspace  # noqa: E402
from elkscout.sources.arcgis import query_layer_geojson  # noqa: E402

UTM = 32613
FIELDS = "id,name,mvum_symbol_name,other_ohv_gt50inches,other_ohv_gt50_datesopen"


def _md(s: str) -> tuple[int, int]:
    m, d = s.strip().split("/")
    return int(m), int(d)


def open_on(dates: str | None, day: dt.date) -> bool:
    """MVUM 'MM/DD-MM/DD[,MM/DD-MM/DD]' windows (wrapping the new year allowed)."""
    if not dates or not isinstance(dates, str):
        return False
    md = (day.month, day.day)
    for span in dates.split(","):
        if "-" not in span:
            continue
        a, b = (_md(x) for x in span.split("-", 1))
        if (a <= b and a <= md <= b) or (a > b and (md >= a or md <= b)):
            return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--start", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--end", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--buffer-mi", type=float, default=1.0)
    ap.add_argument("--trailheads", default=None)
    a = ap.parse_args()
    ws = Workspace(Path(a.data))
    bbox = Grid.load(ws.grid_json).bbox4326()
    net = Net(Cache(ws.cache), offline=False)
    days = [a.start + dt.timedelta(days=i) for i in range((a.end - a.start).days + 1)]

    parts = []
    for layer in (1, 2):
        g = query_layer_geojson(net, endpoints.MVUM, layer, source="mvum_roads", bbox4326=bbox, out_fields=FIELDS)
        if len(g):
            parts.append(g)
    mv = gpd.GeoDataFrame(pd.concat(parts, ignore_index=True), geometry="geometry", crs=4326).to_crs(UTM)
    ok = mv[mv.apply(lambda r: str(r.get("other_ohv_gt50inches") or "").lower() == "open"
                     and all(open_on(r.get("other_ohv_gt50_datesopen"), d) for d in days), axis=1)]
    print(f"MVUM routes in bbox: {len(mv)}; open to OHV >50 in on all of {days[0]}..{days[-1]}: {len(ok)}")

    net_lines = ok.geometry.union_all()
    ends = []
    for _, r in ok.iterrows():
        geoms = getattr(r.geometry, "geoms", [r.geometry])
        for line in geoms:
            for xy in (line.coords[0], line.coords[-1]):
                p = Point(xy)
                # a dead end touches no other open route within 30 m except its own line
                others = ok[ok["id"] != r["id"]]
                if len(others) and others.distance(p).min() < 30:
                    continue
                ends.append({"name": f"FR {r['id']} {str(r['name']).title()} road end", "highway": "road_end",
                             "ref": f"FR {r['id']}", "geometry": p})
    ends = gpd.GeoDataFrame(ends, crs=UTM)

    own = gpd.read_file(ws.manual / "ownership.geojson").to_crs(UTM)
    units = gpd.read_file(ws.manual / "boundary.geojson").to_crs(UTM).geometry.union_all()
    cand = [ends]
    if a.trailheads:
        cand.append(gpd.read_file(a.trailheads).to_crs(UTM))
    cand = gpd.GeoDataFrame(pd.concat(cand, ignore_index=True), geometry="geometry", crs=UTM)
    j = gpd.sjoin(cand, own[["public", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    j = j[(j["public"] == True) & (j.geometry.distance(units) <= a.buffer_mi * 1609.344)]  # noqa: E712
    out = j[["name", "highway", "ref", "geometry"]].to_crs(4326)
    out.to_file(ws.manual_path("osm_trailheads"), driver="GeoJSON")
    print(f"wrote {len(out)} ACCESS candidates -> {ws.manual_path('osm_trailheads')} "
          f"({int((out['highway'] == 'road_end').sum())} road ends, {int((out['highway'] != 'road_end').sum())} trailheads)")
    _ = net_lines
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
