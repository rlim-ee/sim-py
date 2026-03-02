from __future__ import annotations

from shiny import render, reactive, ui
import shinywidgets as sw

import pandas as pd
import geopandas as gpd
import folium
import plotly.graph_objects as go
import json
from pathlib import Path
import numpy as np
import branca

# ---------- Utils ----------
def _is_dark(input) -> bool:
    try:
        dm = getattr(input, "darkmode", None)
        return bool(dm()) if callable(dm) else False
    except Exception:
        return False


def _get_region(input) -> str:
    for attr in ("geo_select", "fr_region"):
        try:
            fn = getattr(input, attr, None)
            if callable(fn):
                val = fn()
                if val:
                    return val
        except Exception:
            pass
    return "France"


PIE_FIELDS_TS = ["nuc", "hyd", "fos", "eol", "sol", "autre"]
PIE_LABELS_FR = ["Nucléaire", "Hydraulique", "Fossile", "Éolien", "Solaire", "Autre"]
PIE_COLOR_MAP = {
    "Nucléaire": "#FFE18B",
    "Hydraulique": "#2071B2",
    "Fossile": "#313334",
    "Éolien": "#8DCDBF",
    "Solaire": "#F4902E",
    "Autre": "#14682D",
}

# ---------- Chargement CSV ----------
def _load_timeseries_df(app_dir: Path) -> pd.DataFrame:
    path = app_dir / "www" / "data" / "data_energie_region.csv"

    df = pd.read_csv(path, sep=";")

    # Typage
    df["year"] = df["year"].astype(int)
    num_cols = ["conso", *PIE_FIELDS_TS]
    df[num_cols] = df[num_cols].astype(float)

    # Agrégats
    df["prod_tot"] = df[PIE_FIELDS_TS].sum(axis=1)
    df["balance"] = df["prod_tot"] - df["conso"]

    return df


# ---------- Carte (choroplèthe solde) ----------
def _build_balance_choropleth_html_from_base(
    gjson_base: dict, df_year: pd.DataFrame, dark: bool
) -> str:

    sub = df_year[df_year["regions"] != "France"]
    mvals = sub.set_index("regions")[["conso", "prod_tot", "balance"]].to_dict("index")

    if len(mvals):
        vmin = float(min(v["balance"] for v in mvals.values()))
        vmax = float(max(v["balance"] for v in mvals.values()))
    else:
        vmin, vmax = -1.0, 1.0

    vmax = max(vmax, 0.1)
    vmin = min(vmin, -0.1)

    cmap = branca.colormap.LinearColormap(
        colors=["#DC2626", "#F3F4F6", "#16A34A"],
        vmin=vmin,
        vmax=vmax,
    )
    cmap.caption = "Solde (TWh)"

    def fmt(x):
        try:
            return f"{float(x):,.1f}".replace(",", " ")
        except Exception:
            return "0,0"

    features = []
    for feat in gjson_base["features"]:
        nom = feat["properties"].get("NOM")
        vals = mvals.get(nom, {"conso": 0.0, "prod_tot": 0.0, "balance": 0.0})

        props = {
            "NOM": nom,
            "conso": float(vals["conso"]),
            "prod_tot": float(vals["prod_tot"]),
            "balance": float(vals["balance"]),
            "prod_txt": fmt(vals["prod_tot"]),
            "conso_txt": fmt(vals["conso"]),
            "balance_txt": fmt(vals["balance"]),
        }

        features.append(
            {"type": "Feature", "geometry": feat["geometry"], "properties": props}
        )

    gjson = {"type": "FeatureCollection", "features": features}

    tiles = "cartodbdark_matter" if dark else "cartodbpositron"
    contour_color = "#FFFFFF"
    highlight_color = "#E2E8F0" if dark else "#111827"

    m = folium.Map(
        location=[46.8, 2.5],
        zoom_start=5,
        tiles=tiles,
        control_scale=True,
        width="100%",
    )

    def _style_fn(feat):
        val = feat["properties"].get("balance", 0.0)
        return {
            "fillColor": cmap(val),
            "color": contour_color,
            "weight": 1,
            "fillOpacity": 0.6 if dark else 0.7,
        }

    folium.GeoJson(
        data=gjson,
        name="Régions",
        style_function=_style_fn,
        highlight_function=lambda feat: {
            "weight": 2,
            "color": highlight_color,
            "fillOpacity": 0.85,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=["NOM", "prod_txt", "conso_txt", "balance_txt"],
            aliases=[
                "Région",
                "Production (TWh)",
                "Consommation (TWh)",
                "Solde (TWh)",
            ],
            localize=True,
            sticky=False,
            labels=True,
        ),
    ).add_to(m)

    cmap.add_to(m)
    return m._repr_html_()


