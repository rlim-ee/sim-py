# server/repartition.py — Europe (no-reactive + cache + dark)
from __future__ import annotations
from shiny import render, ui, req
import shinywidgets as sw

from pathlib import Path
import geopandas as gpd
import pandas as pd
import numpy as np
import plotly.express as px
import folium, branca, json

# =========================
#     Cache module-level
# =========================
_DATA_CACHE: dict[str, dict] = {}  # clé: str(path.resolve()) -> payload dict


# ------------------ Helpers ------------------
def _is_dark(input) -> bool:
    """Retourne True si le dark mode est actif côté UI (sécurisé)."""
    try:
        dm = getattr(input, "darkmode", None)
        return bool(dm()) if callable(dm) else False
    except Exception:
        return False


def _plotly_theme(is_dark: bool):
    return {
        "font": "#e5e7eb" if is_dark else "#0f172a",
        "grid": "rgba(203,213,225,.26)" if is_dark else "rgba(15,23,42,.08)",
        "zeroline": "rgba(148,163,184,.35)" if is_dark else "rgba(100,116,139,.35)",
        "paper": "rgba(0,0,0,0)",
        "plot": "rgba(0,0,0,0)",
        "bar": "#7c8cff" if is_dark else "#5B7CFF",
        "bar_outline": "rgba(255,255,255,.18)" if is_dark else "rgba(0,0,0,.08)",
    }


# =========================================================
#                 Construction carte Folium
# =========================================================
def _build_map_html(gdf: gpd.GeoDataFrame, gj_text: str, is_dark: bool) -> str:
    tiles = "cartodbdark_matter" if is_dark else "cartodbpositron"
    m = folium.Map(
        location=[54.0, 15.0],
        zoom_start=4,
        tiles=tiles,
        control_scale=True,
        width="100%",
        height="100%",  # remplit le wrapper .map-wrap
    )

    # Choroplèthe DC / million hab
    vals = gdf["dc_per_million"].to_numpy(dtype=float) if "dc_per_million" in gdf.columns else np.array([0.0])
    vmin = float(np.nanmin(vals)) if len(vals) else 0.0
    vmax = float(np.nanmax(vals)) if len(vals) else 1.0
    if not np.isfinite(vmin): vmin = 0.0
    if not np.isfinite(vmax) or vmax <= vmin: vmax = vmin + 1.0

    cmap = branca.colormap.linear.YlOrRd_09.scale(vmin, vmax)
    cmap.caption = "DC / million d'habitants"

    def style_fn(feat):
        v = feat["properties"].get("dc_per_million")
        try:
            v = float(v) if v is not None else None
        except Exception:
            v = None
        return {
            "fillColor": "#cccccc" if v is None else cmap(v),
            "color": "#999" if not is_dark else "#94A3B8",
            "weight": 0.7,
            "fillOpacity": 0.85,
        }

    folium.GeoJson(
        data=json.loads(gj_text),
        name="Choroplèthe DC/million",
        style_function=style_fn,
        tooltip=folium.GeoJsonTooltip(
            fields=[c for c in ["country", "dc_total", "population", "dc_per_million"] if c in gdf.columns],
            aliases=["Pays", "Nombre de DC", "Population", "DC / million hab."],
            labels=True, sticky=False,
        ),
        highlight_function=lambda _: {"weight": 2, "color": "#333" if not is_dark else "#E2E8F0"},
        smooth_factor=0.3,
        embed=True,
    ).add_to(m)

    # Cercles proportionnels (si colonnes présentes)
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

    # Cadre de la carte
    try:
        tb = gdf.total_bounds
        m.fit_bounds([[float(tb[1]), float(tb[0])], [float(tb[3]), float(tb[2])]])
    except Exception:
        pass

    # Neutraliser le wrapper "ratio" que folium insère parfois
    html = m._repr_html_()
    html = (html
            .replace("height: 0.0%;", "height: 100%;")
            .replace("height:0.0%;", "height: 100%;")
            .replace("padding-bottom: 60.0%;", "padding-bottom: 0;")
            .replace("padding-bottom: 75.0%;", "padding-bottom: 0;"))
    return html


