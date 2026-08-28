"""Wildfire burn perimeters (MTBS) -> work/burns.geojson (EPSG:4326).

Contract — fetch_burns(net, ws, bbox4326, hunt_year):
1. ws.manual_path("burns") if present.
2. endpoints.MTBS layer MTBS_LAYER (63, all-years perimeters). Query bbox with
   max_allowable_offset 0.0003. Field names vary by vintage; discovered
   case-insensitively:
   - year: first existing of FIRE_YEAR / Fire_Year / YEAR / Ig_Date-derived
     (Ig_Date may be epoch-ms or 'YYYY-MM-DD' — both handled).
   - name: first existing of FIRE_NAME / Fire_Name / INCIDENT / Event_ID.
3. Filter to hunt_year - 22 <= year <= hunt_year - 1 (the burn-age curve spans
   2-20 yr; fetched a little wide, scoring clips).
4. Normalize to columns: `year` (int), `fire_name` (str, title-cased).
5. Write ws.burns_geojson. Empty is allowed (no burns near AOI).
Offline miss -> OfflineMissError("burns", ws).
"""

from __future__ import annotations

import datetime as _dt
import logging

import geopandas as gpd
import pandas as pd

from .. import endpoints
from ..net import Net, OfflineError
from ..paths import OfflineMissError, Workspace
from .arcgis import query_layer_geojson

log = logging.getLogger("elkscout.burns")

SOURCE = "burns"

_OFFSET_DEG = 0.0003
# Case-insensitive discovery lists; the normalized `year`/`fire_name` names of
# a manual drop-in are matched by YEAR / FIRE_NAME respectively.
_YEAR_FIELDS = ("FIRE_YEAR", "Fire_Year", "YEAR")
_DATE_FIELDS = ("Ig_Date", "IG_DATE")
_NAME_FIELDS = ("FIRE_NAME", "Fire_Name", "INCIDENT", "Event_ID")


def fetch_burns(net: Net, ws: Workspace, bbox4326: tuple[float, float, float, float], hunt_year: int) -> None:
    manual = ws.manual_path(SOURCE)
    if manual.exists():
        log.info("burns: using manual drop-in %s", manual)
        gdf = gpd.read_file(manual)
        gdf = gdf.set_crs("EPSG:4326") if gdf.crs is None else gdf.to_crs("EPSG:4326")
    else:
        try:
            gdf = query_layer_geojson(
                net,
                endpoints.MTBS,
                endpoints.MTBS_LAYER,
                source=SOURCE,
                bbox4326=bbox4326,
                max_allowable_offset=_OFFSET_DEG,
            )
        except OfflineError as e:
            raise OfflineMissError(SOURCE, ws) from e
    gdf = _normalize(gdf, hunt_year)
    _write(ws, gdf)
    log.info("burns: %d perimeters in [%d, %d] -> %s", len(gdf), hunt_year - 22, hunt_year - 1, ws.burns_geojson)


# -- internals ---------------------------------------------------------------

def _normalize(gdf: gpd.GeoDataFrame, hunt_year: int) -> gpd.GeoDataFrame:
    if len(gdf) == 0:
        return gdf
    lower = {c.lower(): c for c in gdf.columns if c != gdf.geometry.name}

    year_col = next((lower[f.lower()] for f in _YEAR_FIELDS if f.lower() in lower), None)
    if year_col is None:
        year_col = next((lower[f.lower()] for f in _DATE_FIELDS if f.lower() in lower), None)
    if year_col is None:
        raise RuntimeError(
            f"burns: no year field ({'/'.join(_YEAR_FIELDS + _DATE_FIELDS)}) "
            f"among columns {list(gdf.columns)}"
        )
    years = gdf[year_col].map(_parse_year)

    name_col = next((lower[f.lower()] for f in _NAME_FIELDS if f.lower() in lower), None)
    if name_col is None:
        log.warning("burns: no name field among columns %s; using 'Unknown'", list(gdf.columns))
        names = pd.Series(["Unknown"] * len(gdf), index=gdf.index)
    else:
        names = gdf[name_col].map(lambda v: "Unknown" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).title())

    n_bad = int(years.isna().sum())
    if n_bad:
        log.warning("burns: dropping %d perimeter(s) with unparseable %s", n_bad, year_col)
    keep = years.notna() & (years >= hunt_year - 22) & (years <= hunt_year - 1)

    out = gpd.GeoDataFrame(
        {"year": years[keep].astype(int), "fire_name": names[keep]},
        geometry=gdf.geometry[keep],
        crs=gdf.crs,
    )
    return out.reset_index(drop=True)


def _parse_year(value) -> float:
    """Ignition year from a year number, epoch-ms date, or date string; NaN if unparseable."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")
    if isinstance(value, (int, float)):
        v = float(value)
        if 1200 <= v <= 2200:  # already a calendar year
            return float(int(v))
        try:
            return float(_dt.datetime.utcfromtimestamp(v / 1000).year)  # epoch-ms
        except (OverflowError, OSError, ValueError):
            return float("nan")
    s = str(value).strip()
    try:
        return float(int(s[:4]))  # 'YYYY-MM-DD...' or 'YYYY'
    except ValueError:
        return float("nan")


def _write(ws: Workspace, gdf: gpd.GeoDataFrame) -> None:
    path = ws.burns_geojson
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    if len(gdf) == 0:
        path.write_text('{"type": "FeatureCollection", "features": []}\n', encoding="utf-8")
        return
    gdf.to_file(path, driver="GeoJSON")
