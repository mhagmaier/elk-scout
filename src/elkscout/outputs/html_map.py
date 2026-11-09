"""Interactive folium map -> data/out/map.html.

Layers (each toggleable): habitat-score heatmap (RGBA PNG overlay), typed
waypoint markers with evidence popups, motorized routes, trails, burn
perimeters, private land, unit boundary, hunt-area outlines. USGS topo and
Esri imagery basemaps — tiles load in the viewer's browser, so offline
pipeline runs still produce a working map.
"""

from __future__ import annotations

import base64
import logging
import warnings
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import rasterio.warp
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.io import MemoryFile

from ..config import Config
from ..factors import _read_vec
from ..grid import read_raster
from ..paths import Workspace
from ..sources.mvum import mvum_roads_path

log = logging.getLogger("elkscout.map")

TYPE_COLORS = {
    "BED": "#1f77b4",
    "FEED": "#2ca02c",
    "WATER": "#17becf",
    "SADDLE": "#d62728",
    "GLASS": "#ffbf00",
    "CAMP": "#9467bd",
    "ACCESS": "#7f7f7f",
}

# Dark-blue -> green -> yellow score ramp (viridis-like), transparent at zero.
_RAMP = [
    (0.0, (68, 1, 84)),
    (0.25, (59, 82, 139)),
    (0.5, (33, 145, 140)),
    (0.75, (94, 201, 98)),
    (1.0, (253, 231, 37)),
]
OVERLAY_ALPHA = 150
SIMPLIFY_DEG = 0.0005

USGS_TOPO = "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}"
ESRI_IMAGERY = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
)


def _score_png_uri(score: np.ndarray) -> str:
    s = np.clip(np.nan_to_num(score, nan=0.0), 0.0, 1.0)
    xs = [p[0] for p in _RAMP]
    rgba = np.zeros((*s.shape, 4), dtype=np.uint8)
    for i in range(3):
        ys = [p[1][i] for p in _RAMP]
        rgba[..., i] = np.interp(s, xs, ys).astype(np.uint8)
    rgba[..., 3] = np.where(s > 0.01, OVERLAY_ALPHA, 0).astype(np.uint8)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", rasterio.errors.NotGeoreferencedWarning)
        with MemoryFile() as mem:
            with mem.open(driver="PNG", width=s.shape[1], height=s.shape[0], count=4, dtype="uint8") as ds:
                ds.write(rgba.transpose(2, 0, 1))
            payload = mem.read()
    return "data:image/png;base64," + base64.b64encode(payload).decode()


def _add_lines(m, gdf: gpd.GeoDataFrame, name: str, color: str, dash: str | None = None, weight: float = 1.5):
    if gdf is None or len(gdf) == 0:
        return
    g = gdf.copy()
    g["geometry"] = g.geometry.simplify(SIMPLIFY_DEG)
    fg = folium.FeatureGroup(name=name, show=True)
    folium.GeoJson(
        g.to_json(),
        style_function=lambda _f, c=color, d=dash, w=weight: {"color": c, "weight": w, "dashArray": d},
    ).add_to(fg)
    fg.add_to(m)


