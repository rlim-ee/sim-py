# server/energie/repartition.py — carte et graphiques "Répartition des DC en Europe"
#
# Ce module répond à la question : "où se concentrent les data centers en Europe ?"
#
# Il produit trois outputs :
#   - repartition_map  → carte choroplèthe + cercles proportionnels (Folium)
#   - dc_share_plot    → barres horizontales (top 10 pays par part de DC)
#   - kpi_total_dc, kpi_leader_value, kpi_leader_caption, kpi_top10  → chiffres clés
#
# Folium est une bibliothèque Python qui génère des cartes interactives
# (basées sur Leaflet.js) sous forme de fichier HTML. Ce HTML est injecté
# directement dans la page Shiny via ui.HTML().
#
# Les données viennent de www/data/europe_map.geojson.
# La carte est pré-construite en clair ET en sombre au chargement pour
# éviter un recalcul à chaque changement de thème.
from __future__ import annotations
from shiny import render, ui, req
import shinywidgets as sw

from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import plotly.express as px
import folium, branca, json

from server._common import is_dark, plotly_theme, cached


# =========================================================
# Construction de la carte Folium
# =========================================================
def _build_map_html(gdf: gpd.GeoDataFrame, gj_text: str, dark: bool) -> str:
    """
    Construit la carte choroplèthe Europe avec les cercles proportionnels.
    Retourne du HTML brut que Shiny affichera dans un iframe invisible.
    """
    tiles = "cartodbdark_matter" if dark else "cartodbpositron"
    m = folium.Map(
        location=[54.0, 15.0],
        zoom_start=4,
        tiles=tiles,
        control_scale=True,
        width="100%",
        height="100%",
    )

    # Calcul de l'échelle de couleur : du jaune (peu de DC) au rouge (beaucoup)
    vals = gdf["dc_per_million"].to_numpy(dtype=float) if "dc_per_million" in gdf.columns else np.array([0.0])
    vmin = float(np.nanmin(vals)) if len(vals) else 0.0
    vmax = float(np.nanmax(vals)) if len(vals) else 1.0
    if not np.isfinite(vmin):
        vmin = 0.0
    if not np.isfinite(vmax) or vmax <= vmin:
        vmax = vmin + 1.0

    cmap = branca.colormap.linear.YlOrRd_09.scale(vmin, vmax)
    cmap.caption = "DC / million d'habitants"

    def style_fn(feat):
        # Chaque pays reçoit une couleur selon sa densité de DC par habitant
        v = feat["properties"].get("dc_per_million")
        try:
            v = float(v) if v is not None else None
        except Exception:
            v = None
        return {
            "fillColor": "#cccccc" if v is None else cmap(v),
            "color": "#999" if not dark else "#94A3B8",
            "weight": 0.7,
            "fillOpacity": 0.85,
        }

    # Couche choroplèthe avec infobulle au survol
    folium.GeoJson(
        data=json.loads(gj_text),
        name="Choroplèthe DC/million",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=[c for c in ["country", "dc_total", "population", "dc_per_million"] if c in gdf.columns],
            aliases=["Pays", "Nombre de DC", "Population", "DC / million hab."],
            labels=True, sticky=False,
        ),
        highlight_function=lambda _: {"weight": 2, "color": "#333" if not dark else "#E2E8F0"},
        smooth_factor=0.3,
        embed=True,
    ).add_to(m)

    # Cercles proportionnels : la taille reflète le nombre total de DC (pas la densité)
    if {"lat", "lon", "dc_total"}.issubset(gdf.columns):
        dc = gdf["dc_total"].to_numpy(dtype=float)
        if float(np.nanmax(dc)) == float(np.nanmin(dc)):
            radii = [10.0] * len(dc)
        else:
            r = np.sqrt(np.clip(dc, 0, None))
            rmin, rmax = float(np.nanmin(r)), float(np.nanmax(r))
            radii = [float(np.interp(rv, (rmin, rmax), (6.0, 28.0))) for rv in r.tolist()]

        circle_color = "#3b0a91"
        for (_, row), R in zip(gdf.iterrows(), radii):
            folium.CircleMarker(
                location=(float(row["lat"]), float(row["lon"])),
                radius=float(R),
                weight=1,
                color=circle_color,
                fill=True,
                fill_color=circle_color,
                fill_opacity=0.75,
                tooltip=folium.Tooltip(
                    f"<b>{row['country']}</b><br>"
                    f"DC (total): <b>{int(row['dc_total'])}</b><br>"
                    f"DC/million: {float(row.get('dc_per_million', 0.0)):.1f}"
                ),
            ).add_to(m)

    cmap.add_to(m)

    # Ajustement automatique du zoom pour englober tous les pays
    try:
        tb = gdf.total_bounds
        m.fit_bounds([[float(tb[1]), float(tb[0])], [float(tb[3]), float(tb[2])]])
    except Exception:
        pass

    # Folium génère du HTML avec une hauteur exprimée en pourcentage flottant (0.0%)
    # qu'on corrige en valeur utilisable par le navigateur.
    html = m._repr_html_()
    html = (html
            .replace("height: 0.0%;", "height: 100%;")
            .replace("height:0.0%;", "height: 100%;")
            .replace("padding-bottom: 60.0%;", "padding-bottom: 0;")
            .replace("padding-bottom: 75.0%;", "padding-bottom: 0;"))
    return html


