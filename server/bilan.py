# server/bilan.py — Bilan énergétique (perf + dark + aire empilée)

from __future__ import annotations
from shiny import render, reactive, ui
import shinywidgets as sw

import pandas as pd
import geopandas as gpd
import folium
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
import json
from io import StringIO

# ------------------ Constantes / couleurs ------------------
COLORS = {
    "prod": "#2EA043",    # production (vert)
    "conso": "#1F6FEB",   # consommation (bleu)
    "nuc": "#F59E0B", "hyd": "#2563EB", "eol": "#10B981",
    "sol": "#F97316", "fos": "#374151", "aut": "#8B5CF6",
}
PIE_COLOR_MAP = {
    "Nucléaire": COLORS["nuc"], "Hydraulique": COLORS["hyd"],
    "Éolien": COLORS["eol"], "Solaire": COLORS["sol"],
    "Fossile": COLORS["fos"], "Autre": COLORS["aut"],
}
METRIC_CONSO = "CONSO_TWH"
METRIC_PROD  = "PR_TOT_TWH"
PIE_FIELDS   = ["PR_NUC_TWH","PR_HYD_TWH","PR_EOL_TWH","PR_SOL_TWH","PR_FOS_TWH","PR_AUT_TWH"]
PIE_LABELS   = ["Nucléaire","Hydraulique","Éolien","Solaire","Fossile","Autre"]

def _is_dark(input) -> bool:
    try:
        return bool(input.darkmode())
    except Exception:
        return False

# ------------------ Chargement + préparation  ------------------
def _load_data_prepared(app_dir: Path):
    path = app_dir / "www" / "data" / "regions_simplified.geojson"

    gj_text = path.read_text(encoding="utf-8")

    # 2) GeoPandas pour les valeurs et le point interne (placement des cercles)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    for col in [METRIC_CONSO, METRIC_PROD, *PIE_FIELDS]:
        if col in gdf.columns:
            gdf[col] = pd.to_numeric(gdf[col], errors="coerce").fillna(0.0)

    rep = gdf.geometry.representative_point()
    gdf["lon"] = rep.x.astype(float)
    gdf["lat"] = rep.y.astype(float)

    try:
        gdf_simpl = gdf.to_crs(3857).copy()
        gdf_simpl["geometry"] = gdf_simpl.geometry.simplify(400)  # ~400 m
        gj_text_simpl = gdf_simpl.to_crs(4326).to_json()
        gj_text = gj_text_simpl
    except Exception:
        pass  

    regions = sorted(gdf["NOM"].astype(str).tolist())
    # Sommes nationales pour le pie "France"
    france_sum = gdf[PIE_FIELDS].sum()

    return {
        "gdf": gdf,
        "gj_text": gj_text,
        "regions": regions,
        "france_sum": france_sum,
    }

# ------------------ Fabrique la carte Folium ------------------
def _build_map_html(gdf: gpd.GeoDataFrame, gj_text: str, metric_key: str, dark: bool) -> str:
    tiles = "cartodbdark_matter" if dark else "cartodbpositron"
    contour_color   = "#6B7280" if not dark else "#94A3B8"
    highlight_color = "#111827" if not dark else "#E2E8F0"
    circle_color    = COLORS["prod"] if metric_key == METRIC_PROD else COLORS["conso"]
    label_metric    = "Production" if metric_key == METRIC_PROD else "Consommation"

    m = folium.Map(location=[46.8, 2.5], zoom_start=5, tiles=tiles, control_scale=True, width="100%")

    # contours
    folium.GeoJson(
        data=json.loads(gj_text),
        name="Régions (contours)",
        style_function=lambda feat: {
            "fillColor": "#000000",
            "color": contour_color,
            "weight": 1,
            "fillOpacity": 0.04,
        },
        highlight_function=lambda feat: {"weight": 2, "color": highlight_color, "fillOpacity": 0.06},
    ).add_to(m)

    # cercles
    vmax = float(max(1.0, gdf[metric_key].max()))
    for _, r in gdf.iterrows():
        val = float(r[metric_key])
        radius = max(6.0, (val / vmax) * 50.0) if val > 0 else 4.0
        tooltip = f"<b>{r.get('NOM','')}</b><br>{label_metric} : {val:,.1f} TWh".replace(",", " ")
        folium.CircleMarker(
            location=[float(r["lat"]), float(r["lon"])],
            radius=radius,
            color=circle_color, fill=True, fill_color=circle_color, fill_opacity=0.55,
            weight=1, opacity=0.95, tooltip=tooltip
        ).add_to(m)

    return m._repr_html_()

