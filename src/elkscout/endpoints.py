"""All public data endpoints in one place (verified 2026-08; see README provenance)."""

# Idaho Fish & Game hunting layers; GMU polygons are layer 3 (field names vary —
# discover from layer metadata at runtime).
IDFG_HUNTING = "https://gisportal-idfg.idaho.gov/hosting/rest/services/Hunting/MapServer"
IDFG_HUNTING_ALT = "https://gis.idfg.idaho.gov/server/rest/services/Hunting/MapServer"
IDFG_GMU_LAYER = 3


def idfg_default_boundary():
    """The built-in Idaho boundary source, used when a config has no `boundary:` block."""
    from .config import BoundarySource  # local import: endpoints stays import-light

    return BoundarySource(
        base_url=IDFG_HUNTING,
        alt_urls=[IDFG_HUNTING_ALT],
        layer=IDFG_GMU_LAYER,
        layer_hint="unit",
        unit_field=None,
        unit_field_hints=["NAME", "UNIT", "GMU"],
        unit_value_format="{unit}",
    )

# USGS 3DEP seamless elevation (meters).
DEM_IMAGESERVER = "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer"

# MTBS burned-area perimeters (all years) — layer 63 of the EDW service.
MTBS = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MTBS_01/MapServer"
MTBS_LAYER = 63

# USFS Motor Vehicle Use Map (authoritative motorized routes; discover layer ids by name).
MVUM = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_MVUM_01/MapServer"

# BLM Surface Management Agency (land ownership) — the LimitedScale service is queryable.
BLM_SMA = "https://gis.blm.gov/arcgis/rest/services/lands/BLM_Natl_SMA_LimitedScale/MapServer"

# USGS National Map hydrography.
NHDPLUS_HR = "https://hydro.nationalmap.gov/arcgis/rest/services/NHDPlus_HR/MapServer"
WBD = "https://hydro.nationalmap.gov/arcgis/rest/services/wbd/MapServer"

# OpenStreetMap Overpass (primary + mirror).
OVERPASS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# MRLC GeoServer (NLCD land cover + tree canopy) via WCS.
MRLC_WCS = "https://www.mrlc.gov/geoserver/ows"

# NRCS AWDB (SNOTEL) REST API v1.
AWDB = "https://wcc.sc.egov.usda.gov/awdbRestApi/services/v1"

# Open-Meteo forecast (no key; 16-day horizon).
OPEN_METEO = "https://api.open-meteo.com/v1/forecast"

# Endpoints probed by `elkscout doctor`: (name, url, params)
DOCTOR_PROBES = [
    ("IDFG GMU service", IDFG_HUNTING, {"f": "json"}),
    ("IDFG GMU alt host", IDFG_HUNTING_ALT, {"f": "json"}),
    ("3DEP elevation", DEM_IMAGESERVER, {"f": "json"}),
    ("MTBS burns", MTBS, {"f": "json"}),
    ("USFS MVUM", MVUM, {"f": "json"}),
    ("BLM ownership", BLM_SMA, {"f": "json"}),
    ("NHDPlus water", NHDPLUS_HR, {"f": "json"}),
    ("WBD watersheds", WBD, {"f": "json"}),
    ("Overpass OSM", "https://overpass-api.de/api/status", {}),
    ("MRLC landcover", MRLC_WCS, {"service": "WCS", "request": "GetCapabilities"}),
    ("SNOTEL AWDB", f"{AWDB}/reference-data", {"referenceLists": "networks"}),
    ("Open-Meteo", OPEN_METEO, {"latitude": 44.1, "longitude": -115.7, "daily": "temperature_2m_max", "forecast_days": 1}),
]
