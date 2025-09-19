# server.py
from __future__ import annotations

from pathlib import Path
import json
import math
import unicodedata

import numpy as np
import pandas as pd
import plotly.express as px
from shapely.geometry import shape

from shiny import App
import shinywidgets as sw

from ui import app_ui

# -------------------------------------------------------------------
# Chemins et chargement GeoJSON
# -------------------------------------------------------------------
ROOT = Path(__file__).parent
DATA = ROOT / "data"

def read_geojson_from(cands: list[Path]) -> dict:
    for p in cands:
        if p.exists():
            with p.open("r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError(f"Aucun GeoJSON trouvé parmi : {cands}")

# Europe (inchangé)
EU_GJ = read_geojson_from([
    DATA / "europe_map.geojson",
    DATA / "europe_maap.geojson",
])

# France (regions.geojson fourni par toi)
FR_GJ = read_geojson_from([
    ROOT / "regions.geojson",
    DATA / "regions.geojson",
])

# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def slug(s: str) -> str:
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return (s.lower().replace("\u00a0", " ")
            .replace("-", " ").replace("_", " ").strip())

def ensure_feature_id(gj: dict, prefer: tuple[str, ...]) -> str:
    feats = gj.get("features", [])
    if not feats:
        return "id"
    props0 = feats[0].get("properties", {}) or {}
    key = None
    for k in (*prefer, "id", "ID"):
        if k in props0:
            key = k
            break
    if key is None:
        key = next(iter(props0.keys()), "id")
    for ft in feats:
        props = ft.get("properties", {}) or {}
        ft["id"] = str(props.get(key, "")).strip()
    return key

def read_csv_auto(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, sep=None, engine="python", encoding="utf-8")

def pick_first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None

# Palettes / couleurs
YLORRD = ["#FFF3B0", "#FFE08A", "#FFC15E", "#FF9C47", "#F66D44", "#D62F27"]
PURPLE = "#5B21B6"
WHITE = "#FFFFFF"

# -------------------------------------------------------------------
# DC Europe — prépa
# -------------------------------------------------------------------
EU_ID_KEY = ensure_feature_id(EU_GJ, ("name", "NAME", "iso3", "ISO3"))

def find_dcpm_key(props: dict) -> str:
    for k in ("dc_per_million", "dc_per_million_hab", "dcpm"):
        if k in props:
            return k
    for k in props:
        ks = slug(k).replace(" ", "")
        if "dc" in ks and "million" in ks:
            return k
    return "dc_per_million"

EU_VAL_KEY = find_dcpm_key((EU_GJ["features"][0].get("properties", {}) if EU_GJ.get("features") else {}) or {})

eu_rows = []
for ft in EU_GJ.get("features", []):
    p = ft.get("properties", {}) or {}
    g = ft.get("geometry")
    lon, lat = (np.nan, np.nan)
    try:
        if g:
            rp = shape(g).representative_point()
            lon, lat = float(rp.x), float(rp.y)
    except Exception:
        pass
    eu_rows.append({
        "id": ft.get("id", ""),
        "name": p.get("name") or p.get("NAME"),
        "nb_dc": p.get("nb_dc") or p.get("dc_count") or p.get("nb"),
        "pop": p.get("pop") or p.get("population"),
        "dcpm": p.get(EU_VAL_KEY),
        "lon": lon, "lat": lat
    })

eu_df = pd.DataFrame(eu_rows)
eu_df["nb_dc"] = pd.to_numeric(eu_df["nb_dc"], errors="coerce")
eu_df["pop"]   = pd.to_numeric(eu_df["pop"], errors="coerce")
eu_df["dcpm"]  = pd.to_numeric(eu_df["dcpm"], errors="coerce")

nb_max = float(eu_df["nb_dc"].max(skipna=True)) if eu_df["nb_dc"].notna().any() else 1.0
def bubble_radius(n) -> int:
    if not np.isfinite(n) or n <= 0:
        return 6
    return int(round(6 + 22 * math.sqrt(n / nb_max)))

eu_df["radius"] = eu_df["nb_dc"].apply(bubble_radius)
total_dc = float(eu_df["nb_dc"].sum(skipna=True)) if eu_df["nb_dc"].notna().any() else 0.0
eu_df["Share"] = np.where(eu_df["nb_dc"].notna() & (total_dc > 0),
                          (eu_df["nb_dc"] / total_dc) * 100.0, np.nan)

# -------------------------------------------------------------------
# Énergie France — table + id
# -------------------------------------------------------------------
FR_ID_KEY = ensure_feature_id(FR_GJ, ("NOM", "nom", "name", "NAME"))
FR_IDS = [ft.get("id", "") for ft in FR_GJ.get("features", [])]

FR_TABLE_PATH = pick_first_existing(
    [
        DATA / "fr_energy_regions.csv",
        DATA / "energie_fr_regions.csv",
        DATA / "energie_fr.csv",
        DATA / "energy_fr.csv",
        DATA / "fr_mix_regions.csv",
    ]
)

def load_fr_table() -> pd.DataFrame:
    if FR_TABLE_PATH is None:
        return pd.DataFrame({"Region": FR_IDS})
    df = read_csv_auto(FR_TABLE_PATH)

    region_cands = [c for c in df.columns if slug(c) in ("region", "région", "nom", "name")]
    key = region_cands[0] if region_cands else df.columns[0]

    df = df.copy()
    df["__region_key__"] = df[key].astype(str).str.strip()

    names_map = {}
    for r in df["__region_key__"]:
        r_slug = slug(r)
        hit = next((x for x in FR_IDS if x == r), None)
        if hit is None:
            hit = next((x for x in FR_IDS if slug(x) == r_slug), None)
        names_map[r] = hit if hit is not None else r

    df["Region"] = df["__region_key__"].map(names_map)
    df.drop(columns=["__region_key__"], inplace=True)

    filiere_alias = {
        "hydro": {"hydro", "hydraulique"},
        "nucleaire": {"nucleaire", "nucléaire", "nuke"},
        "eolien": {"eolien", "éolien", "wind"},
        "solaire": {"solaire", "pv", "photovoltaïque", "photovoltaique"},
        "gaz": {"gaz", "gas"},
        "bioenergies": {"bio", "bioenergie", "bioénergies", "biomasse"},
        "charbon": {"charbon", "coal"},
        "autres": {"autres", "autre", "others", "autresenr"},
    }
    def guess_tag(col: str) -> str | None:
        c = slug(col)
        for tag, aliases in filiere_alias.items():
            if c in aliases:
                return tag
        if "nucle" in c: return "nucleaire"
        if "eol" in c:   return "eolien"
        if "sol" in c or "pv" in c: return "solaire"
        if "hydro" in c: return "hydro"
        if "gaz" in c or "gas" in c: return "gaz"
        if "bio" in c:  return "bioenergies"
        if "charbon" in c or "coal" in c: return "charbon"
        if "autre" in c or "other" in c:  return "autres"
        return None

    value_cols = []
    tag_map: dict[str, list[str]] = {}
    for col in df.columns:
        if col == "Region": continue
        tag = guess_tag(col)
        if tag:
            value_cols.append(col)
            tag_map.setdefault(tag, []).append(col)

    total_col = next(
        (c for c in df.columns if slug(c) in ("total", "twh", "demande", "consommation", "conso", "total_twh")),
        None,
    )
    for c in value_cols + ([total_col] if total_col else []):
        if c: df[c] = pd.to_numeric(df[c], errors="coerce")

    for tag, cols in tag_map.items():
        df[f"F_{tag}"] = df[cols].sum(axis=1, skipna=True)

    if total_col is None:
        fcols = [c for c in df.columns if c.startswith("F_")]
        if fcols:
            df["Total_TWh"] = df[fcols].sum(axis=1, skipna=True)
        else:
            df["Total_TWh"] = np.nan
    else:
        df["Total_TWh"] = df[total_col]

    ren_cols = [c for c in ["F_hydro", "F_eolien", "F_solaire", "F_bioenergies"] if c in df.columns]
    if ren_cols:
        df["Ren_pct"] = np.where(df["Total_TWh"] > 0,
                                 (df[ren_cols].sum(axis=1, skipna=True) / df["Total_TWh"]) * 100.0,
                                 np.nan)
    else:
        df["Ren_pct"] = np.nan

    return df

FR_TAB = load_fr_table()

# -------------------------------------------------------------------
# Caches simples (évite le “clignotement”)
# -------------------------------------------------------------------
_EU_MAP = None
_FR_MAP = None
_FR_BIVAR = None

# -------------------------------------------------------------------
# Server
# -------------------------------------------------------------------
def server(input, output, session):

    @output
    @sw.render_widget
    def eu_map():
        try:
            from ipyleaflet import (
                Map, Choropleth, CircleMarker, LayersControl,
                basemap_to_tiles, basemaps, WidgetControl
            )
            from branca.colormap import linear
            import ipywidgets as W
        except Exception:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.update_layout(
                height=420, margin=dict(l=0, r=0, t=0, b=0),
                annotations=[dict(x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,
                                  text="Installe ipyleaflet & ipywidgets<br><code>pip install ipyleaflet ipywidgets</code>")]
            )
            return fig

        global _EU_MAP
        if _EU_MAP is None:
            m = Map(center=(54, 15), zoom=3, scroll_wheel_zoom=True)
            m.layers = ()
            m.add_layer(basemap_to_tiles(basemaps.CartoDB.Positron))

            # Choropleth DC/million avec key_on="id"
            vals = []
            choro = {}
            for ft in EU_GJ["features"]:
                fid = ft.get("id", "")
                v = ft.get("properties", {}).get(EU_VAL_KEY)
                try:
                    vv = float(v)
                except (TypeError, ValueError):
                    vv = np.nan
                choro[fid] = 0.0 if not np.isfinite(vv) else vv
                if np.isfinite(vv):
                    vals.append(vv)
            vmin = float(min(vals)) if vals else 0.0
            vmax = float(max(vals)) if vals else 1.0
            cmap = linear.YlOrRd_09.scale(vmin, vmax)
            ch_layer = Choropleth(
                geo_data=EU_GJ, choro_data=choro, key_on="id",
                colormap=cmap,
                style={"color":"#ffffff","weight":1,"fillOpacity":0.6},
                hover_style={"color":"#666666","weight":2,"fillOpacity":0.7},
                name="DC/million",
            )
            m.add_layer(ch_layer)

            # Bulles (nb DC)
            df = eu_df.dropna(subset=["lat","lon"]).copy()
            for _, r in df.iterrows():
                cm = CircleMarker(
                    location=(float(r["lat"]), float(r["lon"])),
                    radius=int(r["radius"]) if np.isfinite(r["radius"]) else 6,
                    color=WHITE, fill_color=PURPLE, fill_opacity=0.60,
                    opacity=0.9, weight=1,
                )
                name = r.get("name") or "—"
                nb   = "—" if not np.isfinite(r.get("nb_dc", np.nan)) else f"{int(r['nb_dc']):,}".replace(",", " ")
                pop  = "—" if not np.isfinite(r.get("pop",   np.nan)) else f"{int(r['pop']):,}".replace(",", " ")
                dcpm = "—" if not np.isfinite(r.get("dcpm",  np.nan)) else f"{r['dcpm']:.2f}"
                cm.popup = W.HTML(f"<b>{name}</b><br>DC : {nb}<br>Population : {pop}<br>DC / million : {dcpm}")
                m.add_layer(cm)

            legend = W.HTML(
                value=("<div style='background:#fff;padding:8px 10px;border-radius:8px;"
                       "box-shadow:0 2px 8px rgba(0,0,0,.15);font:13px/1.35 system-ui;'>"
                       "<b>Couleur</b> = DC / million<br>"
                       "<span style='opacity:.8'>Taille</span> = nb total de DC</div>")
            )
            m.add_control(WidgetControl(widget=legend, position="bottomright"))
            m.add_control(LayersControl(position="topright"))
            _EU_MAP = m
        return _EU_MAP

    @output
    @sw.render_widget
    def barPlot_eu():
        df = eu_df.copy()
        df = df[df["Share"].notna()].sort_values("Share")
        fig = px.bar(
            df, x="Share", y="name", orientation="h",
            color="Share", color_continuous_scale="Plasma",
            labels={"Share":"", "name":""}
        )
        fig.update_traces(hovertemplate="Pays : %{y}<br>Part : %{x:.2f}%<extra></extra>")
        fig.update_layout(
            coloraxis_showscale=False,
            xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#eaeef3"),
            yaxis=dict(showgrid=False),
            margin=dict(l=120, r=30, t=20, b=30),
            height=422,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        )
        return fig

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

    # ---------------- ÉNERGIE FRANCE ----------------
    def _fr_total_by_region() -> dict[str, float]:
        d = {}
        if "Region" not in FR_TAB.columns:
            return d
        for _, row in FR_TAB.iterrows():
            rid = str(row["Region"])
            val = row.get("Total_TWh", np.nan)
            try:
                d[rid] = float(val) if np.isfinite(float(val)) else 0.0
            except Exception:
                d[rid] = 0.0
        return d

    @output
    @sw.render_widget
    def map_fr():
        try:
            from ipyleaflet import (
                Map, Choropleth, LayersControl, basemap_to_tiles, basemaps, WidgetControl
            )
            from branca.colormap import linear
            import ipywidgets as W
        except Exception:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.update_layout(
                height=420, margin=dict(l=0, r=0, t=0, b=0),
                annotations=[dict(x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,
                                  text="Installe ipyleaflet & ipywidgets<br><code>pip install ipyleaflet ipywidgets</code>")]
            )
            return fig

        global _FR_MAP
        total_by_reg = _fr_total_by_region()
        choro = {}
        vals = []
        for ft in FR_GJ["features"]:
            fid = ft.get("id", "")
            v = float(total_by_reg.get(fid, 0.0))
            choro[fid] = v
            vals.append(v)

        if _FR_MAP is None:
            m = Map(center=(46.6, 2.2), zoom=5, scroll_wheel_zoom=True)
            m.layers = ()
            m.add_layer(basemap_to_tiles(basemaps.CartoDB.Positron))

            vmin = float(min(vals)) if vals else 0.0
            vmax = float(max(vals)) if vals else 1.0
            if vmin == vmax:
                vmax = vmin + 1.0
            cmap = linear.Blues_09.scale(vmin, vmax)

            ch_layer = Choropleth(
                geo_data=FR_GJ, choro_data=choro, key_on="id",
                colormap=cmap,
                style={"color":"#ffffff","weight":1,"fillOpacity":0.65},
                hover_style={"color":"#666666","weight":2,"fillOpacity":0.75},
                name="Total (TWh)",
            )
            m.add_layer(ch_layer)

            legend = W.HTML(
                value=("<div style='background:#fff;padding:8px 10px;border-radius:8px;"
                       "box-shadow:0 2px 8px rgba(0,0,0,.15);font:13px/1.35 system-ui;'>"
                       "<b>Couleur</b> = Total annuel (TWh)</div>")
            )
            m.add_control(WidgetControl(widget=legend, position="bottomright"))
            m.add_control(LayersControl(position="topright"))
            _FR_MAP = m
        else:
            from ipyleaflet import Choropleth
            ch_layer = next((ly for ly in _FR_MAP.layers if isinstance(ly, Choropleth)), None)
            if ch_layer is not None:
                ch_layer.choro_data = choro
        return _FR_MAP

    def _fr_bivar_classes() -> dict[str, int]:
        x = []  # Total_TWh
        y = []  # Ren_pct
        ids = []
        for _, row in FR_TAB.iterrows():
            ids.append(str(row.get("Region", "")))
            xv = row.get("Total_TWh", np.nan)
            yv = row.get("Ren_pct", np.nan)
            try: xv = float(xv)
            except Exception: xv = np.nan
            try: yv = float(yv)
            except Exception: yv = np.nan
            x.append(xv); y.append(yv)
        x = np.array(x, float); y = np.array(y, float)

        def qbreak(v: np.ndarray) -> np.ndarray:
            v = v[np.isfinite(v)]
            if v.size == 0:
                return np.array([0.0, 1/3, 2/3, 1.0])
            qs = np.quantile(v, [0.0, 1/3, 2/3, 1.0])
            qs = np.unique(qs)
            if qs.size < 4:
                vmin, vmax = (float(np.nanmin(v)), float(np.nanmax(v)))
                if vmax <= vmin: vmax = vmin + 1.0
                qs = np.array([vmin, vmin+(vmax-vmin)/3, vmin+2*(vmax-vmin)/3, vmax])
            return qs

        bx = qbreak(x); by = qbreak(y)
        def to_bin(v, brks):
            idx = int(np.digitize([v], brks, right=True)[0]) - 1
            return max(0, min(2, idx))

        classes = {}
        for rid, xv, yv in zip(ids, x, y):
            if not np.isfinite(xv) or not np.isfinite(yv):
                classes[rid] = 1
            else:
                i = to_bin(xv, bx); j = to_bin(yv, by)
                classes[rid] = 1 + i*3 + j  # 1..9
        return classes

    @output
    @sw.render_widget
    def map_fr_bivar():
        try:
            from ipyleaflet import (
                Map, Choropleth, LayersControl, basemap_to_tiles, basemaps, WidgetControl
            )
            from branca.colormap import StepColormap
            import ipywidgets as W
        except Exception:
            import plotly.graph_objects as go
            fig = go.Figure()
            fig.update_layout(
                height=420, margin=dict(l=0, r=0, t=0, b=0),
                annotations=[dict(x=0.5,y=0.5,xref="paper",yref="paper",showarrow=False,
                                  text="Installe ipyleaflet & ipywidgets<br><code>pip install ipyleaflet ipywidgets</code>")]
            )
            return fig

        global _FR_BIVAR
        classes = _fr_bivar_classes()

        colors = [
            "#e8e8e8","#b5c0da","#6c83b5",
            "#b8d6be","#90b2b3","#567994",
            "#73ae80","#5a9178","#2a5a5b",
        ]
        idx = list(range(1, 10))
        cmap = StepColormap(colors=colors, index=idx, vmin=1, vmax=9)

        choro = {}
        for ft in FR_GJ["features"]:
            fid = ft.get("id", "")
            choro[fid] = int(classes.get(fid, 1))

        if _FR_BIVAR is None:
            m = Map(center=(46.6, 2.2), zoom=5, scroll_wheel_zoom=True)
            m.layers = ()
            m.add_layer(basemap_to_tiles(basemaps.CartoDB.Positron))

            ch_layer = Choropleth(
                geo_data=FR_GJ, choro_data=choro, key_on="id",
                colormap=cmap,
                style={"color":"#ffffff","weight":1,"fillOpacity":0.9},
                hover_style={"color":"#333333","weight":2,"fillOpacity":0.95},
                name="Bivariée (Total vs %EnR)",
            )
            m.add_layer(ch_layer)

            legend = W.HTML(
                value=("<div style='background:#fff;padding:8px 10px;border-radius:8px;"
                       "box-shadow:0 2px 8px rgba(0,0,0,.15);font:13px/1.35 system-ui;'>"
                       "<b>Bivariée</b><br><small>→ Total (TWh) &nbsp; ↑ Part EnR (%)</small></div>")
            )
            m.add_control(WidgetControl(widget=legend, position="bottomright"))
            m.add_control(LayersControl(position="topright"))
            _FR_BIVAR = m
        else:
            from ipyleaflet import Choropleth
            ch_layer = next((ly for ly in _FR_BIVAR.layers if isinstance(ly, Choropleth)), None)
            if ch_layer is not None:
                ch_layer.choro_data = choro
        return _FR_BIVAR

    def _mix_for_region(region: str) -> pd.Series:
        df = FR_TAB.copy()
        if "Region" in df.columns and region in set(df["Region"].astype(str)):
            sub = df[df["Region"].astype(str) == region]
        else:
            sub = df
        fcols = [c for c in df.columns if c.startswith("F_")]
        if not fcols:
            return pd.Series(dtype=float)
        s = sub[fcols].sum(numeric_only=True)
        s = s[s > 0]
        s.index = [c.replace("F_", "").capitalize() for c in s.index]
        return s.sort_values(ascending=False)

    @output
    @sw.render_widget
    def fr_pie():
        region = getattr(input, "region_fr", lambda: "France")()
        if not region or region not in set(FR_TAB.get("Region", [])):
            region = "France"
        s = _mix_for_region(region)
        if s.empty:
            fig = px.pie(values=[1], names=["Aucune donnée"], hole=0.4)
            fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
            return fig
        fig = px.pie(values=s.values, names=s.index, hole=0.4, title=f"Mix électrique – {region}")
        fig.update_traces(textposition="inside", textinfo="percent+label")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20),
                          showlegend=True, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    @output
    @sw.render_widget
    def fr_radar():
        region = getattr(input, "region_fr", lambda: "France")()
        s_reg = _mix_for_region(region if region else "France")
        s_fr  = _mix_for_region("France")
        if s_fr.empty and s_reg.empty:
            fig = px.line_polar(r=[1], theta=["—"], line_close=True)
            fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20))
            return fig

        def to_pct(s: pd.Series) -> pd.Series:
            tot = float(s.sum()) if s.size else 0.0
            return (s / tot * 100.0) if tot > 0 else s * 0.0

        s_reg_p = to_pct(s_reg); s_fr_p = to_pct(s_fr)
        axes = sorted(set(s_reg_p.index) | set(s_fr_p.index))
        r1 = [s_reg_p.get(a, 0.0) for a in axes]
        r2 = [s_fr_p.get(a, 0.0) for a in axes]

        df = pd.DataFrame({"Filière": axes + axes,
                           "Part": r1 + r2,
                           "Série": ([region]*len(axes)) + (["France"]*len(axes))})
        fig = px.line_polar(df, r="Part", theta="Filière", color="Série", line_close=True)
        fig.update_traces(fill="toself")
        fig.update_layout(height=420, margin=dict(l=20, r=20, t=20, b=20),
                          polar=dict(radialaxis=dict(ticksuffix="%")),
                          legend=dict(orientation="h", yanchor="bottom", y=-0.1),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig

    @output
    @sw.render_widget
    def fr_evo_filiere():
        evo_path = pick_first_existing(
            [
                DATA / "fr_evolution_filiere.csv",
                DATA / "evolution_production_filiere.csv",
                DATA / "fr_evo_filiere.csv",
                DATA / "energie_fr_evo.csv",
            ]
        )
        if evo_path is None:
            df = pd.DataFrame(
                {"Annee":[2020,2020,2020,2024,2024,2024],
                 "Filiere":["Nucléaire","Éolien","Solaire","Nucléaire","Éolien","Solaire"],
                 "TWh":[335,40,13,320,55,22]}
            )
        else:
            df = read_csv_auto(evo_path)
            cols = {slug(c): c for c in df.columns}
            col_year = cols.get("annee") or cols.get("année") or cols.get("year")
            col_fil  = cols.get("filiere") or cols.get("filière") or cols.get("fil")
            col_val  = cols.get("twh") or cols.get("valeur") or cols.get("value")
            if not (col_year and col_fil and col_val):
                col_year = col_year or next((c for c in df.columns if "ann" in slug(c) or "year" in slug(c)), df.columns[0])
                col_fil  = col_fil  or next((c for c in df.columns if "fil" in slug(c)), df.columns[1])
                col_val  = col_val  or next((c for c in df.columns if any(k in slug(c) for k in ["twh","val","prod"])), df.columns[2])
            df = df.rename(columns={col_year:"Annee", col_fil:"Filiere", col_val:"TWh"})
            df["TWh"] = pd.to_numeric(df["TWh"], errors="coerce")

        fig = px.line(df, x="Annee", y="TWh", color="Filiere", markers=True)
        fig.update_layout(height=420, margin=dict(l=40, r=20, t=20, b=40),
                          yaxis_title="TWh", xaxis_title="Année",
                          legend=dict(orientation="h", yanchor="bottom", y=-0.2),
                          paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        return fig


app = App(app_ui, server)