# =========================================================
# Chargement et préparation des données (une seule fois)
# =========================================================
def _load_data_prepared(app_dir: Path) -> dict:
    """Charge le GeoJSON, prépare les colonnes et pré-calcule les deux versions de la carte."""
    geo_path = Path(app_dir) / "www" / "data" / "europe_map.geojson"
    if not geo_path.exists():
        raise FileNotFoundError(f"GeoJSON introuvable : {geo_path}")

    gdf = gpd.read_file(geo_path)
    # Reprojection en WGS84 (coordonnées géographiques standard pour Folium/Leaflet)
    if gdf.crs is None or (getattr(gdf.crs, "to_epsg", lambda: None)() != 4326):
        gdf = gdf.to_crs(4326)

    rename_map = {"name": "country", "nb_dc": "dc_total", "pop": "population"}
    gdf = gdf.rename(columns={k: v for k, v in rename_map.items() if k in gdf.columns})
    cols_keep = [c for c in ["country", "dc_total", "population", "dc_per_million", "geometry"] if c in gdf.columns]
    gdf = gdf[cols_keep].copy()

    for col in ("dc_total", "population", "dc_per_million"):
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce").fillna(0.0)

    # Point représentatif de chaque pays pour positionner les cercles
    reps = gdf.geometry.representative_point()
    gdf["lat"] = reps.y.astype(float)
    gdf["lon"] = reps.x.astype(float)

    # Simplification géométrique pour alléger le GeoJSON transmis au navigateur
    try:
        gdf_simpl = gdf.to_crs(3857).copy()
        gdf_simpl["geometry"] = gdf_simpl.geometry.simplify(2000)  # ≈ 2 km de tolérance
        gj_text = gdf_simpl.to_crs(4326)[
            ["country", "dc_total", "population", "dc_per_million", "geometry"]
        ].to_json()
    except Exception:
        gj_text = geo_path.read_text(encoding="utf-8")

    # Tableau des parts par pays (pour le graphique à barres)
    df_share = pd.DataFrame({
        "country": gdf["country"].astype(str),
        "dc_total": gdf["dc_total"].astype(float),
    }).dropna()
    tot_dc = float(df_share["dc_total"].sum()) if not df_share.empty else 0.0
    df_share["share"] = (df_share["dc_total"] / tot_dc * 100.0) if tot_dc > 0 else 0.0
    df_share = df_share.sort_values("share", ascending=False).reset_index(drop=True)

    # Les deux versions de la carte sont construites une seule fois
    # (le cache évite de les reconstruire pour chaque utilisateur)
    maps_html = {
        False: _build_map_html(gdf, gj_text, dark=False),
        True:  _build_map_html(gdf, gj_text, dark=True),
    }

    return {
        "gdf": gdf,
        "gj_text": gj_text,
        "df_share": df_share,
        "total_dc": tot_dc,
        "maps_html": maps_html,
    }


