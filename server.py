# server.py — Leaflet robuste (choroplèthe YlOrRd discrète + bulles violettes)
from __future__ import annotations

from pathlib import Path
import json

from shiny import App
import shinywidgets as sw

import pandas as pd
import numpy as np
import plotly.express as px
from shapely.geometry import shape

from ui import app_ui

# ------------------ Chargement données ------------------
DATA = Path(__file__).parent / "data"
geo_path = DATA / "europe_map.geojson"
if not geo_path.exists():
    alt = DATA / "europe_maap.geojson"
    if alt.exists():
        geo_path = alt

with open(geo_path, "r", encoding="utf-8") as f:
    GJ = json.load(f)

def _norm(s: str) -> str:
    return (str(s).lower()
            .replace(" ", "").replace("-", "").replace(".", "")
            .replace("_", "").replace("\u00a0", ""))

def _pick_dcpm_key(props0: dict) -> str:
    for k in ("dc_per_million", "dc_per_million_hab", "dcpm"):
        if k in props0:
            return k
    wanted = {"dcpermillion", "dcpm", "dcpermillionhab"}
    for k in props0:
        if _norm(k) in wanted:
            return k
    for k in props0:
        nk = _norm(k)
        if "dc" in nk and "million" in nk:
            return k
    return "dc_per_million"

feats = GJ.get("features", [])
props0 = (feats[0].get("properties", {}) if feats else {}) or {}
VAL_KEY = _pick_dcpm_key(props0)

# tableau utile pour les bulles
rows = []
for ft in feats:
    p = ft.get("properties", {}) or {}
    g = ft.get("geometry")
    try:
        pt = shape(g).representative_point() if g else None
        lon, lat = (float(pt.x), float(pt.y)) if pt else (np.nan, np.nan)
    except Exception:
        lon, lat = np.nan, np.nan
    rows.append({
        "name": p.get("name") or p.get("NAME"),
        "nb_dc": p.get("nb_dc") or p.get("dc_count") or p.get("nb"),
        "pop":   p.get("pop")   or p.get("population"),
        "dcpm":  p.get(VAL_KEY),
        "lon":   lon, "lat":    lat,
    })

eu = pd.DataFrame(rows)
eu["nb_dc"] = pd.to_numeric(eu["nb_dc"], errors="coerce")
eu["pop"]   = pd.to_numeric(eu["pop"],   errors="coerce")
eu["dcpm"]  = pd.to_numeric(eu["dcpm"],  errors="coerce")

# rayon des bulles (entier)
nb_max = float(eu["nb_dc"].max(skipna=True)) if eu["nb_dc"].notna().any() else 1.0
def _radius(n) -> int:
    if not np.isfinite(n) or n <= 0:
        return 6
    return int(round(6 + 22 * np.sqrt(n / nb_max)))
eu["radius"] = eu["nb_dc"].apply(_radius)

# part (%) barplot
total = float(eu["nb_dc"].sum(skipna=True)) if eu["nb_dc"].notna().any() else 0.0
eu["Share"] = np.where(eu["nb_dc"].notna() & (total > 0),
                       (eu["nb_dc"] / total) * 100.0, np.nan)

# couleurs
YLORRD = ["#FFF3B0", "#FFE08A", "#FFC15E", "#FF9C47", "#F66D44", "#D62F27"]
BUBBLE_FILL = "#5B21B6"
BUBBLE_STROKE = "#FFFFFF"