# =========================================================
#   Chargement unique + préparation (hors reactive.*)
# =========================================================
def _load_data_prepared(app_dir: Path) -> dict:
    geo_path = Path(app_dir) / "www" / "data" / "europe_map.geojson"
    if not geo_path.exists():
        raise FileNotFoundError(f"GeoJSON introuvable : {geo_path}")

    # GeoDataFrame (calculs + cercles)
    gdf = gpd.read_file(geo_path)
    if gdf.crs is None or (getattr(gdf.crs, "to_epsg", lambda: None)() != 4326):
        gdf = gdf.to_crs(4326)

    # Harmoniser / réduire
    rename_map = {"name": "country", "nb_dc": "dc_total", "pop": "population"}
    gdf = gdf.rename(columns={k: v for k, v in rename_map.items() if k in gdf.columns})
    cols_keep = [c for c in ["country", "dc_total", "population", "dc_per_million", "geometry"] if c in gdf.columns]
    gdf = gdf[cols_keep].copy()

    for col in ("dc_total", "population", "dc_per_million"):
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce").fillna(0.0)

    reps = gdf.geometry.representative_point()
    gdf["lat"] = reps.y.astype(float)
    gdf["lon"] = reps.x.astype(float)

    # GeoJSON simplifié
    try:
        gdf_simpl = gdf.to_crs(3857).copy()
        gdf_simpl["geometry"] = gdf_simpl.geometry.simplify(2000)  # ≈2 km
        gj_text = gdf_simpl.to_crs(4326)[
            ["country", "dc_total", "population", "dc_per_million", "geometry"]
        ].to_json()
    except Exception:
        gj_text = geo_path.read_text(encoding="utf-8")

    # Part de DC par pays
    df_share = pd.DataFrame({
        "country": gdf["country"].astype(str),
        "dc_total": gdf["dc_total"].astype(float),
    }).dropna()
    tot_dc = float(df_share["dc_total"].sum()) if not df_share.empty else 0.0
    df_share["share"] = (df_share["dc_total"] / tot_dc * 100.0) if tot_dc > 0 else 0.0
    df_share = df_share.sort_values("share", ascending=False).reset_index(drop=True)

    # Pré-construction HTML (clair/sombre)
    maps_html = {
        False: _build_map_html(gdf, gj_text, is_dark=False),
        True:  _build_map_html(gdf, gj_text, is_dark=True),
    }

    return {
        "gdf": gdf,
        "gj_text": gj_text,
        "df_share": df_share,
        "total_dc": tot_dc,
        "maps_html": maps_html,
    }


def _get_data(app_dir: Path) -> dict:
    """Retourne les données depuis un cache global non-réactif."""
    key = str(Path(app_dir).resolve())
    payload = _DATA_CACHE.get(key)
    if payload is None:
        payload = _load_data_prepared(app_dir)
        _DATA_CACHE[key] = payload
    return payload


# =========================================================
#                        SERVER
# =========================================================
def server(input, output, session, app_dir: Path):

    # -------- Carte Europe (aucun recalcul lourd) --------
    @output
    @render.ui
    def repartition_map():
        # Ne rendre que si l’onglet Europe est actif (évite courses d’état client)
        tabs = getattr(input, "tabs_repartition", None)
        if callable(tabs):
            req(tabs() == "Europe")

        d = _get_data(app_dir)
        dark = _is_dark(input)
        html = d["maps_html"][bool(dark)]

        # on renvoie le wrapper (hauteur fixée par CSS .map-wrap)
        return ui.div(ui.HTML(html), class_="map-wrap")

    # -------- Barres (part du nombre de DC) --------
    @output
    @sw.render_widget
    def dc_share_plot():
        d = _get_data(app_dir)
        df_share = d["df_share"]
        if df_share.empty:
            return px.bar(title="Aucune donnée")

        TOP_N = 12
        top = df_share.head(TOP_N)
        rest_pct = max(0.0, 100.0 - float(top["share"].sum()))
        chart_df = pd.concat(
            [pd.DataFrame([{"country": "Reste de l'Europe", "share": rest_pct}]), top[["country", "share"]]],
            ignore_index=True,
        )

        data_plot = chart_df.sort_values("share", ascending=True)
        th = _plotly_theme(_is_dark(input))

        fig = px.bar(
            data_plot,
            x="share", y="country", orientation="h",
            text=data_plot["share"].map(lambda v: f"{v:.1f}%"),
        )
        fig.update_traces(
            textposition="outside", cliponaxis=False,
            hovertemplate="(%{x:.1f}%, %{y})<extra></extra>",
            marker=dict(color=th["bar"], line=dict(color=th["bar_outline"], width=1)),
        )
        xmax = float(data_plot["share"].max()) if len(data_plot) else 0.0
        fig.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            autosize=True, showlegend=False, title_text="",
            paper_bgcolor=th["paper"], plot_bgcolor=th["plot"],
            font=dict(color=th["font"], family="Poppins, Arial, sans-serif", size=13),
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

    # ------------------------ KPI ------------------------
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
