"""ElkScout command line.

    elkscout run       --config configs/unit33_oct_rifle.yaml [--offline] [--data DIR]
    elkscout fetch     --config ... [--only dem,osm] [--aoi-bbox minlon,minlat,maxlon,maxlat]
    elkscout score     --config ...        # terrain + factors + scoring
    elkscout waypoints --config ...
    elkscout report    --config ...        # GPX + KML + map + briefing
    elkscout doctor    [--data DIR]        # endpoint reachability + cache state
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from . import __version__, endpoints
from .cache import Cache
from .config import Config, load_config
from .grid import Grid
from .net import Net
from .paths import Workspace

log = logging.getLogger("elkscout")

FETCH_STEPS = ["boundary", "dem", "osm", "mvum", "water", "ownership", "burns", "landcover", "snow", "weather"]


def _setup_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def _ws(args) -> Workspace:
    ws = Workspace(Path(args.data))
    ws.ensure_dirs()
    return ws


def _net(ws: Workspace, offline: bool) -> Net:
    return Net(Cache(ws.cache), offline=offline)


def _parse_bbox(s: str) -> tuple[float, float, float, float]:
    parts = [float(p) for p in s.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("expected minlon,minlat,maxlon,maxlat")
    minlon, minlat, maxlon, maxlat = parts
    if not (minlon < maxlon and minlat < maxlat):
        raise argparse.ArgumentTypeError("bbox must be minlon,minlat,maxlon,maxlat with min < max")
    return (minlon, minlat, maxlon, maxlat)


# -- stages -----------------------------------------------------------------

def stage_fetch(ws: Workspace, cfg: Config, net: Net, only: list[str] | None, aoi_bbox=None) -> None:
    from .sources import boundary, burns, dem, landcover, mvum, osm, ownership, snotel, water, weather

    steps = only or FETCH_STEPS

    if "boundary" in steps:
        if aoi_bbox is not None:
            bnd = boundary.synth_boundary_from_bbox(ws, aoi_bbox)
            log.info("boundary: synthetic AOI bbox %s", aoi_bbox)
        else:
            bnd = boundary.fetch_boundary(net, ws, cfg)
            log.info("boundary: unit %s fetched (%d parts)", cfg.unit, len(bnd))
    else:
        if not ws.boundary_geojson.exists():
            raise SystemExit(
                f"{ws.boundary_geojson} missing - run `elkscout fetch --only boundary` "
                "(or a full fetch) first"
            )
        bnd = boundary.load_boundary(ws)

    grid = Grid.from_boundary(bnd, cfg.grid)
    grid.save(ws.grid_json)
    log.info("grid: %dx%d cells at %.0f m (EPSG:%d)", grid.width, grid.height, grid.res, grid.epsg)
    bbox = grid.bbox4326()

    if "dem" in steps:
        dem.fetch_dem(net, ws, grid)
    if "osm" in steps:
        osm.fetch_osm(net, ws, bbox)
    if "mvum" in steps:
        mvum.fetch_mvum(net, ws, bbox)
    if "water" in steps:
        water.fetch_water(net, ws, bbox)
    if "ownership" in steps:
        ownership.fetch_ownership(net, ws, bbox, cfg.land_access)
    if "burns" in steps:
        burns.fetch_burns(net, ws, bbox, cfg.hunt_window.start.year)
    if "landcover" in steps:
        landcover.fetch_landcover(net, ws, grid)
    if "snow" in steps:
        snotel.fetch_snow(net, ws, bbox, cfg)
    if "weather" in steps:
        c = bnd.to_crs(epsg=cfg.grid.epsg).geometry.union_all().centroid
        lon, lat = grid.xy_to_lonlat(c.x, c.y)
        weather.fetch_weather(net, ws, [(float(lon), float(lat))], cfg)


def stage_score(ws: Workspace, cfg: Config) -> None:
    from . import access, factors, scoring, terrain

    terrain.run_terrain(ws)
    log.info("terrain derivatives written")
    factors.run_factors(ws, cfg)
    log.info("factor measurement rasters written")
    access.build_access_points(ws, cfg)
    scoring.run_scoring(ws, cfg)
    log.info("suitability scores written")


def stage_waypoints(ws: Workspace, cfg: Config) -> None:
    from . import waypoints

    waypoints.run_waypoints(ws, cfg)
    log.info("waypoints + hunt areas written")


def stage_report(ws: Workspace, cfg: Config) -> None:
    from .outputs import briefing, gpx_writer, html_map, kml_writer

    paths = gpx_writer.write_gpx_files(ws, cfg)
    log.info("GPX written: %s", ", ".join(str(p) for p in paths))
    log.info("KML written: %s", kml_writer.write_kml(ws, cfg))
    log.info("map written: %s", html_map.write_map(ws, cfg))
    log.info("briefing written: %s", briefing.write_briefing(ws, cfg))


def cmd_doctor(args) -> int:
    ws = _ws(args)
    net = _net(ws, offline=False)
    probes = list(endpoints.DOCTOR_PROBES)
    if getattr(args, "config", None):
        from .sources.boundary import resolve_boundary_source

        cfg = load_config(args.config)
        src = resolve_boundary_source(cfg)
        for i, url in enumerate((src.base_url, *src.alt_urls)):
            probes.insert(i, (f"Unit {cfg.unit} boundary", url, {"f": "json"}))
    print(f"elkscout {__version__} doctor\n")
    print("endpoint reachability:")
    ok = 0
    for name, url, params in probes:
        try:
            net.session.get(url, params=params, timeout=15).raise_for_status()
            status = "OK"
            ok += 1
        except Exception as e:  # noqa: BLE001 - report any failure mode
            status = f"FAIL ({type(e).__name__})"
        print(f"  {name:<20} {status}")
    print(f"\n{ok}/{len(probes)} endpoints reachable.")
    if ok == 0:
        print("No endpoints reachable — run `elkscout fetch` on a networked machine, or provide")
        print(f"manual drop-ins under {ws.manual}/ (see README).")
    print("\ncache state:")
    total = 0
    for sub in sorted(ws.cache.glob("*")):
        if sub.is_dir():
            n = sum(1 for f in sub.iterdir() if f.suffix != ".jsonl")
            total += n
            print(f"  {sub.name:<16} {n} objects")
    if total == 0:
        print("  (empty)")
    print("\nmanual drop-ins present:")
    found = [k for k in ws.MANUAL_FILES if ws.manual_path(k).exists()]
    print("  " + (", ".join(found) if found else "(none)"))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="elkscout", description=__doc__)
    ap.add_argument("--version", action="version", version=f"elkscout {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def common(p, config_required=True):
        p.add_argument("--config", required=config_required, help="scoring profile YAML")
        p.add_argument("--data", default="data", help="workspace root (default: ./data)")
        p.add_argument("--offline", action="store_true", help="never touch the network")
        p.add_argument("-v", "--verbose", action="store_true")

    p_run = sub.add_parser("run", help="fetch + score + waypoints + report")
    common(p_run)
    p_run.add_argument("--aoi-bbox", type=_parse_bbox, default=None, help="test AOI override (minlon,minlat,maxlon,maxlat)")

    p_fetch = sub.add_parser("fetch", help="fetch all source data into the cache/workspace")
    common(p_fetch)
    p_fetch.add_argument("--only", default=None, help=f"comma list of {','.join(FETCH_STEPS)}")
    p_fetch.add_argument("--aoi-bbox", type=_parse_bbox, default=None)

    for name, help_ in (("score", "terrain + factors + suitability scoring"),
                        ("waypoints", "extract typed waypoints + hunt areas"),
                        ("report", "GPX + KML + interactive map + briefing")):
        p = sub.add_parser(name, help=help_)
        common(p)

    p_doc = sub.add_parser("doctor", help="probe endpoints and show cache state")
    p_doc.add_argument("--config", default=None, help="also probe this profile's boundary service")
    p_doc.add_argument("--data", default="data")
    p_doc.add_argument("-v", "--verbose", action="store_true")

    args = ap.parse_args(argv)
    _setup_logging(getattr(args, "verbose", False))

    if args.cmd == "doctor":
        return cmd_doctor(args)

    ws = _ws(args)
    cfg = load_config(args.config)

    if args.cmd == "fetch":
        only = [s.strip() for s in args.only.split(",")] if args.only else None
        if only:
            unknown = [s for s in only if s not in FETCH_STEPS]
            if unknown:
                ap.error(f"--only: unknown step(s) {', '.join(unknown)}; valid: {','.join(FETCH_STEPS)}")
        stage_fetch(ws, cfg, _net(ws, args.offline), only, aoi_bbox=args.aoi_bbox)
    elif args.cmd == "score":
        stage_score(ws, cfg)
    elif args.cmd == "waypoints":
        stage_waypoints(ws, cfg)
    elif args.cmd == "report":
        stage_report(ws, cfg)
    elif args.cmd == "run":
        stage_fetch(ws, cfg, _net(ws, args.offline), None, aoi_bbox=args.aoi_bbox)
        stage_score(ws, cfg)
        stage_waypoints(ws, cfg)
        stage_report(ws, cfg)
        print(f"\nDone. Outputs in {ws.out}/ — import the .gpx into OnX (web map: My Content > Import).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
