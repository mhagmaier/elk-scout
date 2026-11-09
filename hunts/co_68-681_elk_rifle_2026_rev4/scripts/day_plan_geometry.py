"""Terrain and wind geometry behind the guide's day plan (read-only on data/work).

For each hunt day's targets: the local downhill direction (a plane fit to the
DEM over the block, or within 400 m of a point), how that day's forecast wind
sits against the slope (0 deg = blowing uphill with the rising air, +-180 =
blowing downhill against it), and where the nearest legal road end lies.

Then the specific numbers the plan's approach notes quote: feed-slope
directions; bearings, distances and climbs between points; which side of each
block its nearest legal road runs on, and at what elevation; the meadow above
B2-03; T22's layout along its slope; and every instance of the named road ends.

Usage (repo root):
  python3 day_plan_geometry.py --data data --config <profile.yaml> [--context <guide_context.json>]
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
from shapely.geometry import Point  # noqa: E402
from shapely.ops import nearest_points  # noqa: E402

from elkscout.access import legal_routes  # noqa: E402
from elkscout.config import load_config  # noqa: E402

M_PER_MI = 1609.344
C16 = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]

# The guide's day plan (section 9): what each hunt day goes after, in order.
TARGETS = [["B1-01", "B1-02", "T05"], ["B2-02", "B2-03", "T12"], ["T22", "F4-01"], ["T04"], ["B2-06", "T17"]]
FEED = ["F1-01", "F2-01", "F3-02", "F4-01", "F4-02"]
PAIRS = [("F1-01", "T05"), ("F1-01", "B1-01"), ("B1-02", "B1-01"), ("A1-01", "B1-02"), ("A1-01", "B1-01"),
         ("F1-01", "A1-01"), ("F4-01", "T22"), ("F2-01", "T12"), ("F2-01", "B2-02"), ("B2-05", "B2-02"),
         ("B2-03", "B2-02")]
ROUTE_BLOCKS = ["T04", "T05", "T12", "T22"]
ROAD_ENDS = ["FR 856.1A Bull Bear road end", "FR 870 Middle Cr road end", "FR 873 Kelly road end",
             "FR 888 Greenback road end", "FR 709 Antelope road end", "FR 690.2A Storm King Cg road end"]
CONTEXT_CODES = ["A1-01", "B1-01", "B1-02", "F1-01", "B2-02", "B2-03", "B2-06", "F2-01", "F4-01"]


def compass(deg: float) -> str:
    return C16[int((deg % 360) / 22.5 + 0.5) % 16]


def bearing(a: Point, b: Point) -> float:
    return (math.degrees(math.atan2(b.x - a.x, b.y - a.y)) + 360) % 360


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    ap.add_argument("--config", required=True)
    ap.add_argument("--context", default=None, help="guide_context.json, for the road-end lookups at the end")
    a = ap.parse_args()
    w = Path(a.data) / "work"
    cfg = load_config(a.config)
    epsg = cfg.grid.epsg
    days = [cfg.hunt_window.start + dt.timedelta(days=i) for i in range((cfg.hunt_window.end - cfg.hunt_window.start).days + 1)]

    wp = gpd.read_file(w / "waypoints.geojson").to_crs(epsg)
    bl = gpd.read_file(w / "timber_blocks.geojson").to_crs(epsg)
    ends = gpd.read_file(w / "access_points.geojson").to_crs(epsg)
    legal = legal_routes(gpd.read_file(w / "mvum_roads.geojson"), cfg.access.vehicle, days).to_crs(epsg).reset_index(drop=True)
    daily = json.loads((w / "weather.json").read_text())["points"][0]["daily"]
    wind_from = dict(zip(daily["time"], daily["wind_direction_10m_dominant"]))
    with rasterio.open(w / "dem.tif") as s:
        dem = s.read(1).astype("float64")
        tr = s.transform

    def z_ft(p: Point) -> float:
        return float(dem[rasterio.transform.rowcol(tr, p.x, p.y)]) * 3.28084

    def downhill(geom) -> tuple[float, float]:
        """Downhill bearing (deg) and slope (%) of a plane fit to the DEM inside geom."""
        m = ~geometry_mask([geom], out_shape=dem.shape, transform=tr)
        r, c = np.nonzero(m)
        xs, ys = rasterio.transform.xy(tr, r, c)
        zz = dem[r, c]
        ok = np.isfinite(zz)
        A = np.c_[np.asarray(xs)[ok], np.asarray(ys)[ok], np.ones(ok.sum())]
        bx, by, _ = np.linalg.lstsq(A, zz[ok], rcond=None)[0]
        return (math.degrees(math.atan2(-bx, -by)) + 360) % 360, math.hypot(bx, by) * 100

    def point(code: str) -> Point:
        return wp.loc[wp["name"].str.split().str[0] == code].geometry.iloc[0]

    def block(bid: str):
        return bl.loc[bl["id"] == bid].geometry.iloc[0]

    def target(t: str):
        """(geometry to fit the slope over, reference point)."""
        if t.startswith("T"):
            g = block(t)
            return g, g.representative_point()
        p = point(t)
        return p.buffer(400), p

    id_col = next((c for c in legal.columns if c.lower() == "id"), None)
    name_col = next((c for c in legal.columns if c.lower() == "name"), None)

    def route_label(i: int) -> str:
        rid = str(legal.iloc[i][id_col]) if id_col else ""
        nm = str(legal.iloc[i][name_col]).title() if name_col and legal.iloc[i][name_col] else ""
        return f"FR {rid} {nm}".strip()

    print("== Each day's targets against that day's forecast wind")
    for day, ts in zip(days, TARGETS):
        frm = wind_from.get(str(day))
        if frm is None:
            print(f"\n{day:%a %b %-d}: no forecast in weather.json")
            continue
        to = (frm + 180) % 360
        print(f"\n{day:%a %b %-d}: wind from {compass(frm)} ({frm:.0f} deg), blowing toward {compass(to)}")
        for t in ts:
            geom, ref = target(t)
            dh, slope = downhill(geom)
            up = (dh + 180) % 360
            rel = (to - up + 540) % 360 - 180
            k = int(ends.distance(ref).values.argmin())
            e = ends.iloc[k]
            print(f"  {t}: downhill {compass(dh)} ({dh:.0f}), slope {slope:.0f}%, uphill {compass(up)}; "
                  f"wind vs uphill {rel:+.0f} deg | nearest road end {e['name']} lies {compass(bearing(ref, e.geometry))} "
                  f"at {ref.distance(e.geometry) / M_PER_MI:.1f} mi")

    print("\n== Feed-slope directions (within 300 m)")
    for code in FEED:
        print(f"  {code}: downhill {compass(downhill(point(code).buffer(300))[0])}")

    print("\n== Bearings, distances and climbs (to a block's nearest point)")
    for src, dst in PAIRS:
        p = point(src)
        q = nearest_points(p, block(dst))[1] if dst.startswith("T") else point(dst)
        print(f"  {src} -> {dst}: {compass(bearing(p, q))}, {p.distance(q) / M_PER_MI:.2f} mi, {z_ft(q) - z_ft(p):+.0f} ft")

    print("\n== Nearest legal road to each block")
    for bid in ROUTE_BLOCKS:
        g = block(bid)
        d = legal.distance(g)
        j = int(d.values.argmin())
        p_rt, p_b = nearest_points(legal.geometry.iloc[j], g)
        print(f"  {bid}: {route_label(j)} at {d.min() / M_PER_MI:.1f} mi, on the block's {compass(bearing(p_b, p_rt))} side; "
              f"block downhill {compass(downhill(g)[0])}; road {z_ft(p_rt):,.0f} ft vs block edge {z_ft(p_b):,.0f} ft")

    print("\n== The meadow southwest of B2-03")
    b3 = point("B2-03")
    for d_m in (100, 200, 300):
        q = Point(b3.x + d_m * math.sin(math.radians(225)), b3.y + d_m * math.cos(math.radians(225)))
        print(f"  {d_m} m SW of B2-03: {z_ft(q):,.0f} ft ({z_ft(q) - z_ft(b3):+.0f} ft vs the bed at {z_ft(b3):,.0f} ft)")

    print("\n== T22 along its slope")
    t22 = block("T22")
    dh, _ = downhill(t22)
    ax = math.radians(dh + 90)
    part = max(getattr(t22, "geoms", [t22]), key=lambda g: g.area)
    xy = np.asarray(part.exterior.coords)
    c = t22.centroid
    proj = (xy[:, 0] - c.x) * math.sin(ax) + (xy[:, 1] - c.y) * math.cos(ax)
    e1, e2 = Point(xy[proj.argmax()]), Point(xy[proj.argmin()])
    print(f"  {t22.area / 4046.86:.0f} ac, downhill {compass(dh)}; along-slope length {(proj.max() - proj.min()) / M_PER_MI:.2f} mi; "
          f"{compass(dh + 90)} end {z_ft(e1):,.0f} ft, {compass(dh - 90)} end {z_ft(e2):,.0f} ft, centroid {z_ft(c):,.0f} ft")
    f41 = point("F4-01")
    print(f"  F4-01 -> T22 centroid: {compass(bearing(f41, c))}, {f41.distance(c) / M_PER_MI:.2f} mi")

    print("\n== Named road ends (every instance) and the nearest waypoint")
    for nm in ROAD_ENDS:
        for e in ends.loc[ends["name"] == nm].geometry:
            dist = wp.distance(e)
            k = int(dist.values.argmin())
            code = wp.iloc[k]["name"].split()[0]
            print(f"  {nm}: {z_ft(e):,.0f} ft; nearest waypoint {code} lies {compass(bearing(e, wp.geometry.iloc[k]))} "
                  f"at {dist.min() / M_PER_MI:.2f} mi")

    if a.context:
        ctx = json.loads(Path(a.context).read_text())["waypoints"]
        print("\n== Guide context: nearest legal road end and route")
        for code in CONTEXT_CODES:
            v = ctx[code]
            print(f"  {code}: {v['end']} {v['end_mi']} mi, {v['end_climb_ft']:+d} ft | {v['route']} {v['route_mi']} mi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
