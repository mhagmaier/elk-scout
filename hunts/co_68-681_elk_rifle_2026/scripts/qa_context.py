"""QA + guide context for an elkscout run (read-only on the run's artifacts).

Per waypoint: GMU, land status (manual ownership incl. CPW public-access
properties), nearest ACCESS (straight-line mi + vertical ft) for packout math.
Per ACCESS point: nearest OSM motorized way and nearest MVUM route with its
open dates for high-clearance vehicles and OHVs wider than 50 in.
Per hunt area: general downhill (drainage) direction from a plane fit to the DEM,
and the MVUM routes within 1 mi of its waypoints.

Usage (repo root): python3 qa_context.py --data data --out <json>
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
import rasterio.mask  # noqa: E402

from elkscout import endpoints  # noqa: E402
from elkscout.cache import Cache  # noqa: E402
from elkscout.grid import Grid  # noqa: E402
from elkscout.net import Net  # noqa: E402
from elkscout.paths import Workspace  # noqa: E402
from elkscout.sources.arcgis import query_layer_geojson  # noqa: E402

UTM = 32613
M_PER_MI = 1609.344
MVUM_FIELDS = (
    "id,name,mvum_symbol_name,seasonal,highclearancevehicle,highclearancevehicle_datesopen,"
    "other_ohv_gt50inches,other_ohv_gt50_datesopen,passengervehicle_datesopen,districtname"
)
COMPASS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def compass(deg: float) -> str:
    return COMPASS[int((deg % 360) / 22.5 + 0.5) % 16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ws = Workspace(Path(a.data))
    grid = Grid.load(ws.grid_json)
    bbox = grid.bbox4326()
    net = Net(Cache(ws.cache), offline=False)

    wp = gpd.read_file(ws.work / "waypoints.geojson").to_crs(UTM)
    gmu = gpd.read_file(ws.manual / "boundary.geojson").to_crs(UTM)[["GMUID", "geometry"]]
    own = gpd.read_file(ws.manual / "ownership.geojson").to_crs(UTM)[["agency", "public", "cpw_property", "geometry"]]
    osm = gpd.read_file(ws.manual / "osm_motorized.geojson").to_crs(UTM)
    areas = gpd.read_file(ws.work / "hunt_areas.geojson").to_crs(UTM)

    mv = []
    for layer, kind in ((1, "road"), (2, "trail")):
        g = query_layer_geojson(net, endpoints.MVUM, layer, source="mvum_roads", bbox4326=bbox, out_fields=MVUM_FIELDS)
        if len(g):
            g["kind"] = kind
            mv.append(g)
    import pandas as pd

    mvum = gpd.GeoDataFrame(pd.concat(mv, ignore_index=True), geometry="geometry", crs=4326).to_crs(UTM)

    j = gpd.sjoin(wp, gmu, how="left", predicate="within").drop(columns="index_right")
    j = gpd.sjoin(j, own, how="left", predicate="within").drop(columns="index_right")
    j = j[~j.index.duplicated(keep="first")]

    access = j[j["wp_type"] == "ACCESS"]
    with rasterio.open(ws.work / "dem.tif") as dem_src:
        dem = dem_src.read(1).astype("float64")
        dem_tr, dem_crs, dem_nd = dem_src.transform, dem_src.crs, dem_src.nodata

    out: dict = {"waypoints": [], "access": [], "areas": []}
    for idx, r in j.iterrows():
        ev = r["evidence_json"] if isinstance(r["evidence_json"], dict) else json.loads(r["evidence_json"])
        rec = {
            "name": r["name"], "type": r["wp_type"], "area": r["hunt_area"], "rank": int(r["area_rank"]),
            "lat": round(ev["lat"], 5), "lon": round(ev["lon"], 5), "elev_ft": int(r["elevation_ft"]),
            "score": float(r["score"]), "gmu": int(r["GMUID"]) if not math.isnan(r["GMUID"]) else None,
            "land": r["agency"], "public": bool(r["public"]) if r["public"] is not None else None,
            "cpw_property": r["cpw_property"], "desc": r["desc"],
        }
        if r["wp_type"] != "ACCESS" and len(access):
            d = access.geometry.distance(r.geometry)
            k = d.idxmin()
            rec["nearest_access"] = access.loc[k, "name"]
            rec["access_mi"] = round(d[k] / M_PER_MI, 2)
            rec["access_dz_ft"] = int(r["elevation_ft"] - access.loc[k, "elevation_ft"])
        out["waypoints"].append(rec)

    for _, r in access.iterrows():
        rec = {"name": r["name"], "area": r["hunt_area"], "land": r["agency"], "cpw_property": r["cpw_property"]}
        d = osm.geometry.distance(r.geometry)
        k = d.idxmin()
        rec["osm"] = {k2: osm.loc[k, k2] for k2 in ("name", "highway", "ref") if k2 in osm.columns}
        rec["osm"]["dist_mi"] = round(d[k] / M_PER_MI, 2)
        d = mvum.geometry.distance(r.geometry)
        k = d.idxmin()
        mrow = mvum.loc[k]
        rec["mvum"] = {c: mrow[c] for c in ("kind", "id", "name", "mvum_symbol_name", "seasonal",
                                            "highclearancevehicle_datesopen", "other_ohv_gt50inches",
                                            "other_ohv_gt50_datesopen", "districtname")}
        rec["mvum"]["dist_mi"] = round(d[k] / M_PER_MI, 2)
        out["access"].append(rec)

    for _, ar in areas.iterrows():
        geom = ar.geometry
        masked, tr = rasterio.mask.mask(rasterio.open(ws.work / "dem.tif"), [gpd.GeoSeries([geom], crs=UTM).to_crs(dem_crs).iloc[0]], crop=True, filled=False)
        z = masked[0]
        rows, cols = np.nonzero(~np.ma.getmaskarray(z))
        xs, ys = rasterio.transform.xy(tr, rows, cols)
        zz = np.asarray(z[rows, cols], dtype="float64")
        A = np.c_[np.asarray(xs), np.asarray(ys), np.ones(len(zz))]
        (gx, gy, _), *_ = np.linalg.lstsq(A, zz, rcond=None)
        down_az = (math.degrees(math.atan2(-gx, -gy)) + 360) % 360
        sub = j[j["hunt_area"] == ar["name"]]
        hull = sub.geometry.union_all().buffer(M_PER_MI)
        near = mvum[mvum.intersects(hull)]
        out["areas"].append({
            "name": ar["name"], "rank": int(ar["rank"]), "n": int(ar["n_waypoints"]),
            "mean_score": float(ar["mean_score"]),
            "gmus": sorted({int(g) for g in sub["GMUID"].dropna()}),
            "elev_range_ft": [int(zz.min() * 3.28084), int(zz.max() * 3.28084)],
            "drains_toward": compass(down_az), "drains_toward_deg": round(down_az),
            "mvum_within_1mi": [
                {c: m[c] for c in ("kind", "id", "name", "seasonal", "highclearancevehicle_datesopen",
                                   "other_ohv_gt50inches", "other_ohv_gt50_datesopen")}
                for _, m in near.drop_duplicates(subset=["id"]).iterrows()
            ][:25],
        })

    Path(a.out).write_text(json.dumps(out, indent=1, default=str))
    print(f"wrote {a.out}: {len(out['waypoints'])} waypoints, {len(out['access'])} access, {len(out['areas'])} areas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
