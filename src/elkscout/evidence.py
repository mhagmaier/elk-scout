"""Per-waypoint evidence: sampled physical facts + a human-readable sentence.

build_evidence samples the rasters/vectors at one grid cell and returns a dict;
render_sentence turns it into the hunter-facing "why this point" text that ends
up in the GPX description and the briefing; short_tag yields the terse fragment
used inside waypoint names.

The `terrain` dict may carry an extra "canopy" band (percent, NaN where
unknown) injected by waypoints.py. `vectors` holds GeoDataFrames (possibly
empty) for: water_lines, burns, ownership, huc12.
"""

from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

MI_PER_M = 1.0 / 1609.344
FAR_M = 99_000.0  # >= this means "no such feature in the AOI"

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
_COMPASS_WORD = {
    "N": "North",
    "NE": "Northeast",
    "E": "East",
    "SE": "Southeast",
    "S": "South",
    "SW": "Southwest",
    "W": "West",
    "NW": "Northwest",
}

# TPI thresholds (meters) for the terse landform label.
_BENCH_TPI300 = 8.0
_KNOB_TPI1000 = 15.0
_VALLEY_TPI1000 = -15.0


def _compass(aspect_deg: float | None) -> str | None:
    if aspect_deg is None or (isinstance(aspect_deg, float) and math.isnan(aspect_deg)):
        return None
    return _COMPASS[int(((aspect_deg % 360) + 22.5) // 45) % 8]


def _sample(arr: np.ndarray | None, row: int, col: int) -> float | None:
    if arr is None:
        return None
    v = float(arr[row, col])
    return None if math.isnan(v) else v


def _tpi_class(wp_type: str, tpi300: float | None, tpi1000: float | None) -> str:
    if wp_type == "SADDLE":
        return "saddle"
    if wp_type == "GLASS":
        return "knob"
    t300 = tpi300 if tpi300 is not None else 0.0
    t1000 = tpi1000 if tpi1000 is not None else 0.0
    if t1000 <= _VALLEY_TPI1000:
        return "valley"
    if t1000 >= _KNOB_TPI1000 and t300 > 0:
        return "knob"
    if abs(t300) < _BENCH_TPI300 and t1000 > 0:
        return "bench"
    return "slope"


def _point_lookup(gdf: gpd.GeoDataFrame, pt4326: Point, column: str):
    if gdf is None or len(gdf) == 0 or column not in gdf.columns:
        return None
    hits = gdf[gdf.geometry.contains(pt4326)]
    if len(hits) == 0:
        return None
    return hits.iloc[0][column]


_DEG_TO_MI = 69.0  # approximate; fine for a consistency gate


def _nearest_water_name(water_lines: gpd.GeoDataFrame, pt4326: Point, dist_water_mi: float | None):
    """GNIS name of the nearest named flowline — only when it plausibly IS the
    water the sampled distance refers to (unnamed springs/creeks may be closer)."""
    if (
        water_lines is None
        or len(water_lines) == 0
        or "GNIS_NAME" not in water_lines.columns
        or dist_water_mi is None
    ):
        return None
    named = water_lines[water_lines["GNIS_NAME"].notna()]
    if len(named) == 0:
        return None
    dists = np.array([geom.distance(pt4326) for geom in named.geometry])
    i = int(np.argmin(dists))
    named_mi = float(dists[i]) * _DEG_TO_MI
    tolerance = max(0.05, 0.25 * dist_water_mi)
    return str(named.iloc[i]["GNIS_NAME"]) if abs(named_mi - dist_water_mi) <= tolerance else None


def _nearest_block(blocks_grid, x: float, y: float) -> dict:
    """Nearest security-timber block (projected grid CRS): id, acres, miles (0 = inside)."""
    if blocks_grid is None or len(blocks_grid) == 0:
        return {"timber_block": None, "timber_block_acres": None, "timber_block_mi": None}
    p = Point(x, y)
    d = blocks_grid.geometry.distance(p)
    i = d.idxmin()
    return {
        "timber_block": str(blocks_grid.loc[i, "id"]),
        "timber_block_acres": int(blocks_grid.loc[i, "acres"]),
        "timber_block_mi": round(float(d.loc[i]) * MI_PER_M, 2),
    }


DEAD_WINDOW_CELLS = 10  # ~300 m radius at 30 m


def _sentinel_evidence(terrain: dict, meta: dict, row: int, col: int) -> dict:
    """Near-live imagery facts at the point: snow on the ground now, nearby timber loss."""
    out = {"snow_now": None, "snow_date": None, "dead_share_300m": None, "leafon_baseline_year": None}
    snow = terrain.get("snow_now")
    if snow is not None:
        v = float(snow[row, col])
        out["snow_now"] = None if math.isnan(v) else bool(v >= 0.5)
        out["snow_date"] = meta.get("snow_date")
    dead = terrain.get("dead")
    if dead is not None:
        r0, r1 = max(0, row - DEAD_WINDOW_CELLS), min(dead.shape[0], row + DEAD_WINDOW_CELLS + 1)
        c0, c1 = max(0, col - DEAD_WINDOW_CELLS), min(dead.shape[1], col + DEAD_WINDOW_CELLS + 1)
        win = dead[r0:r1, c0:c1]
        win = win[np.isfinite(win)]
        if win.size:
            out["dead_share_300m"] = round(float(win.mean()), 2)
            out["leafon_baseline_year"] = meta.get("leafon_baseline_year")
    return out


def build_evidence(
    row: int,
    col: int,
    wp_type: str,
    grid,
    dem: np.ndarray,
    terrain: dict[str, np.ndarray],
    factors: dict[str, np.ndarray],
    vectors: dict[str, gpd.GeoDataFrame],
) -> dict:
    x, y = grid.xy(row, col)
    lon, lat = grid.xy_to_lonlat(float(x), float(y))
    pt = Point(float(lon), float(lat))

    elev_m = _sample(dem, row, col)
    aspect = _sample(terrain.get("aspect_deg"), row, col)
    dist_th = _sample(factors.get("dist_trailhead_m"), row, col)
    dist_mot = _sample(factors.get("dist_motorized_m"), row, col)
    dist_wat = _sample(factors.get("dist_water_m"), row, col)
    # FAR_M is the "no such feature in the AOI" sentinel — never quote it as a distance.
    dist_water_mi = round(dist_wat * MI_PER_M, 2) if dist_wat is not None and dist_wat < FAR_M else None
    burn_year = _point_lookup(vectors.get("burns"), pt, "year")
    burn_name = _point_lookup(vectors.get("burns"), pt, "fire_name")

    return {
        "elevation_ft": int(round(elev_m * 3.28084)) if elev_m is not None else None,
        "aspect_deg": round(aspect, 1) if aspect is not None else None,
        "aspect_compass": _compass(aspect),
        "slope_pct": int(round(_sample(terrain.get("slope_pct"), row, col) or 0)),
        "tpi_class": _tpi_class(wp_type, _sample(terrain.get("tpi300"), row, col), _sample(terrain.get("tpi1000"), row, col)),
        "canopy_pct": int(round(c)) if (c := _sample(terrain.get("canopy"), row, col)) is not None else None,
        "dist_motorized_mi": round(dist_mot * MI_PER_M, 1) if dist_mot is not None and dist_mot < FAR_M else None,
        "dist_trailhead_mi": round(dist_th * MI_PER_M, 1) if dist_th is not None and dist_th < FAR_M else None,
        "dist_water_mi": dist_water_mi,
        "burn_name": str(burn_name) if burn_name is not None else None,
        "burn_year": int(burn_year) if burn_year is not None else None,
        "nearest_water_name": _nearest_water_name(vectors.get("water_lines"), pt, dist_water_mi),
        "agency": _point_lookup(vectors.get("ownership"), pt, "agency"),
        "huc12_name": _point_lookup(vectors.get("huc12"), pt, "name"),
        **_nearest_block(vectors.get("timber_blocks_grid"), float(x), float(y)),
        **_sentinel_evidence(terrain, vectors.get("sentinel_meta") or {}, row, col),
        "lon": round(float(lon), 6),
        "lat": round(float(lat), 6),
    }


# {Aspect} starts a sentence ("North-facing bench"); {aspect} sits mid-sentence
# ("Feed on an east-facing slope"), so it is lowercase and takes its article {a}.
_LEAD = {
    "BED": "{Aspect}-facing {landform} at {elev} ft",
    "FEED": "Feed on {a} {aspect}-facing {landform} at {elev} ft",
    "WATER": "Water hole at {elev} ft",
    "SADDLE": "Travel saddle at {elev} ft",
    "GLASS": "Glassing knob at {elev} ft",
    "CAMP": "Camp spot at {elev} ft",
    "ACCESS": "Access point at {elev} ft",
}


def _article(word: str) -> str:
    return "an" if word[:1].lower() in "aeiou" else "a"


def render_sentence(ev: dict, wp_type: str) -> str:
    aspect_word = _COMPASS_WORD.get(ev.get("aspect_compass") or "", None)
    elev = f"{ev['elevation_ft']:,}" if ev.get("elevation_ft") is not None else "?"
    lead_tpl = _LEAD.get(wp_type, "{elev} ft point")
    needs_aspect = "{aspect}" in lead_tpl or "{Aspect}" in lead_tpl
    if needs_aspect and aspect_word is None:
        lead = f"{ev.get('tpi_class', 'point').capitalize()} at {elev} ft"
        if wp_type == "FEED":
            landform = ev.get("tpi_class", "flat")
            lead = f"Feed on {_article(landform)} {landform} at {elev} ft"
    else:
        lead = lead_tpl.format(Aspect=aspect_word, aspect=(aspect_word or "").lower(), a=_article(aspect_word or ""),
                               landform=ev.get("tpi_class", "slope"), elev=elev)

    clauses: list[str] = []
    if ev.get("canopy_pct") is not None:
        clauses.append(f"{ev['canopy_pct']}% canopy")
    if ev.get("slope_pct"):
        clauses.append(f"{ev['slope_pct']}% slope")
    body = (", " + ", ".join(clauses)) if clauses else ""

    tail: list[str] = []
    if ev.get("dist_motorized_mi") is not None:
        tail.append(f"{ev['dist_motorized_mi']:.1f} mi from the nearest motorized route")
    water_name = ev.get("nearest_water_name")
    if ev.get("dist_water_mi") is not None:
        target = water_name if water_name else "water"
        tail.append(f"{ev['dist_water_mi']:.2f} mi to {target}")
    if ev.get("burn_year") and ev.get("burn_name"):
        tail.append(f"in the {ev['burn_year']} {ev['burn_name']} burn")
    if ev.get("dead_share_300m") is not None and ev["dead_share_300m"] >= 0.25:
        since = f" since {ev['leafon_baseline_year']}" if ev.get("leafon_baseline_year") else ""
        tail.append(f"Sentinel-2: {int(round(ev['dead_share_300m'] * 100))}% of ground within 300 m "
                    f"lost greenness{since}, likely dead timber")
    if ev.get("snow_now") is True:
        tail.append(f"snow on the ground ({ev.get('snow_date') or 'latest Sentinel-2'})")
    if ev.get("timber_block") is not None and ev.get("timber_block_mi") is not None:
        if ev["timber_block_mi"] <= 0.01:
            tail.append(f"inside security timber {ev['timber_block']} ({ev['timber_block_acres']:,} ac)")
        elif ev["timber_block_mi"] <= 1.5:
            tail.append(f"{ev['timber_block_mi']:.1f} mi to security timber {ev['timber_block']} ({ev['timber_block_acres']:,} ac)")
    sentence = f"{lead}{body}; {', '.join(tail)}." if tail else f"{lead}{body}."
    return sentence.encode("ascii", "replace").decode("ascii")


def short_tag(ev: dict, wp_type: str) -> str:
    comp = ev.get("aspect_compass") or ""
    if wp_type == "BED":
        landform = "bench" if ev.get("tpi_class") == "bench" else "timber"
        return f"{comp}-{landform}"[:10] if comp else landform[:10]
    if wp_type == "FEED":
        return "burn-edge" if ev.get("burn_year") else "meadow"
    if wp_type == "WATER":
        return "creek" if ev.get("nearest_water_name") else "water"
    return {"SADDLE": "saddle", "GLASS": "glass", "CAMP": "camp", "ACCESS": "TH"}.get(wp_type, "pt")