# ------------------ SERVER ------------------
def server(input, output, session):

    @output
    @sw.render_widget
    def eu_map():
        try:
            from ipyleaflet import (
                Map, GeoJSON, CircleMarker, Popup, LayersControl, WidgetControl,
                basemaps, basemap_to_tiles
            )
            import ipywidgets as widgets
        except Exception:
            # Fallback si ipyleaflet/ipywidgets ne sont pas installés
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.update_layout(height=420, margin=dict(l=0, r=0, t=0, b=0),
                              annotations=[dict(x=0.5, y=0.5, xref="paper", yref="paper",
                                                showarrow=False,
                                                text="Installe ipyleaflet & ipywidgets<br><code>pip install ipyleaflet ipywidgets</code>")])
            return fig

        # --- deep-copy GeoJSON (et conversion full-Python) ---
        gj_copy = json.loads(json.dumps(GJ))  # évite tout état partagé / mutation

        # --- quelle clé identifie les features (ISO, name...) ---
        feats = gj_copy.get("features", [])
        p0 = (feats[0].get("properties", {}) if feats else {}) or {}
        for cand in ("color_code", "iso3", "ISO3", "country_id", "iso2", "ISO2", "name", "NAME"):
            if cand in p0:
                id_key = cand
                break
        else:
            id_key = "name"

        # --- on pré-calcule une couleur discrète YlOrRd PAR PAYS (quantiles) ---
        vals = []
        keys = []
        for ft in feats:
            pr = ft.get("properties", {}) or {}
            keys.append(str(pr.get(id_key, "")).strip())
            v = pr.get(VAL_KEY)
            try:
                vals.append(float(v))
            except (TypeError, ValueError):
                vals.append(np.nan)
        vals = np.array(vals, dtype=float)
        finite = vals[np.isfinite(vals)]
        if finite.size >= 3:
            edges = np.quantile(finite, [0, .2, .4, .6, .8, 1.0])
            edges = np.unique(edges)
            if edges.size < 2:
                edges = np.array([finite.min(), finite.max()+1e-9])
        elif finite.size == 2:
            edges = np.array([finite.min(), finite.max()])
        elif finite.size == 1:
            v = float(finite[0]); edges = np.array([v*0.9, v*1.1])
        else:
            edges = np.array([0.0, 1.0])
        K = max(1, len(edges) - 1)
        palette = YLORRD[:K] if K <= len(YLORRD) else [YLORRD[i*len(YLORRD)//K] for i in range(K)]

        def _class_color(x: float) -> str:
            try:
                xv = float(x)
            except Exception:
                return "#f2f3f5"
            if not np.isfinite(xv): return "#f2f3f5"
            idx = int(np.digitize([xv], edges, right=True)[0]) - 1
            idx = max(0, min(K-1, idx))
            return palette[idx]

        color_by_key = {k: _class_color(v) for k, v in zip(keys, vals)}

        # --- carte de base ---
        m = Map(center=(54, 15), zoom=3, scroll_wheel_zoom=True)
        m.layers = ()
        m.add_layer(basemap_to_tiles(basemaps.CartoDB.Positron))

        # --- choroplèthe (style_callback sans calcul, lookup couleur) ---
        def style_cb(feature, **kwargs):
            pr = feature.get("properties", {}) or {}
            k = str(pr.get(id_key, "")).strip()
            return {
                "fillColor":   color_by_key.get(k, "#f2f3f5"),
                "color":       "#ffffff",
                "weight":      1,          # int
                "fillOpacity": 0.55,
            }

        default_style = {"color": "#ffffff", "weight": 1, "fillOpacity": 0.55}
        hover_style   = {"weight": 2, "color": "#666666", "fillOpacity": 0.65}

        geo_layer = GeoJSON(
            data=gj_copy,
            style=default_style,
            style_callback=style_cb,
            hover_style=hover_style,
            name="Choroplèthe DC/million",
        )
        m.add_layer(geo_layer)

        # --- bulles violettes (taille = nb DC) ---
        df = eu.dropna(subset=["lat", "lon"]).copy()
        for _, row in df.iterrows():
            lat = float(row["lat"]); lon = float(row["lon"])
            rad = int(row["radius"]) if np.isfinite(row["radius"]) else 6
            cm = CircleMarker(
                location=(lat, lon),
                radius=rad,
                color=BUBBLE_STROKE,
                fill_color=BUBBLE_FILL,
                fill_opacity=0.60,
                opacity=0.9,
                weight=1,
            )
            name = row.get("name") or "—"
            nb   = "—" if not np.isfinite(row.get("nb_dc", np.nan)) else f"{int(row['nb_dc']):,}".replace(",", " ")
            pop  = "—" if not np.isfinite(row.get("pop",   np.nan)) else f"{int(row['pop']):,}".replace(",", " ")
            dcpm = "—" if not np.isfinite(row.get("dcpm",  np.nan)) else f"{row['dcpm']:.2f}"
            html = widgets.HTML(f"<b>{name}</b><br/>DC : {nb}<br/>Population : {pop}<br/>DC / million : {dcpm}")
            cm.popup = Popup(child=html, max_width=250)
            m.add_layer(cm)

        # légende
        import ipywidgets as widgets
        legend = widgets.HTML(
            value=(
                "<div style='background:#fff;padding:8px 10px;border-radius:8px;"
                "box-shadow:0 2px 8px rgba(0,0,0,.15);font:13px/1.3 system-ui;'>"
                "<b>Couleur</b> = DC / million (quantiles)<br>"
                "<div style='display:flex;align-items:center;gap:6px;margin-top:6px'>"
                f"<span style='display:inline-block;width:16px;height:12px;background:{palette[0]};border:1px solid #ddd'></span>"
                "<span style='opacity:.8'>faible</span>"
                "<span style='flex:1 1 auto;border-top:1px solid #ddd;margin:0 6px'></span>"
                f"<span style='display:inline-block;width:16px;height:12px;background:{palette[-1]};border:1px solid #ddd'></span>"
                "<span style='opacity:.8'>élevé</span>"
                "</div>"
                f"<div style='margin-top:6px'><b>Taille</b> = nb total de DC &nbsp; "
                f"<span style='display:inline-block;width:12px;height:12px;background:{BUBBLE_FILL};"
                "border:1px solid #fff;border-radius:50%;vertical-align:middle'></span></div>"
                "</div>"
            )
        )
        m.add_control(WidgetControl(widget=legend, position="bottomright"))
        m.add_control(LayersControl(position="topright"))
        return m

    # ----- barplot -----
    @output
    @sw.render_widget
    def barPlot_eu():
        df = eu.copy()
        df = df[df["Share"].notna()].sort_values("Share")
        fig = px.bar(
            df, x="Share", y="name",
            orientation="h",
            color="Share", color_continuous_scale="Plasma",
            labels={"Share": "", "name": ""},
        )
        fig.update_traces(hovertemplate="Pays : %{y}<br>Part : %{x:.2f}%<extra></extra>")
        fig.update_layout(
            coloraxis_showscale=False,
            xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#eaeef3"),
            yaxis=dict(showgrid=False),
            margin=dict(l=120, r=30, t=20, b=30),
            height=422,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

    # ----- mini bar -----
    @output
    @sw.render_widget
    def dc_demand_plot():
        df = pd.DataFrame({"Année": ["2024", "2035"], "TWh": [96, 236]})
        fig = px.bar(
            df, x="Année", y="TWh",
            color="Année", color_discrete_map={"2024": "#3B556D", "2035": "#5FC2BA"},
            text=df["TWh"].astype(str) + " TWh",
        )
        fig.update_traces(opacity=0.9, textposition="outside",
                          hovertemplate="Année : %{x}<br>Demande : %{y} TWh<extra></extra>")
        fig.update_layout(
            yaxis_title="Demande (TWh)", xaxis_title=None,
            margin=dict(l=40, r=20, t=10, b=40),
            height=420, showlegend=False,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        fig.update_yaxes(range=[0, float(df["TWh"].max()) * 1.25])
        return fig

app = App(app_ui, server)
