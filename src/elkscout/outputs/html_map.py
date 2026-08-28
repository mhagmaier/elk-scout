"""Interactive folium map -> data/out/map.html.

Contract — write_map(ws, cfg) -> Path:
- Base: folium.Map over the AOI centroid; two tile layers with proper
  attribution: "USGS Topo" (https://basemap.nationalmap.gov/arcgis/rest/services
  /USGSTopo/MapServer/tile/{z}/{y}/{x}) and "Esri Imagery" (World_Imagery tile
  URL). NOTE: tiles load in the USER'S browser, not in this pipeline, so
  blocked egress here doesn't matter.
- Overlays, each in its own FeatureGroup with LayerControl:
  1. "Habitat score": composite raster -> colormapped RGBA PNG (pure numpy:
     a simple viridis-like or custom green-yellow-red ramp; alpha 0 where
     score==0/NaN, else ~140) via folium.raster_layers.ImageOverlay with the
     grid bounds in lat/lon (grid.bbox4326 — remember ImageOverlay wants
     [[south, west], [north, east]]).
  2. "Waypoints": CircleMarkers colored by type (BED #1f77b4, FEED #2ca02c,
     WATER #17becf, SADDLE #d62728, GLASS #ffbf00, CAMP #9467bd,
     ACCESS #7f7f7f), radius 6, popup = "<b>{name}</b><br>{desc}<br>
     score {score}", tooltip = name.
  3. "Motorized routes": red lines (weight 1.5) from motorized + mvum.
  4. "Trails": brown dashed lines.
  5. "Burns": orange polygons (fill_opacity 0.15), tooltip "{fire_name} {year}".
  6. "Private land": hatched effect approximated by gray fill_opacity 0.35 for
     ownership rows where public == False.
  7. "Unit boundary": black outline, no fill.
  8. "Hunt areas": thick dashed outlines w/ label tooltips.
- Save to ws.map_html; return the path. Simplify big vector layers
  (geometry.simplify(0.0005)) so the HTML stays under ~15 MB.
"""

from __future__ import annotations

from pathlib import Path

from ..config import Config
from ..paths import Workspace

TYPE_COLORS = {
    "BED": "#1f77b4",
    "FEED": "#2ca02c",
    "WATER": "#17becf",
    "SADDLE": "#d62728",
    "GLASS": "#ffbf00",
    "CAMP": "#9467bd",
    "ACCESS": "#7f7f7f",
}


def write_map(ws: Workspace, cfg: Config) -> Path:
    raise NotImplementedError
