# server.py — Leaflet: choroplèthe (polygones YlOrRd) + bulles violettes (taille = nb DC)
from __future__ import annotations

from pathlib import Path
import json

from shiny import App
import shinywidgets as sw

import pandas as pd
import numpy as np
import plotly.express as px
from shapely.geometry import shape  # pip install shapely

from ui import app_ui

# -------- Fichiers --------
DATA = Path(__file__).parent / "data"
geo_path = DATA / "europe_map.geojson"
if not geo_path.exists():
    alt = DATA / "europe_maap.geojson"
    if alt.exists():
        geo_path = alt

with open(geo_path, "r", encoding="utf-8") as f:
    gj = json.load(f)

# -------- Helpers --------
def _norm(s: str) -> str:
    return (
        str(s).lower()
        .replace(" ", "").replace("-", "").replace(".", "")
        .replace("_", "").replace("\u00a0", "")
    )

def pick_value_key(props0: dict) -> str | None:
    # clé qui porte "DC par million" dans le GeoJSON
    for k in ("dc_per_million", "dc_per_million_hab", "dcpm"):
        if k in props0:
            return k
    wanted = {"dcpermillion", "dcpm", "dcpermillionhab"}
    for k in props0:
        if _norm(k) in wanted:
            return k
    for k in props0:
        nk = _norm(k)
        if ("dc" in nk) and ("million" in nk):
            return k
    return None

# -------- Extraire les données utiles + centroïdes --------
feats = gj.get("features", [])
props0 = (feats[0].get("properties", {}) if feats else {}) or {}
val_key = pick_value_key(props0) or "dc_per_million"  # fallback

rows = []
for ft in feats:
    p = ft.get("properties", {}) or {}
    g = ft.get("geometry")

    # centroïde robuste (representative_point)
    try:
        pt = shape(g).representative_point() if g else None
        lon, lat = (float(pt.x), float(pt.y)) if pt else (np.nan, np.nan)
    except Exception:
        lon, lat = np.nan, np.nan

    rows.append(
        {
            "name": p.get("name") or p.get("NAME"),
            "nb_dc": p.get("nb_dc") or p.get("dc_count") or p.get("nb"),
            "pop": p.get("pop") or p.get("population"),
            "dcpm": p.get(val_key),  # DC / million
            "lon": lon,
            "lat": lat,
        }
    )

eu = pd.DataFrame(rows)
eu["nb_dc"] = pd.to_numeric(eu["nb_dc"], errors="coerce")
eu["pop"]   = pd.to_numeric(eu["pop"],   errors="coerce")
eu["dcpm"]  = pd.to_numeric(eu["dcpm"],  errors="coerce")

# Taille des bulles (entier)
nb_max = float(eu["nb_dc"].max(skipna=True)) if eu["nb_dc"].notna().any() else 1.0
def _radius(n) -> int:
    if not np.isfinite(n) or n <= 0:
        return 6
    return int(round(6 + 22 * np.sqrt(n / nb_max)))
eu["radius"] = eu["nb_dc"].apply(_radius)

# Part (%) pour barplot
total = float(eu["nb_dc"].sum(skipna=True)) if eu["nb_dc"].notna().any() else 0.0
eu["Share"] = np.where(eu["nb_dc"].notna() & (total > 0), (eu["nb_dc"] / total) * 100.0, np.nan)

# ---------- Couleurs ----------
# Palette choroplèthe jaune -> rouge (YlOrRd-like)
YLORRD = ["#FFF3B0", "#FFE08A", "#FFC15E", "#FF9C47", "#F66D44", "#D62F27"]
# Bulles UNIQUES (plus de dégradé)
BUBBLE_FILL = "#5B21B6"     # violet
BUBBLE_STROKE = "#FFFFFF"

def color_from_dcpm_discrete(x: float, vmin: float, vmax: float) -> str:
    """Retourne une couleur discrète YlOrRd selon la valeur normalisée entre vmin et vmax."""
    try:
        xv = float(x)
    except Exception:
        return "#f2f3f5"
    if not np.isfinite(xv):
        return "#f2f3f5"
    if vmax <= vmin:
        return YLORRD[-1]
    t = (xv - vmin) / (vmax - vmin)
    t = min(max(t, 0.0), 1.0)
    idx = int(np.floor(t * (len(YLORRD) - 1)))
    return YLORRD[idx]

