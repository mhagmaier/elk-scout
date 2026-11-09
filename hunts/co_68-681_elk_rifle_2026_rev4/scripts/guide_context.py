"""Guide context for the revision-4 run (read-only on data/work).

Per waypoint: land (agency or CPW public-access parcel), nearest legal road end
for the profile vehicle (name, straight-line mi, climb ft), nearest legal MVUM
route (any point along it). Per hunt area: drain direction (plane fit to the DEM
over the area's waypoint hull + 1 km). Per block: nearest legal route and the
waypoints within 1 mi.

Usage (repo root): python3 guide_context.py --data data --config <profile.yaml> --out work/guide_context.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
from rasterio.features import geometry_mask  # noqa: E402

from elkscout.access import legal_routes  # noqa: E402
from elkscout.config import load_config  # noqa: E402

M_PER_MI = 1609.344
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg: float) -> str:
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    w = Path(a.data) / "work"
    cfg = load_config(a.config)
    epsg = cfg.grid.epsg
    days = [cfg.hunt_window.start + dt.timedelta(days=i) for i in range((cfg.hunt_window.end - cfg.hunt_window.start).days + 1)]

    wp = gpd.read_file(w / "waypoints.geojson").to_crs(epsg)
    own = gpd.read_file(w / "ownership.geojson").to_crs(epsg)
    pa = gpd.read_file(w / "public_access.geojson").to_crs(epsg) if (w / "public_access.geojson").exists() else None
    ends = gpd.read_file(w / "access_points.geojson").to_crs(epsg)
    mvum = gpd.read_file(w / "mvum_roads.geojson")
    legal = legal_routes(mvum, cfg.access.vehicle, days).to_crs(epsg).reset_index(drop=True)
    blocks = gpd.read_file(w / "timber_blocks.geojson").to_crs(epsg)
    with rasterio.open(w / "dem.tif") as s:
        dem = s.read(1).astype("float64"); tr = s.transform

    def elev_ft(pt):
        r, c = rasterio.transform.rowcol(tr, pt.x, pt.y)
        return float(dem[r, c]) * 3.28084

    name_col = next((c for c in legal.columns if c.lower() == "name"), None)
    id_col = next((c for c in legal.columns if c.lower() == "id"), None)

    def route_label(i):
        rid = str(legal.iloc[i][id_col]) if id_col else ""
        nm = str(legal.iloc[i][name_col]).title() if name_col and legal.iloc[i][name_col] else ""
        return f"FR {rid} {nm}".strip()

    out = {"waypoints": {}, "areas": {}, "blocks": {}}
    for _, p in wp.iterrows():
        g = p.geometry
        land = None
        if pa is not None:
            hit = pa[pa.contains(g)]
            if len(hit):
                land = str(hit.iloc[0].get("PropName", "CPW public access"))
        if land is None:
            hit = own[own.contains(g)]
            land = str(hit.iloc[0].get("agency", hit.iloc[0].get("ADMIN_AGENCY_CODE", "?"))) if len(hit) else "?"
        d_end = ends.distance(g)
        k = int(d_end.values.argmin())
        e = ends.iloc[k]
        d_rt = legal.distance(g)
        j = int(d_rt.values.argmin())
        out["waypoints"][p["name"].split()[0]] = {
            "name": p["name"], "type": p["wp_type"], "area": p["hunt_area"], "rank": int(p["area_rank"]),
            "lat": round(gpd.GeoSeries([g], crs=epsg).to_crs(4326).iloc[0].y, 5),
            "lon": round(gpd.GeoSeries([g], crs=epsg).to_crs(4326).iloc[0].x, 5),
            "elev_ft": int(p["elevation_ft"]), "land": land,
            "end": str(e["name"]), "end_mi": round(float(d_end.min()) / M_PER_MI, 1),
            "end_climb_ft": int(round(elev_ft(g) - elev_ft(e.geometry))),
            "route": route_label(j), "route_mi": round(float(d_rt.min()) / M_PER_MI, 1),
        }

    for area, grp in wp.groupby("hunt_area"):
        hull = grp.union_all().convex_hull.buffer(1000)
        msk = ~geometry_mask([hull], out_shape=dem.shape, transform=tr)
        rr, cc = np.nonzero(msk)
        xs, ys = rasterio.transform.xy(tr, rr, cc)
        z = dem[rr, cc]
        ok = np.isfinite(z)
        A = np.c_[np.asarray(xs)[ok], np.asarray(ys)[ok], np.ones(ok.sum())]
        bx, by, _ = np.linalg.lstsq(A, z[ok], rcond=None)[0]
        down = (math.degrees(math.atan2(-bx, -by)) + 360) % 360
        out["areas"][area] = {"rank": int(grp["area_rank"].iloc[0]), "drains": compass(down), "drains_deg": round(down),
                              "n": len(grp)}

    for _, b in blocks.iterrows():
        d_rt = legal.distance(b.geometry)
        j = int(d_rt.values.argmin())
        near = wp[wp.distance(b.geometry) <= M_PER_MI]
        out["blocks"][b["id"]] = {"route": route_label(j), "route_mi": round(float(d_rt.min()) / M_PER_MI, 1),
                                  "wps_1mi": sorted(n.split()[0] for n in near["name"])}
    Path(a.out).write_text(json.dumps(out, indent=1))
    print(json.dumps(out["areas"], indent=1))
    for k, v in out["waypoints"].items():
        print(k, v["land"], "| end:", v["end"], v["end_mi"], "mi", f"{v['end_climb_ft']:+d} ft", "| route:", v["route"], v["route_mi"], "mi")
    for k, v in out["blocks"].items():
        print(k, v["route"], v["route_mi"], v["wps_1mi"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
