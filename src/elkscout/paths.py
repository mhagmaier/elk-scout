"""Workspace layout: every on-disk artifact the pipeline reads or writes.

All inter-stage contracts are file paths defined here, so stages can run
standalone and tests can pre-seed any stage's inputs.

Conventions:
- Vector artifacts under work/ are GeoJSON in EPSG:4326.
- Raster artifacts under work/ are GeoTIFFs aligned to the scoring grid
  (EPSG:32611, 30 m) EXCEPT dem_raw.tif which is as-fetched.
- manual/ holds user-supplied drop-in files that satisfy a source without
  network access; each sources.* module checks its manual file first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        self.root = Path(self.root)

    # -- directories ------------------------------------------------------
    @property
    def cache(self) -> Path:
        return self.root / "cache"

    @property
    def manual(self) -> Path:
        return self.root / "manual"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @property
    def out(self) -> Path:
        return self.root / "out"

    @property
    def qa(self) -> Path:
        return self.out / "qa"

    def ensure_dirs(self) -> None:
        for d in (self.cache, self.manual, self.work, self.out, self.qa):
            d.mkdir(parents=True, exist_ok=True)

    # -- work artifacts (stage outputs) -----------------------------------
    @property
    def boundary_geojson(self) -> Path:  # unit polygon, EPSG:4326
        return self.work / "boundary.geojson"

    @property
    def grid_json(self) -> Path:  # Grid definition (transform/shape/crs)
        return self.work / "grid.json"

    @property
    def dem_tif(self) -> Path:  # float32 meters, on-grid
        return self.work / "dem.tif"

    @property
    def terrain_tif(self) -> Path:  # multiband float32 on-grid; band names in tags
        return self.work / "terrain.tif"

    @property
    def motorized_geojson(self) -> Path:  # OSM motorized ∪ MVUM roads, lines
        return self.work / "motorized.geojson"

    @property
    def trails_geojson(self) -> Path:  # non-motorized trails, lines
        return self.work / "trails.geojson"

    @property
    def trailheads_geojson(self) -> Path:  # points
        return self.work / "trailheads.geojson"

    @property
    def springs_geojson(self) -> Path:  # points
        return self.work / "springs.geojson"

    @property
    def water_lines_geojson(self) -> Path:  # perennial NHD flowlines
        return self.work / "water_lines.geojson"

    @property
    def water_bodies_geojson(self) -> Path:  # lakes/reservoirs polygons
        return self.work / "water_bodies.geojson"

    @property
    def huc12_geojson(self) -> Path:  # watershed polygons w/ name attr
        return self.work / "huc12.geojson"

    @property
    def ownership_geojson(self) -> Path:  # polygons w/ agency attr ("ADMIN")
        return self.work / "ownership.geojson"

    @property
    def public_access_geojson(self) -> Path:  # always-open overlays (walk-in, enrolled trust land)
        return self.work / "public_access.geojson"

    @property
    def access_points_geojson(self) -> Path:  # legal road ends for the hunter's vehicle
        return self.work / "access_points.geojson"

    @property
    def timber_blocks_geojson(self) -> Path:  # security timber polygons + stats
        return self.work / "timber_blocks.geojson"

    @property
    def timber_json(self) -> Path:  # timber summary stats
        return self.work / "timber.json"

    @property
    def sentinel_tif(self) -> Path:  # on-grid: snow_now, ndvi_now, dndvi
        return self.work / "sentinel.tif"

    @property
    def sentinel_json(self) -> Path:  # scene ids, dates, observed snow line
        return self.work / "sentinel.json"

    @property
    def burns_geojson(self) -> Path:  # MTBS perimeters w/ "year" + "fire_name"
        return self.work / "burns.geojson"

    @property
    def landcover_tif(self) -> Path:  # uint8 NLCD class codes, on-grid
        return self.work / "landcover.tif"

    @property
    def canopy_tif(self) -> Path:  # uint8 percent tree canopy, on-grid
        return self.work / "canopy.tif"

    @property
    def snow_json(self) -> Path:  # SNOTEL summary + derived elevation shift
        return self.work / "snow.json"

    @property
    def weather_json(self) -> Path:  # Open-Meteo summary (may be climatology note)
        return self.work / "weather.json"

    @property
    def factors_tif(self) -> Path:  # multiband float32 factor stack, on-grid
        return self.work / "factors.tif"

    @property
    def composite_tif(self) -> Path:  # overall habitat score, on-grid
        return self.work / "composite.tif"

    @property
    def type_scores_tif(self) -> Path:  # multiband per-waypoint-type composites
        return self.work / "type_scores.tif"

    @property
    def waypoints_geojson(self) -> Path:  # typed points w/ evidence, EPSG:4326
        return self.work / "waypoints.geojson"

    @property
    def hunt_areas_geojson(self) -> Path:  # named area polygons, EPSG:4326
        return self.work / "hunt_areas.geojson"

    # -- final outputs -----------------------------------------------------
    def gpx_all(self, unit: str) -> Path:
        return self.out / f"elkscout_unit{unit}_all.gpx"

    def gpx_area(self, unit: str, area_slug: str) -> Path:
        return self.out / f"elkscout_unit{unit}_{area_slug}.gpx"

    def kml(self, unit: str) -> Path:
        return self.out / f"elkscout_unit{unit}.kml"

    def timber_kml(self, unit: str) -> Path:
        return self.out / f"elkscout_unit{unit}_timber_blocks.kml"

    @property
    def imagery_dir(self) -> Path:  # photo chips + sheets for the eyeball check
        return self.out / "imagery"

    @property
    def imagery_review_json(self) -> Path:  # verdicts written after looking at the sheets
        return self.work / "imagery_review.json"

    @property
    def map_html(self) -> Path:
        return self.out / "map.html"

    @property
    def briefing_md(self) -> Path:
        return self.out / "briefing.md"

    # -- manual drop-ins (checked by sources before any network call) ------
    MANUAL_FILES: dict[str, str] = field(
        default_factory=lambda: dict(_MANUAL_FILES), repr=False
    )

    def manual_path(self, key: str) -> Path:
        """Path of the manual drop-in for a logical source key."""
        return self.manual / _MANUAL_FILES[key]


# Logical source key -> filename under data/manual/. Documented in README;
# error messages for --offline cache misses name these exact files.
_MANUAL_FILES: dict[str, str] = {
    "boundary": "boundary.geojson",
    "dem": "dem.tif",
    "osm_motorized": "osm_motorized.geojson",
    "osm_trails": "osm_trails.geojson",
    "osm_trailheads": "osm_trailheads.geojson",
    "osm_springs": "osm_springs.geojson",
    "mvum_roads": "mvum_roads.geojson",
    "water_lines": "water_lines.geojson",
    "water_bodies": "water_bodies.geojson",
    "huc12": "huc12.geojson",
    "ownership": "ownership.geojson",
    "public_access": "public_access.geojson",
    "burns": "burns.geojson",
    "landcover": "landcover.tif",
    "canopy": "canopy.tif",
    "snow": "snow.json",
    "weather": "weather.json",
}


class OfflineMissError(RuntimeError):
    """Raised when --offline is set and neither cache nor manual file satisfies a source."""

    def __init__(self, source_key: str, ws: Workspace, detail: str = ""):
        manual = ws.manual_path(source_key) if source_key in _MANUAL_FILES else None
        msg = f"offline mode: no cached or manual data for source '{source_key}'."
        if manual is not None:
            msg += f" Provide the file {manual} (see README 'Manual data drop-ins')."
        if detail:
            msg += f" {detail}"
        super().__init__(msg)
