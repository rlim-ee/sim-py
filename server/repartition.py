# server/repartition.py — Carte choroplèthe (dc_per_million) + cercles (dc_total)
from shiny import render, ui
import geopandas as gpd
import numpy as np
import folium
import branca
import json
from pathlib import Path


# ---------- Chargement & préparation des données ----------
def _load_data(app_dir: Path):
    geo_path = app_dir / "www" / "data" / "europe_map.geojson"
    if not geo_path.exists():
        raise FileNotFoundError(
            f"GeoJSON introuvable : {geo_path}\n"
            "Place ton fichier dans www/data/europe_map.geojson"
        )

    gdf = gpd.read_file(geo_path)

    # CRS -> WGS84
    if gdf.crs is None or (getattr(gdf.crs, "to_epsg", lambda: None)() != 4326):
        gdf = gdf.to_crs(4326)

    # Harmonisation des colonnes (selon ton jeu)
    gdf = gdf.rename(
        columns={
            "name": "country",
            "nb_dc": "dc_total",
            "pop": "population",
        }
    )

    # Points de représentation pour les cercles
    reps = gdf.representative_point()
    gdf["lat"] = reps.y.astype(float)
    gdf["lon"] = reps.x.astype(float)

    # Tu as indiqué que tout est déjà numérique -> on ne reconvertit rien ici,
    # mais on s'assure que les champs critiques seront castés au moment de l'usage.
    return gdf


# ---------- Construction de la carte Folium ----------
def _build_map(gdf):
    # Focus Europe
    m = folium.Map(location=[54.0, 15.0], zoom_start=4, tiles="cartodbpositron", control_scale=True)

    # Échelle choroplèthe (casts en float Python)
    vmin = float(np.nanmin(gdf["dc_per_million"]))
    vmax = float(np.nanmax(gdf["dc_per_million"]))
    if not np.isfinite(vmax) or vmax <= vmin:
        vmax = vmin + 1.0

    cmap = branca.colormap.linear.YlOrRd_09.scale(float(vmin), float(vmax))
    cmap.caption = "DC / million d'habitants"

    def style_fn(feat):
        v = feat["properties"].get("dc_per_million")
        try:
            v = float(v) if v is not None else None
        except Exception:
            v = None
        color = "#cccccc" if v is None else cmap(v)
        return {"fillColor": color, "color": "#999999", "weight": 0.7, "fillOpacity": 0.85}

    # IMPORTANT : fournir un GeoJSON sous forme de dict Python pur (pas de ndarrays)
    geojson_dict = json.loads(gdf.to_json(drop_id=True))

    folium.GeoJson(
        data=geojson_dict,
        name="Choroplèthe DC/million",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=["country", "dc_total", "population", "dc_per_million"],
            aliases=["Pays", "Nombre de DC", "Population", "DC / million hab."],
            labels=True,
            sticky=False,
        ),
        highlight_function=lambda _: {"weight": 2, "color": "#333333"},
        smooth_factor=0.3,
        embed=True,
    ).add_to(m)

    # Cercles proportionnels (nb total de DC) — échelle racine
    dc = gdf["dc_total"].to_numpy(dtype=float)
    if float(np.nanmax(dc)) == float(np.nanmin(dc)):
        radii = [10.0] * len(dc)
    else:
        r = np.sqrt(np.clip(dc, a_min=0, a_max=None))
        rmin, rmax = float(np.nanmin(r)), float(np.nanmax(r))
        radii = [float(np.interp(rv, (rmin, rmax), (6.0, 28.0))) for rv in r.tolist()]

    for (_, row), R in zip(gdf.iterrows(), radii):
        lat = float(row["lat"])
        lon = float(row["lon"])
        dc_total = int(row["dc_total"])
        dpm = float(row["dc_per_million"])
        folium.CircleMarker(
            location=(lat, lon),
            radius=float(R),
            weight=1,
            color="#3b0a91",
            fill=True,
            fill_opacity=0.75,
            fill_color="#3b0a91",
            tooltip=folium.Tooltip(
                f"<b>{row['country']}</b><br>"
                f"DC (total): <b>{dc_total}</b><br>"
                f"DC/million: {dpm:.1f}"
            ),
        ).add_to(m)

    cmap.add_to(m)
    folium.LayerControl(collapsed=False).add_to(m)

    # Ajuste aux limites
    try:
        tb = gdf.total_bounds  # [minx, miny, maxx, maxy] -> cast Python floats
        bounds = [[float(tb[1]), float(tb[0])], [float(tb[3]), float(tb[2])]]  # [[south, west], [north, east]]
        m.fit_bounds(bounds)
    except Exception:
        pass

    return m


# ---------- Serveur Shiny ----------
def server(input, output, session, app_dir: Path):
    try:
        gdf = _load_data(app_dir)
    except FileNotFoundError as e:
        @output
        @render.ui
        def repartition_map():
            return ui.card(
                ui.h4("GeoJSON introuvable"),
                ui.pre(str(e)),
                ui.p("Place un fichier dans ", ui.code("www/data/europe_map.geojson"), "."),
            )
        return

    @output
    @render.ui
    def repartition_map():
        m = _build_map(gdf)
        return ui.HTML(m._repr_html_())