def _get_data(app_dir: Path) -> dict:
    """Point d'accès au cache. Le chargement ne se fait qu'au premier appel."""
    return cached(f"repartition::{Path(app_dir).resolve()}", lambda: _load_data_prepared(app_dir))


# =========================================================
# Fonctions serveur Shiny
# =========================================================
def server(input, output, session, app_dir: Path):

    # --- Carte Europe ---
    # Se redessine uniquement si l'onglet actif est "Europe" et si le thème change.
    @output
    @render.ui
    def repartition_map():
        # req() interrompt le rendu si la condition n'est pas remplie
        # (évite un calcul inutile quand l'onglet n'est pas visible)
        tabs = getattr(input, "tabs_repartition", None)
        if callable(tabs):
            req(tabs() == "Europe")

        d = _get_data(app_dir)
        dark = is_dark(input)
        html = d["maps_html"][bool(dark)]

        return ui.div(ui.HTML(html), class_="map-wrap")

    # --- Graphique : part du nombre total de DC par pays (top 10) ---
    @output
    @sw.render_widget
    def dc_share_plot():
        d = _get_data(app_dir)
        df_share = d["df_share"]
        if df_share.empty:
            return px.bar(title="Aucune donnée")

        TOP_N = 10
        top = df_share.head(TOP_N)
        rest_pct = max(0.0, 100.0 - float(top["share"].sum()))
        # On regroupe les pays hors top 10 dans "Reste de l'Europe"
        chart_df = pd.concat(
            [pd.DataFrame([{"country": "Reste de l'Europe", "share": rest_pct}]), top[["country", "share"]]],
            ignore_index=True,
        )

        data_plot = chart_df.sort_values("share", ascending=True)
        th = plotly_theme(is_dark(input))

        fig = px.bar(
            data_plot,
            x="share", y="country", orientation="h",
            text=data_plot["share"].map(lambda v: f"{v:.1f}%"),
            color="share",
            color_continuous_scale="Purples",
        )
        fig.update_traces(
            textposition="outside", cliponaxis=False,
            hovertemplate="(%{x:.1f}%, %{y})<extra></extra>",
            marker_line=dict(color=th["bar_outline"], width=1),
        )
        xmax = float(data_plot["share"].max()) if len(data_plot) else 0.0
        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            autosize=True, showlegend=False, title_text="",
            paper_bgcolor=th["paper"], plot_bgcolor=th["plot"],
            font=dict(color=th["font"], family="Poppins, Arial, sans-serif", size=13),
            coloraxis_showscale=False,
        )
        fig.update_xaxes(
            title_text="Part du nombre de DC", ticksuffix="%", range=[0, xmax * 1.15],
            gridcolor=th["grid"], zeroline=True, zerolinecolor=th["zeroline"],
            linecolor=th["grid"], tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
        )
        fig.update_yaxes(
            title_text="", gridcolor=th["grid"], linecolor=th["grid"],
            tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]), automargin=True,
        )
        return fig

    # --- Chiffres clés (KPI) ---
    @output
    @render.text
    def kpi_total_dc():
        return f"{int(_get_data(app_dir)['total_dc']):,} DC".replace(",", " ")

    @output
    @render.text
    def kpi_leader_value():
        df = _get_data(app_dir)["df_share"]
        if df.empty:
            return "—"
        return f"{df.iloc[0]['share']:.1f} %"

    @output
    @render.text
    def kpi_leader_caption():
        df = _get_data(app_dir)["df_share"]
        if df.empty:
            return "Aucun pays"
        leader = df.iloc[0]
        return f"Part du {leader['country']} dans le nombre total de DC."

    @output
    @render.text
    def kpi_top10():
        df = _get_data(app_dir)["df_share"]
        if df.empty:
            return "—"
        return f"{float(df.head(10)['share'].sum()):.0f} %"