# =========================
#   SERVER
# =========================
def server(input, output, session):

    @output
    @sw.render_widget
    def eu_map():
        try:
            from ipyleaflet import (
                Map, GeoJSON, CircleMarker, Popup,
                LayersControl, WidgetControl, basemaps, basemap_to_tiles
            )
            import ipywidgets as widgets
        except Exception:
            # message clair si ipyleaflet/ipywidgets absents
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.update_layout(
                annotations=[dict(
                    x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
                    text="Installe ipyleaflet & ipywidgets :<br><code>pip install ipyleaflet ipywidgets</code>",
                    font=dict(size=16)
                )],
                height=420, margin=dict(l=0, r=0, t=0, b=0)
            )
            return fig

        # plage couleurs pour DC / million
        v = eu["dcpm"].dropna()
        vmin = float(np.percentile(v, 5)) if len(v) else 0.0
        vmax = float(np.percentile(v, 95)) if len(v) else 1.0

        # carte de base
        m = Map(center=(54, 15), zoom=3, scroll_wheel_zoom=True)
        m.layers = ()
        m.add_layer(basemap_to_tiles(basemaps.CartoDB.Positron))

        # === 1) Choroplèthe (polygones) SOUS les bulles ===
        def style_callback(feature, **kwargs):
            p = feature.get("properties", {}) or {}
            try:
                val = float(p.get("dc_per_million") if "dc_per_million" in p else p.get("dcpm"))
            except Exception:
                val = float("nan")
            return {
                "fillColor":   color_from_dcpm_discrete(val, vmin, vmax),
                "color":       "#ffffff",   # contour
                "weight":      1,           # int !
                "fillOpacity": 0.55,
            }

        default_style = {"color": "#ffffff", "weight": 1, "fillOpacity": 0.55}
        hover_style   = {"weight": 2, "color": "#666666", "fillOpacity": 0.65}

        geo_layer = GeoJSON(
            data=gj,
            style=default_style,
            style_callback=style_callback,  # ✅ choroplèthe YlOrRd
            hover_style=hover_style,
            name="Choroplèthe DC/million",
        )
        m.add_layer(geo_layer)

        # === 2) Bulles proportionnelles (nb total de DC) — COULEUR FIXE ===
        df = eu.dropna(subset=["lat", "lon"]).copy()
        for _, row in df.iterrows():
            cm = CircleMarker(
                location=(float(row["lat"]), float(row["lon"])),
                radius=int(row["radius"]),   # int requis
                color=BUBBLE_STROKE,
                fill_color=BUBBLE_FILL,    
                fill_opacity=0.60,
                opacity=0.9,
                weight=1,                    # int requis
            )
            name = row.get("name") or "—"
            nb   = "—" if not np.isfinite(row.get("nb_dc", np.nan)) else f"{int(row['nb_dc']):,}".replace(",", " ")
            pop  = "—" if not np.isfinite(row.get("pop",   np.nan)) else f"{int(row['pop']):,}".replace(",", " ")
            dcpm = "—" if not np.isfinite(row.get("dcpm",  np.nan)) else f"{row['dcpm']:.2f}"
            html = widgets.HTML(f"<b>{name}</b><br/>DC : {nb}<br/>Population : {pop}<br/>DC / million : {dcpm}")
            cm.popup = Popup(child=html, max_width=250)
            m.add_layer(cm)

        # Légende
        legend = widgets.HTML(
            value=(
                "<div style='background:#fff;padding:8px 10px;border-radius:8px;"
                "box-shadow:0 2px 8px rgba(0,0,0,.15);font:13px/1.3 system-ui;'>"
                "<b>Couleur</b> = DC / million<br>"
                "<div style='display:flex;align-items:center;gap:6px;margin-top:6px'>"
                f"<span style='display:inline-block;width:16px;height:12px;background:{YLORRD[0]};border:1px solid #ddd'></span>"
                "<span style='opacity:.8'>faible</span>"
                "<span style='flex:1 1 auto;border-top:1px solid #ddd;margin:0 6px'></span>"
                f"<span style='display:inline-block;width:16px;height:12px;background:{YLORRD[-1]};border:1px solid #ddd'></span>"
                "<span style='opacity:.8'>élevé</span>"
                "</div>"
                f"<div style='margin-top:6px'><b>Taille</b> = nb total de DC &nbsp; "
                f"<span style='display:inline-block;width:12px;height:12px;background:{BUBBLE_FILL};"
                "border:1px solid #fff;border-radius:50%;vertical-align:middle'></span></div>"
                "</div>"
            )
        )
        from ipyleaflet import WidgetControl, LayersControl
        m.add_control(WidgetControl(widget=legend, position="bottomright"))
        m.add_control(LayersControl(position="topright"))
        return m

    # ---- barplot identique ----
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

    # ---- mini graphique identique ----
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

# App
app = App(app_ui, server)