# ---------- Chargement + préparation ----------
def _load_data_prepared(app_dir: Path):
    geo_path = app_dir / "www" / "data" / "regions_simplified.geojson"

    gdf = gpd.read_file(geo_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    try:
        gdf2 = gdf.to_crs(3857).copy()
        gdf2["geometry"] = gdf2.geometry.simplify(2000, preserve_topology=True)
        gdf = gdf2.to_crs(4326)
    except Exception:
        pass

    gjson_base = json.loads(gdf[["NOM", "geometry"]].to_json())

    df_ts = _load_timeseries_df(app_dir)

    regions = sorted([r for r in df_ts["regions"].unique() if r != "France"])
    years = sorted(df_ts["year"].unique())

    fr_by_year = (
        df_ts[df_ts["regions"] == "France"]
        .set_index("year")[["conso", *PIE_FIELDS_TS, "prod_tot", "balance"]]
    )

    filieres_map = {
        "nuc": "Nucléaire",
        "hyd": "Hydraulique",
        "fos": "Fossile",
        "eol": "Éolien",
        "sol": "Solaire",
        "autre": "Autre",
    }

    long_by_region = {}
    for reg in ["France"] + regions:
        sub = df_ts[df_ts["regions"] == reg].copy().sort_values("year")
        long_by_region[reg] = (
            sub.melt(
                id_vars=["year", "conso"],
                value_vars=list(filieres_map.keys()),
                var_name="filiere",
                value_name="production",
            )
            .assign(filiere=lambda x: x["filiere"].map(filieres_map))
        )

    return {
        "gjson_base": gjson_base,
        "regions": regions,
        "years": years,
        "ts": df_ts,
        "fr_by_year": fr_by_year,
        "long_by_region": long_by_region,
    }


# ---------- SERVER ----------
def server(input, output, session, app_dir: Path):
    _data_cache = reactive.Value(None)

    @reactive.calc
    def data():
        obj = _data_cache.get()
        if obj is None:
            obj = _load_data_prepared(app_dir)
            _data_cache.set(obj)
        return obj

    @reactive.effect
    def _init_selects():
        d = data()
        choices = ["France"] + d["regions"]
        try:
            ui.update_select("geo_select", choices=choices, selected="France")
        except Exception:
            ui.update_select("fr_region", choices=choices, selected="France")

    # ---------------- Carte ----------------
    @output
    @render.ui
    def fr_map():
        d = data()
        year = int(input.year())
        dark = _is_dark(input)
        df_year = d["ts"][d["ts"]["year"] == year]
        html = _build_balance_choropleth_html_from_base(
            d["gjson_base"], df_year, dark
        )
        return ui.HTML(html)

    # ---------------- Camembert ----------------
    @output
    @sw.render_widget
    def prod_pie():
        d = data()
        region = _get_region(input)
        year = int(input.year())
        dark = _is_dark(input)

        if region == "France":
            row = d["fr_by_year"].loc[year]
            values = [row[k] for k in PIE_FIELDS_TS]
        else:
            row = d["ts"][(d["ts"]["regions"] == region) & (d["ts"]["year"] == year)]
            values = [row.iloc[0][k] if not row.empty else 0 for k in PIE_FIELDS_TS]

        font_color = "#F8FAFC" if dark else "#0B162C"

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=PIE_LABELS_FR,
                    values=values,
                    hole=0.15,
                    marker=dict(colors=[PIE_COLOR_MAP[l] for l in PIE_LABELS_FR]),
                    textinfo="percent+label",
                    textfont=dict(color=font_color),
                    hovertemplate="<b>%{label}</b><br>%{value:.1f} TWh<br>%{percent}<extra></extra>",
                )
            ]
        )

        fig.update_layout(
            height=340,
            font=dict(color=font_color, family="Poppins, Arial, sans-serif"),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(
                orientation="h",
                y=-0.15,
                x=0.5,
                xanchor="center",
                font=dict(color=font_color)
            )
        )

        return fig

    # ---------------- Évolution ----------------
    @output
    @sw.render_widget
    def area_chart():
        d = data()
        region = _get_region(input)
        year_sel = int(input.year())
        dark = _is_dark(input)
        key = (region, year_sel, dark)

        if not hasattr(area_chart, "_cache"):
            area_chart._cache = {}
        cache = area_chart._cache
        if key in cache:
            return cache[key]

        df_long = d["long_by_region"].get(region)
        if df_long is None:
            df = d["ts"]
            sub = df[df["regions"] == region].copy()
            sub = sub[(sub["year"] >= 2014) & (sub["year"] <= 2024)].sort_values("year")
            filieres_map = {
                "nuc": "Nucléaire",
                "hyd": "Hydraulique",
                "fos": "Fossile",
                "eol": "Éolien",
                "sol": "Solaire",
                "autre": "Autre",
            }
            df_long = (
                sub.melt(
                    id_vars=["year", "conso"],
                    value_vars=list(filieres_map.keys()),
                    var_name="filiere",
                    value_name="production",
                ).assign(filiere=lambda x: x["filiere"].map(filieres_map))
            )

        df_conso = (
            d["ts"][d["ts"]["regions"] == region].copy()
            if region != "France"
            else d["ts"][d["ts"]["regions"] == "France"].copy()
        )
        df_conso = df_conso[(df_conso["year"] >= 2014) & (df_conso["year"] <= 2024)].sort_values(
            "year"
        )

        colors = {
            "Nucléaire": "#FFE18B",
            "Hydraulique": "#2071B2",
            "Fossile": "#313334",
            "Éolien": "#8DCDBF",
            "Solaire": "#F4902E",
            "Autre": "#14682D",
        }
        font_color = "#F8FAFC" if dark else "#0B162C"
        grid_color = "rgba(203,213,225,.26)" if dark else "rgba(15,23,42,.08)"

        fig = go.Figure()
        for f in ["Nucléaire", "Hydraulique", "Fossile", "Éolien", "Solaire", "Autre"]:
            dff = df_long[df_long["filiere"] == f]
            fig.add_trace(
                go.Scatter(
                    x=dff["year"],
                    y=dff["production"],
                    mode="none",
                    stackgroup="one",
                    fill="tonexty",
                    name=f,
                    fillcolor=colors[f],
                    hovertemplate=f"<b>{f}</b><br>Année: %{{x}}<br>Prod: %{{y:.1f}} TWh<extra></extra>",
                )
            )

        fig.add_trace(
            go.Scatter(
                x=df_conso["year"],
                y=df_conso["conso"],
                mode="lines",
                name="Consommation",
                line=dict(color="red", width=3, dash="dash"),
                hovertemplate="<b>Consommation</b><br>Année: %{x}<br>%{y:.1f} TWh<extra></extra>",
            )
        )

        fig.add_vline(x=year_sel, line_width=2, line_dash="dot", line_color="red")
        fig.update_xaxes(rangeslider=dict(visible=False), range=[2014, 2024])
        fig.update_layout(
            autosize=True,
            height=250,
            xaxis=dict(
                title=dict(text="Année", font=dict(size=13, color=font_color)),
                tickfont=dict(size=11, color=font_color),
                gridcolor=grid_color,
                zerolinecolor=grid_color,
            ),
            yaxis=dict(
                title=dict(text="TWh", font=dict(size=13, color=font_color)),
                tickfont=dict(size=11, color=font_color),
                gridcolor=grid_color,
                zerolinecolor=grid_color,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                font=dict(size=11, color=font_color),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=36, r=16, t=8, b=8),
            font=dict(color=font_color, family="Poppins, Arial, sans-serif"),
        )

        cache[key] = fig
        return fig
# ---------------- Select Région ----------------
    @output
    @render.ui
    def region_selector():
        d = data()
        return ui.input_select(
            "fr_region", "Choisir une région", choices=["France"] + d["regions"], selected="France"
        )

    # ---------------- Titres dynamiques ----------------
    @output
    @render.text
    def map_title():
        y = 2024
        year_fn = getattr(input, "year", None)
        if callable(year_fn):
            try:
                y = int(year_fn())
            except Exception:
                pass
        return f"Solde énergétique par région — {y}"

    @output
    @render.text
    def area_title():
        region = _get_region(input)
        return f"Évolution de la production et de la consommation énergétique — {region} (2014–2024)"

    @output
    @render.text
    def pie_title():
        region = _get_region(input)
        year = int(input.year())
        return f"Production d’énergie par filière — {region} — {year}"