# ------------------ SERVER ------------------
def server(input, output, session, app_dir: Path):
    # Cache des données ET des cartes prérendues
    _data_cache = reactive.Value(None)
    _map_cache: dict[tuple[str, bool], str] = {}

    @reactive.calc
    def data():
        obj = _data_cache.get()
        if obj is None:
            obj = _load_data_prepared(app_dir)
            _data_cache.set(obj)
        return obj

    # Init select régions
    @reactive.effect
    def _init_select():
        ui.update_select("fr_region", choices=["France"] + data()["regions"], selected="France")

    # --------- Carte ---------
    @output
    @render.ui
    def fr_map():
        try:
            if input.tabs_bilan() != "France":
                return ui.HTML("")  
        except Exception:
            pass

        d = data()
        metric = input.fr_metric()
        dark   = _is_dark(input)
        key    = (metric, dark)

        if key not in _map_cache:
            _map_cache[key] = _build_map_html(d["gdf"], d["gj_text"], metric, dark)

        return ui.HTML(_map_cache[key])

    # --------- Camembert ---------
    @output
    @sw.render_widget
    def prod_pie():
        try:
            if input.tabs_bilan() != "France":
                return px.scatter() 
        except Exception:
            pass

        gdf = data()["gdf"]
        region = input.fr_region() or "France"

        if region == "France":
            s = data()["france_sum"]
            title = "Production par filière (TWh/an) — France"
        else:
            row = gdf.loc[gdf["NOM"].astype(str) == region]
            s = (row.iloc[0][PIE_FIELDS] if not row.empty else pd.Series([0,0,0,0,0,0], index=PIE_FIELDS))
            title = f"Production par filière (TWh/an) — {region}"

        df_pie = pd.DataFrame({"Filière": PIE_LABELS, "TWh": s.values.astype(float)})
        fig = px.pie(
            df_pie, names="Filière", values="TWh", title=title, hole=0.15,
            color="Filière", color_discrete_map=PIE_COLOR_MAP
        )

        # thème dark/clair
        dark = _is_dark(input)
        font_color = "#F8FAFC" if dark else "#0B162C"
        fig.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value:.1f} TWh<extra></extra>")
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, family="Poppins, Arial, sans-serif"),
            legend=dict(title="", font=dict(color=font_color)),
            title=dict(font=dict(color=font_color)),
            margin=dict(t=58, r=10, b=10, l=10),
        )
        return fig

    # --------- Aire empilée + conso (2010–2024) ---------
    @output
    @sw.render_widget
    def area_chart():
        try:
            if input.tabs_bilan() != "France":
                return go.Figure()
        except Exception:
            pass

        # Données CSV (séparateur ;) — adapter si chargé d'un fichier
        csv_text = """year;conso;nucleaire;hydraulique;fossile;eolien;solaire;autre
2010;499;408;68;55;10;1;5
2011;472;416;50;52;12;2;6
2012;487;405;64;48;15;4;6
2013;495;404;76;40;16;5;7
2014;463;416;67;25;17;6;7
2015;474;384;59;33;21;7;7
2016;482;384;64;45;20;8;8
2017;481;380;53;53;24;9;9
2018;477;393;68;39;29;10;9
2019;472;380;60;41;32;11;9
2020;449;335;62;38;40;12;9
2021;472;361;65;39;38;14;10
2022;454;279;50;49;39;18;10
2023;440;320;59;31;51;21;10
2024;442;362;75;20;48;23;10
"""
        df = pd.read_csv(StringIO(csv_text), sep=";")

        # Mapping couleurs
        colors = {
            "Nucléaire": "#FFE18B",
            "Hydraulique": "#2071B2",
            "Fossile":     "#313334",
            "Éolien":      "#8DCDBF",
            "Solaire":     "#F4902E",
            "Autre":       "#14682D",
        }

        filieres = {
            "nucleaire": "Nucléaire",
            "hydraulique": "Hydraulique",
            "fossile": "Fossile",
            "eolien": "Éolien",
            "solaire": "Solaire",
            "autre": "Autre",
        }

        df_long = (
            df.melt(id_vars=["year", "conso"],
                    value_vars=list(filieres.keys()),
                    var_name="filiere", value_name="production")
              .assign(filiere=lambda d: d["filiere"].map(filieres))
        )

        # Thème clair/sombre
        dark = _is_dark(input)
        font_color = "#F8FAFC" if dark else "#0B162C"
        grid_color = "rgba(203,213,225,.26)" if dark else "rgba(15,23,42,.08)"
        paper_bg   = "rgba(0,0,0,0)"
        plot_bg    = "rgba(0,0,0,0)"

        fig = go.Figure()

        # Aires empilées par filière
        for f in colors:
            dff = df_long[df_long["filiere"] == f]
            fig.add_trace(
                go.Scatter(
                    x=dff["year"], y=dff["production"],
                    mode="none", stackgroup="one", fill="tonexty",
                    name=f, fillcolor=colors[f],
                    hovertemplate=f"<b>{f}</b><br>Année: %{{x}}<br>Production: %{{y:.1f}} TWh<extra></extra>",
                )
            )

        # Courbe de consommation
        fig.add_trace(
            go.Scatter(
                x=df["year"], y=df["conso"], mode="lines",
                name="Consommation", line=dict(color="red", width=3, dash="dash"),
                hovertemplate="<b>Consommation</b><br>Année: %{{x}}<br>%{{y:.1f}} TWh<extra></extra>",
            )
        )

        # Mise en forme 
        fig.update_layout(
            title=None, 
            xaxis=dict(
                title=dict(text="Année", font=dict(size=14, color=font_color)),
                tickfont=dict(size=12, color=font_color),
                gridcolor=grid_color,
                zerolinecolor=grid_color,
                ),
            yaxis=dict(
                title=dict(text="TWh", font=dict(size=14, color=font_color)),
                tickfont=dict(size=12, color=font_color),
                gridcolor=grid_color,
                zerolinecolor=grid_color,
                ),
            legend=dict(
                orientation="v",
                x=1.01, y=0.98, xanchor="left",
                font=dict(size=12, color=font_color)
                ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=48, r=36, t=8, b=36),   
            font=dict(color=font_color, family="Poppins, Arial, sans-serif")
            )

        return fig
