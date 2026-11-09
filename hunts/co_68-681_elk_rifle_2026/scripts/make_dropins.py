"""Build elkscout manual drop-ins for data the default fetch can't get right here.

Uses the pipeline's OWN request + conversion code, only overriding:
  - landcover / canopy: the coverage id (the auto-picker selects a change-count
    product and a Hawaii canopy layer against MRLC's current catalog)
  - osm_*: the Overpass endpoint (overpass-api.de and the kumi mirror drop
    connections from this sandbox; the VK Maps Overpass mirror answers)

Usage (from the repo root):
  python3 make_dropins.py landcover   --data data
  python3 make_dropins.py osm         --data data --overpass URL
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd() / "src"))

from elkscout import endpoints  # noqa: E402
from elkscout.cache import Cache  # noqa: E402
from elkscout.grid import Grid, write_raster  # noqa: E402
from elkscout.net import Net  # noqa: E402
from elkscout.paths import Workspace  # noqa: E402

LANDCOVER_ID = "mrlc_download:NLCD_2021_Land_Cover_L48"
CANOPY_ID = "mrlc_download:nlcd_tcc_conus_2021_v2021-4"


def do_landcover(ws: Workspace, net: Net) -> None:
    import numpy as np

    from elkscout.sources.landcover import _get_coverage

    grid = Grid.load(ws.grid_json)
    ws.manual.mkdir(parents=True, exist_ok=True)
    for key, cov, band in (("landcover", LANDCOVER_ID, "landcover"), ("canopy", CANOPY_ID, "canopy")):
        arr = _get_coverage(net, cov, grid)
        u8 = np.where(np.isfinite(arr), arr, 255).astype("uint8")
        out = ws.manual_path(key)
        write_raster(out, grid, {band: u8}, nodata=255, dtype="uint8")
        vals, counts = np.unique(u8, return_counts=True)
        top = sorted(zip(counts, vals), reverse=True)[:8]
        print(f"{key}: {cov} -> {out}  top values: {[(int(v), int(c)) for c, v in top]}")


def do_osm(ws: Workspace, net: Net, overpass: str) -> None:
    from elkscout.sources import boundary, osm

    endpoints.OVERPASS = [overpass]
    grid = Grid.load(ws.grid_json)
    bbox = grid.bbox4326()
    _ = boundary.load_boundary(ws)
    osm.fetch_osm(net, ws, bbox)
    ws.manual.mkdir(parents=True, exist_ok=True)
    pairs = {
        "osm_motorized": ws.motorized_geojson,
        "osm_trails": ws.trails_geojson,
        "osm_trailheads": ws.trailheads_geojson,
        "osm_springs": ws.springs_geojson,
    }
    for key, src in pairs.items():
        dst = ws.manual_path(key)
        shutil.copyfile(src, dst)
        print(f"{key}: {src} -> {dst}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["landcover", "osm"])
    ap.add_argument("--data", default="data")
    ap.add_argument("--overpass", default=None)
    a = ap.parse_args()
    ws = Workspace(Path(a.data))
    net = Net(Cache(ws.cache), offline=False)
    if a.what == "landcover":
        do_landcover(ws, net)
    else:
        if not a.overpass:
            ap.error("--overpass URL required for osm")
        do_osm(ws, net, a.overpass)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
