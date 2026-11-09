"""Timber-cover analysis on an elkscout run's own rasters.

- How much of the public ground inside the units is timber (pipeline definition:
  canopy >= 50% or NLCD 41/42/43), and how much is dark conifer (NLCD 42/43 with
  canopy >= --dark-canopy).
- Security timber blocks: contiguous dark conifer on public land at least
  --min-road-mi from any motorized route, >= --min-acres. Per block: acres,
  centroid, elevation, north-facing share, median road distance, hunt area.
- Each waypoint: canopy, landcover, timber flag, distance to nearest block.

Usage (repo root): python3 timber_cover.py --data data --out <json> [--kml <path>]
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

import geopandas as gpd  # noqa: E402
import numpy as np  # noqa: E402
import rasterio  # noqa: E402
import rasterio.features  # noqa: E402
from scipy import ndimage  # noqa: E402
from shapely.geometry import shape  # noqa: E402

M_PER_MI = 1609.344
ACRE_M2 = 4046.8564
NLCD_NAMES = {41: "deciduous (aspen)", 42: "evergreen conifer", 43: "mixed forest", 52: "shrub", 71: "grass", 90: "woody wetland", 95: "herb wetland"}


def band(src, name):
    return src.read(list(src.descriptions).index(name) + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", required=True)
    ap.add_argument("--kml", default=None)
    ap.add_argument("--dark-canopy", type=int, default=60)
    ap.add_argument("--min-road-mi", type=float, default=0.5)
    ap.add_argument("--min-acres", type=float, default=100)
    a = ap.parse_args()
    w = Path(a.data) / "work"

    with rasterio.open(w / "factors.tif") as f:
        tr, crs = f.transform, f.crs
        timber = band(f, "timber") > 0.5
        dmot = band(f, "dist_motorized_m")
        public = band(f, "public") > 0.5
        unit = band(f, "unit") > 0.5
    with rasterio.open(w / "landcover.tif") as s:
        lc = s.read(1)
    with rasterio.open(w / "canopy.tif") as s:
        can = s.read(1)
    with rasterio.open(w / "terrain.tif") as s:
        asp = band(s, "aspect_deg")
    with rasterio.open(w / "dem.tif") as s:
        dem_ft = s.read(1).astype("float64") * 3.28084

    pub = unit & public
    can_ok = can != 255
    dark = np.isin(lc, (42, 43)) & can_ok & (can >= a.dark_canopy)
    cell_ac = abs(tr.a * tr.e) / ACRE_M2

    conifer_can = can[np.isin(lc, (42, 43)) & can_ok & pub]
    stats = {
        "public_acres": round(float(pub.sum() * cell_ac)),
        "timber_share_public": round(float((timber & pub).sum() / pub.sum()), 3),
        "dark_conifer_share_public": round(float((dark & pub).sum() / pub.sum()), 3),
        "aspen_share_public": round(float((np.isin(lc, (41,)) & pub).sum() / pub.sum()), 3),
        "conifer_canopy_pct_quartiles": [int(np.percentile(conifer_can, q)) for q in (25, 50, 75)] if conifer_can.size else None,
    }

    secure = dark & pub & (dmot >= a.min_road_mi * M_PER_MI)
    lab, n = ndimage.label(secure, structure=np.ones((3, 3), bool))
    sizes = ndimage.sum(np.ones_like(lab), lab, index=np.arange(1, n + 1))
    keep_ids = [i + 1 for i, s in enumerate(sizes) if s * cell_ac >= a.min_acres]

    areas = gpd.read_file(w / "hunt_areas.geojson").to_crs(crs)
    wp = gpd.read_file(w / "waypoints.geojson").to_crs(crs)
    feed = wp[wp["wp_type"] == "FEED"]

    blocks = []
    for bid in keep_ids:
        m = lab == bid
        polys = [shape(g) for g, v in rasterio.features.shapes(m.astype("uint8"), mask=m, transform=tr) if v == 1]
        geom = gpd.GeoSeries(polys, crs=crs).union_all()
        rr, cc = np.nonzero(m)
        aa = asp[rr, cc]
        north = float(np.mean((aa >= 315) | (aa < 45)))
        mean_az = (math.degrees(math.atan2(np.nanmean(np.sin(np.radians(aa))), np.nanmean(np.cos(np.radians(aa))))) + 360) % 360
        c = geom.representative_point()
        ll = gpd.GeoSeries([c], crs=crs).to_crs(4326).iloc[0]
        hit = areas[areas.intersects(geom)]
        near_feed = feed.distance(geom)
        blocks.append({
            "acres": round(float(m.sum() * cell_ac)),
            "lat": round(ll.y, 5), "lon": round(ll.x, 5),
            "elev_ft": [int(np.percentile(dem_ft[rr, cc], 10)), int(np.percentile(dem_ft[rr, cc], 90))],
            "north_share": round(north, 2), "mean_aspect_deg": round(mean_az),
            "median_canopy": int(np.median(can[rr, cc])),
            "road_mi_median": round(float(np.median(dmot[rr, cc])) / M_PER_MI, 2),
            "road_mi_max": round(float(dmot[rr, cc].max()) / M_PER_MI, 2),
            "hunt_areas": sorted(hit["name"].tolist()),
            "nearest_feed": feed.loc[near_feed.idxmin(), "name"] if len(feed) else None,
            "nearest_feed_mi": round(float(near_feed.min()) / M_PER_MI, 2) if len(feed) else None,
            "_geom": geom,
        })
    blocks.sort(key=lambda b: -b["acres"])

    bgeo = gpd.GeoSeries([b["_geom"] for b in blocks], crs=crs) if blocks else None
    pts = []
    rows, cols = rasterio.transform.rowcol(tr, wp.geometry.x.values, wp.geometry.y.values)
    for (_, r), ri, ci in zip(wp.iterrows(), rows, cols):
        cval = int(can[ri, ci])
        rec = {
            "name": r["name"], "type": r["wp_type"], "area": r["hunt_area"],
            "canopy": None if cval == 255 else cval,
            "landcover": NLCD_NAMES.get(int(lc[ri, ci]), int(lc[ri, ci])),
            "timber": bool(timber[ri, ci]), "dark": bool(dark[ri, ci]),
        }
        if bgeo is not None:
            d = bgeo.distance(r.geometry)
            k = int(d.idxmin())
            rec["nearest_block"] = k + 1
            rec["block_mi"] = round(float(d.min()) / M_PER_MI, 2)
        pts.append(rec)

    out = {"params": vars(a), "stats": stats, "n_blocks": len(blocks),
           "blocks": [{k: v for k, v in b.items() if k != "_geom"} | {"id": i + 1} for i, b in enumerate(blocks)],
           "waypoints": pts}
    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(json.dumps(stats))
    print(f"{len(blocks)} security timber blocks >= {a.min_acres} ac, >= {a.min_road_mi} mi from motorized routes")

    if a.kml and blocks:
        g = gpd.GeoDataFrame(
            [{"Name": f"T{i + 1:02d} timber {b['acres']} ac", "Description":
              f"Dark conifer (NLCD evergreen/mixed, canopy >= {a.dark_canopy}%, median {b['median_canopy']}%), "
              f"{b['acres']} ac public, {b['elev_ft'][0]:,}-{b['elev_ft'][1]:,} ft, "
              f"{int(b['north_share'] * 100)}% north-facing; median {b['road_mi_median']} mi "
              f"(max {b['road_mi_max']} mi) from the nearest motorized route. Nearest FEED: "
              f"{b['nearest_feed']} ({b['nearest_feed_mi']} mi).",
              "geometry": b["_geom"].simplify(15)} for i, b in enumerate(blocks)], crs=crs).to_crs(4326)
        Path(a.kml).unlink(missing_ok=True)
        g.to_file(a.kml, driver="KML", layer="Security timber")
        print(f"wrote {a.kml}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
