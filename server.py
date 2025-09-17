# server.py — DC en Europe à partir d'un europe_map.geojson
from __future__ import annotations

from pathlib import Path
import json

from shiny import App  # pas d'import 'output' ici
import shinywidgets as sw

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from shapely.geometry import shape  # pip install shapely

from ui import app_ui


DATA = (Path(__file__).parent / "data")

# GeoJSON (seul fichier utilisé)
geo_path = DATA / "europe_map.geojson"
if not geo_path.exists():
    alt = DATA / "europe_maap.geojson"  # si ton fichier a été mal orthographié
    if alt.exists():
        geo_path = alt

with open(geo_path, "r", encoding="utf-8") as f:
    gj = json.load(f)

# ---- GeoJSON -> DataFrame (props + centroïdes) ----
rows = []
for ft in gj.get("features", []):
    props = ft.get("properties", {}) or {}
    geom = ft.get("geometry")
    rows.append(
        {
            "name": props.get("name") or props.get("NAME") or props.get("country") or props.get("pays"),
            "iso3": props.get("color_code") or props.get("iso3") or props.get("ISO3"),
            "iso2": props.get("country_id") or props.get("iso2") or props.get("ISO2"),
            "nb_dc": props.get("nb_dc") or props.get("dc_count") or props.get("nb"),
            "pop": props.get("pop") or props.get("population"),
            "geometry": geom,
        }
    )

eu = pd.DataFrame(rows)
eu["nb_dc"] = pd.to_numeric(eu["nb_dc"], errors="coerce")
eu["pop"] = pd.to_numeric(eu["pop"], errors="coerce")

# métriques
eu["dc_per_million"] = eu["nb_dc"] / (eu["pop"] / 1_000_000)
total_dc = float(eu["nb_dc"].sum(skipna=True)) if eu["nb_dc"].notna().any() else 0.0
eu["Share"] = np.where(eu["nb_dc"].notna() & (total_dc > 0), (eu["nb_dc"] / total_dc) * 100.0, np.nan)
eu["radius"] = (np.sqrt(eu["nb_dc"].fillna(0.0)) * 4 + 4).clip(lower=0)

# centroïdes sûrs (representative_point)
def _rep_point_xy(g):
    if not g:
        return np.nan, np.nan
    try:
        pt = shape(g).representative_point()
        return float(pt.x), float(pt.y)
    except Exception:
        return np.nan, np.nan

eu[["lon", "lat"]] = eu["geometry"].apply(lambda g: pd.Series(_rep_point_xy(g)))


# =========================
#   SERVER (définit @output ICI)
# =========================
def server(input, output, session):

    @output
    @sw.render_widget
    def eu_map():
        df = eu.copy()

        # propriété identifiant les features dans TON geojson
        props0 = (gj.get("features") or [{}])[0].get("properties", {})
        for prop in ("color_code", "iso3", "ISO3", "country_id", "iso2", "ISO2", "name", "NAME"):
            if prop in props0:
                feature_prop = prop
                break
        else:
            feature_prop = "name"

        loc_col = {
            "color_code": "iso3", "iso3": "iso3", "ISO3": "iso3",
            "country_id": "iso2", "iso2": "iso2", "ISO2": "iso2",
            "name": "name", "NAME": "name"
        }[feature_prop]

        z = df["dc_per_million"].fillna(0.0)
        zmax = float(z.max()) if z.max() > 0 else 1.0

        fig = go.Figure()

        # Choroplèthe
        fig.add_trace(
            go.Choropleth(
                geojson=gj,
                featureidkey=f"properties.{feature_prop}",
                locations=df[loc_col],
                z=z,
                colorscale="Blues",
                zmin=0,
                zmax=zmax,
                marker_line_color="white",
                marker_line_width=0.6,
                colorbar_title="DC / million",
                customdata=np.stack([df["name"].fillna(""), z], axis=-1),
                hovertemplate="<b>%{customdata[0]}</b><br>DC / million : %{customdata[1]:.2f}<extra></extra>",
                name="",
            )
        )

        # Bulles proportionnelles (nombre total de DC)
        bubbles = df[df["nb_dc"].notna() & df["lat"].notna() & df["lon"].notna()].copy()
        if not bubbles.empty:
            bubbles["pop_fmt"] = bubbles["pop"].astype("Int64").map(lambda x: f"{x:,}".replace(",", " "))
            bubbles["nb_fmt"] = bubbles["nb_dc"].astype("Int64").map(lambda x: f"{x:,}".replace(",", " "))

            fig.add_trace(
                go.Scattergeo(
                    lon=bubbles["lon"],
                    lat=bubbles["lat"],
                    mode="markers",
                    marker=dict(
                        size=bubbles["radius"],
                        color="#1F6FEB",
                        opacity=0.65,
                        line=dict(width=1, color="white"),
                    ),
                    customdata=np.stack([bubbles["name"], bubbles["nb_fmt"], bubbles["pop_fmt"]], axis=-1),
                    hovertemplate="<b>%{customdata[0]}</b><br>DC : %{customdata[1]}<br>Population : %{customdata[2]}<extra></extra>",
                    showlegend=False,
                )
            )

        fig.update_geos(
            showcountries=True,
            countrycolor="white",
            showland=True,
            landcolor="#f0f2f5",
            projection_type="natural earth",
            fitbounds="locations",
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    @output
    @sw.render_widget
    def barPlot_eu():
        df = eu.copy()
        df = df[df["Share"].notna()].sort_values("Share")
        fig = px.bar(
            df,
            x="Share",
            y="name",
            orientation="h",
            color="Share",
            color_continuous_scale="Blues",
            labels={"Share": "", "name": ""},
        )
        fig.update_traces(hovertemplate="Pays : %{y}<br>Part : %{x:.2f}%<extra></extra>")
        fig.update_layout(
            coloraxis_showscale=False,
            xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#eaeef3"),
            yaxis=dict(showgrid=False),
            margin=dict(l=120, r=30, t=20, b=30),
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    x=0,
                    y=-0.2,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    text="Source : ICIS (DataCentreMap, Statista)",
                    font=dict(size=12, color="gray"),
                )
            ],
        )
        return fig

    @output
    @sw.render_widget
    def dc_demand_plot():
        df = pd.DataFrame({"Année": ["2024", "2035"], "TWh": [96, 236]})
        fig = px.bar(
            df,
            x="Année",
            y="TWh",
            color="Année",
            color_discrete_map={"2024": "#3B556D", "2035": "#5FC2BA"},
            text=df["TWh"].astype(str) + " TWh",
        )
        fig.update_traces(
            opacity=0.9,
            textposition="outside",
            hovertemplate="Année : %{x}<br>Demande : %{y} TWh<extra></extra>",
        )
        fig.update_layout(
            yaxis_title="Demande (TWh)",
            xaxis_title=None,
            margin=dict(l=40, r=20, t=10, b=40),
            height=420,
            showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_yaxes(range=[0, float(df["TWh"].max()) * 1.25])
        return fig


# App
app = App(app_ui, server)