def write_map(ws: Workspace, cfg: Config) -> Path:
    from ..waypoints import load_waypoints

    comp, grid = read_raster(ws.composite_tif)
    composite = comp["composite"]
    wp, areas = load_waypoints(ws)
    minlon, minlat, maxlon, maxlat = grid.bbox4326()

    m = folium.Map(
        location=[(minlat + maxlat) / 2, (minlon + maxlon) / 2],
        zoom_start=12,
        tiles=None,
        control_scale=True,
    )
    folium.TileLayer(USGS_TOPO, name="USGS Topo", attr="USGS The National Map").add_to(m)
    folium.TileLayer(ESRI_IMAGERY, name="Esri Imagery", attr="Esri, Maxar, Earthstar Geographics", show=False).add_to(m)

    # Reproject the UTM composite onto a geographic lattice before rendering —
    # stretching the raw UTM array onto the 4326 envelope misregisters the
    # overlay by the grid convergence (~100 m at this latitude).
    dst_transform, dst_w, dst_h = rasterio.warp.calculate_default_transform(
        grid.crs, CRS.from_epsg(4326), grid.width, grid.height, *grid.bounds
    )
    geo_score = np.full((dst_h, dst_w), np.nan, dtype=np.float32)
    rasterio.warp.reproject(
        composite,
        geo_score,
        src_transform=grid.transform,
        src_crs=grid.crs,
        dst_transform=dst_transform,
        dst_crs=CRS.from_epsg(4326),
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    west, north = dst_transform.c, dst_transform.f
    east = west + dst_w * dst_transform.a
    south = north + dst_h * dst_transform.e

    score_fg = folium.FeatureGroup(name="Habitat score")
    folium.raster_layers.ImageOverlay(
        image=_score_png_uri(geo_score),
        bounds=[[south, west], [north, east]],
        opacity=1.0,
        zindex=2,
    ).add_to(score_fg)
    score_fg.add_to(m)

    burns = _read_vec(ws.burns_geojson)
    if len(burns):
        fg = folium.FeatureGroup(name="Burns")
        for _, row in burns.iterrows():
            folium.GeoJson(
                gpd.GeoSeries([row.geometry.simplify(SIMPLIFY_DEG)], crs="EPSG:4326").to_json(),
                style_function=lambda _f: {"color": "#e6641e", "weight": 1, "fillOpacity": 0.15},
                tooltip=f"{row.get('fire_name', 'burn')} {row.get('year', '')}",
            ).add_to(fg)
        fg.add_to(m)

    ownership = _read_vec(ws.ownership_geojson)
    if len(ownership) and "public" in ownership.columns:
        private = ownership[~ownership["public"].astype(bool)]
        if len(private):
            fg = folium.FeatureGroup(name="Private land")
            folium.GeoJson(
                private.to_json(),
                style_function=lambda _f: {"color": "#555555", "weight": 1, "fillColor": "#555555", "fillOpacity": 0.35},
            ).add_to(fg)
            fg.add_to(m)

    motorized = _read_vec(ws.motorized_geojson)
    mvum = _read_vec(mvum_roads_path(ws))
    if len(mvum):
        motorized = gpd.GeoDataFrame(
            pd.concat([motorized[["geometry"]], mvum[["geometry"]]], ignore_index=True), crs="EPSG:4326"
        ) if len(motorized) else mvum
    _add_lines(m, motorized, "Motorized routes", "#cc0000")
    _add_lines(m, _read_vec(ws.trails_geojson), "Trails", "#8b5a2b", dash="6 4")

    boundary = _read_vec(ws.boundary_geojson)
    _add_lines(m, boundary, "Unit boundary", "#000000", weight=2.5)

    if len(areas):
        fg = folium.FeatureGroup(name="Hunt areas")
        for _, row in areas.iterrows():
            folium.GeoJson(
                gpd.GeoSeries([row.geometry.simplify(SIMPLIFY_DEG)], crs="EPSG:4326").to_json(),
                style_function=lambda _f: {"color": "#222222", "weight": 3, "dashArray": "10 6", "fillOpacity": 0},
                tooltip=f"{row['rank']}. {row['name']} (mean {row['mean_score']})",
            ).add_to(fg)
        fg.add_to(m)

    from ..timber import load_blocks

    blocks = load_blocks(ws)
    if len(blocks):
        fg = folium.FeatureGroup(name="Security timber")
        for _, row in blocks.iterrows():
            dead = "dead" in str(row.get("imagery") or "").lower()
            folium.GeoJson(
                gpd.GeoSeries([row.geometry.simplify(SIMPLIFY_DEG / 5)], crs="EPSG:4326").to_json(),
                style_function=lambda _f, d=dead: {
                    "color": "#7f7f7f" if d else "#ffd400",
                    "weight": 2,
                    "fillColor": "#7f7f7f" if d else "#1b5e20",
                    "fillOpacity": 0.25,
                },
                tooltip=f"{row['id']} security timber, {int(row['acres']):,} ac, "
                        f"median {row['road_mi_median']} mi from roads"
                        + (f" — {row['imagery']}" if row.get("imagery") else ""),
            ).add_to(fg)
        fg.add_to(m)

    wp_fg = folium.FeatureGroup(name="Waypoints")
    for _, row in wp.iterrows():
        folium.CircleMarker(
            location=[row.geometry.y, row.geometry.x],
            radius=6,
            color=TYPE_COLORS.get(row["wp_type"], "#000000"),
            fill=True,
            fill_opacity=0.9,
            popup=folium.Popup(f"<b>{row['name']}</b><br>{row['desc']}<br>score {row['score']}", max_width=320),
            tooltip=row["name"],
        ).add_to(wp_fg)
    wp_fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    out = ws.map_html
    out.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(out))
    log.info("map: wrote %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out
