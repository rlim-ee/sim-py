# server/energie/bilan.py — bilan énergétique par région française
#
# Ce module répond à la question : "comment la France et ses régions
# produisent-elles et consomment-elles de l'électricité, année par année ?"
#
# Il produit cinq outputs, tous pilotés par le curseur d'année (input.year())
# et le sélecteur de région (input.fr_region) :
#
#   - fr_map         → carte choroplèthe des régions (solde production − consommation)
#   - prod_pie       → camembert de la production par filière pour la région choisie
#   - area_chart     → graphique en aires empilées (évolution 2014–2024)
#   - region_selector → widget de sélection de région (construit dynamiquement)
#   - map_title, area_title, pie_title → titres mis à jour en temps réel
#
# Folium génère la carte des régions sous forme HTML.
# Plotly génère le camembert et le graphique d'évolution de manière interactive.
# Les données viennent de www/data/data_energie_region.csv et
# www/data/regions_simplified.geojson.
from __future__ import annotations

from shiny import render, ui
import shinywidgets as sw

import copy
import pandas as pd
import geopandas as gpd
import folium
import plotly.graph_objects as go
import json
from pathlib import Path
import branca

from server._common import (
    is_dark, cached, text_color, grid_color,
    FILIERE_CODES, FILIERE_LABEL, FILIERE_COLOR_BY_LABEL, FILIERE_LABELS_FR,
)


# Alias locaux pour raccourcir les noms dans ce module
PIE_FIELDS_TS = FILIERE_CODES
PIE_LABELS_FR = FILIERE_LABELS_FR
PIE_COLOR_MAP = FILIERE_COLOR_BY_LABEL
FILIERES_MAP  = FILIERE_LABEL


# =========================================================
# Lecture de la région sélectionnée
# =========================================================
def _get_region(input) -> str:
    """
    Lit la région active depuis les inputs Shiny.
    Deux noms possibles selon le contexte (geo_select ou fr_region)
    pour rester compatible avec d'éventuelles évolutions de l'interface.
    """
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


# =========================================================
# Chargement du CSV des séries temporelles
# =========================================================
def _load_timeseries_df(app_dir: Path) -> pd.DataFrame:
    """Lit le CSV de données énergétiques par région et par année."""
    path = app_dir / "www" / "data" / "data_energie_region.csv"
    df = pd.read_csv(path, sep=";")
    df["year"]    = df["year"].astype(int)
    num_cols      = ["conso", *PIE_FIELDS_TS]
    df[num_cols]  = df[num_cols].astype(float)
    df["prod_tot"] = df[PIE_FIELDS_TS].sum(axis=1)
    df["balance"]  = df["prod_tot"] - df["conso"]
    return df


# =========================================================
# Construction de la carte Folium des régions
# =========================================================
def _build_balance_choropleth_html_from_base(
    gjson_base: dict, df_year: pd.DataFrame, dark: bool
) -> str:
    """
    Construit la carte choroplèthe du solde (production − consommation) par région.
    Rouge = déficit, vert = excédent.
    La carte est recalculée par (année, thème) et mise en cache.
    """
    sub    = df_year[df_year["regions"] != "France"]
    mvals  = sub.set_index("regions")[["conso", "prod_tot", "balance"]].to_dict("index")

    if len(mvals):
        vmin = float(min(v["balance"] for v in mvals.values()))
        vmax = float(max(v["balance"] for v in mvals.values()))
    else:
        vmin, vmax = -1.0, 1.0

    vmax = max(vmax, 0.1)
    vmin = min(vmin, -0.1)

    cmap = branca.colormap.LinearColormap(
        colors=["#DC2626", "#F3F4F6", "#16A34A"],
        vmin=vmin, vmax=vmax,
    )
    cmap.caption = "Solde (TWh)"

    def fmt(x):
        try:
            return f"{float(x):,.1f}".replace(",", " ")
        except Exception:
            return "0,0"

    # Enrichissement du GeoJSON avec les valeurs de l'année
    features = []
    for feat in gjson_base["features"]:
        nom  = feat["properties"].get("NOM")
        vals = mvals.get(nom, {"conso": 0.0, "prod_tot": 0.0, "balance": 0.0})
        props = {
            "NOM":        nom,
            "conso":      float(vals["conso"]),
            "prod_tot":   float(vals["prod_tot"]),
            "balance":    float(vals["balance"]),
            "prod_txt":   fmt(vals["prod_tot"]),
            "conso_txt":  fmt(vals["conso"]),
            "balance_txt": fmt(vals["balance"]),
        }
        features.append({"type": "Feature", "geometry": feat["geometry"], "properties": props})

    gjson = {"type": "FeatureCollection", "features": features}

    tiles           = "cartodbdark_matter" if dark else "cartodbpositron"
    contour_color   = "#FFFFFF"
    highlight_color = "#E2E8F0" if dark else "#111827"

    m = folium.Map(
        location=[46.8, 2.5], zoom_start=5,
        tiles=tiles, control_scale=True, width="100%",
    )

    def _style_fn(feat):
        val = feat["properties"].get("balance", 0.0)
        return {
            "fillColor":   cmap(val),
            "color":       contour_color,
            "weight":      1,
            "fillOpacity": 0.6 if dark else 0.7,
        }

    folium.GeoJson(
        data=gjson, name="Régions",
        style_function=_style_fn,
        highlight_function=lambda f: {
            "weight": 2, "color": highlight_color, "fillOpacity": 0.85,
        },
        tooltip=folium.features.GeoJsonTooltip(
            fields=["NOM", "prod_txt", "conso_txt", "balance_txt"],
            aliases=["Région", "Production (TWh)", "Consommation (TWh)", "Solde (TWh)"],
            localize=True, sticky=False, labels=True,
        ),
    ).add_to(m)

    cmap.add_to(m)
    return m._repr_html_()


# =========================================================
# Chargement et préparation globale (une seule fois par processus)
# =========================================================
def _load_data_prepared(app_dir: Path) -> dict:
    """
    Charge le GeoJSON des régions, le CSV des séries, et prépare les données
    dérivées utilisées par tous les outputs de ce module.
    """
    geo_path = app_dir / "www" / "data" / "regions_simplified.geojson"

    gdf = gpd.read_file(geo_path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    # Simplification pour réduire la taille des données transmises au navigateur
    try:
        gdf2 = gdf.to_crs(3857).copy()
        gdf2["geometry"] = gdf2.geometry.simplify(2000, preserve_topology=True)
        gdf = gdf2.to_crs(4326)
    except Exception:
        pass

    gjson_base = json.loads(gdf[["NOM", "geometry"]].to_json())

    df_ts = _load_timeseries_df(app_dir)

    regions = sorted([r for r in df_ts["regions"].unique() if r != "France"])
    years   = sorted(df_ts["year"].unique())

    # Données France nationale indexées par année (pour le camembert)
    fr_by_year = (
        df_ts[df_ts["regions"] == "France"]
        .set_index("year")[["conso", *PIE_FIELDS_TS, "prod_tot", "balance"]]
    )

    # Séries en format "long" par région (pour le graphique en aires)
    long_by_region = {}
    for reg in ["France"] + regions:
        sub = df_ts[df_ts["regions"] == reg].copy().sort_values("year")
        long_by_region[reg] = (
            sub.melt(
                id_vars=["year", "conso"],
                value_vars=list(FILIERES_MAP.keys()),
                var_name="filiere",
                value_name="production",
            )
            .assign(filiere=lambda x: x["filiere"].map(FILIERES_MAP))
        )

    return {
        "gjson_base":       gjson_base,
        "regions":          regions,
        "years":            years,
        "ts":               df_ts,
        "fr_by_year":       fr_by_year,
        "long_by_region":   long_by_region,
    }


def _get_data(app_dir: Path) -> dict:
    """Cache global partagé entre toutes les sessions."""
    return cached(f"bilan::{Path(app_dir).resolve()}", lambda: _load_data_prepared(app_dir))


def _get_map_html(app_dir: Path, year: int, dark: bool) -> str:
    """Cache des cartes Folium par (année, thème) — construites à la demande."""
    key = f"bilan::map::{Path(app_dir).resolve()}::{year}::{int(dark)}"

    def _build():
        d = _get_data(app_dir)
        df_year = d["ts"][d["ts"]["year"] == year]
        return _build_balance_choropleth_html_from_base(d["gjson_base"], df_year, dark)

    return cached(key, _build)


# =========================================================
# Fonctions serveur Shiny
# =========================================================
def server(input, output, session, app_dir: Path):
    d = _get_data(app_dir)

    # Carte choroplèthe — se recalcule quand l'année ou le thème change
    @output
    @render.ui
    def fr_map():
        year = int(input.year())
        dark = is_dark(input)
        return ui.HTML(_get_map_html(app_dir, year, dark))

    # Camembert de la production par filière
    @output
    @sw.render_widget
    def prod_pie():
        region = _get_region(input)
        year   = int(input.year())
        dark   = is_dark(input)

        if region == "France":
            row    = d["fr_by_year"].loc[year]
            values = [row[k] for k in PIE_FIELDS_TS]
        else:
            row    = d["ts"][(d["ts"]["regions"] == region) & (d["ts"]["year"] == year)]
            values = [row.iloc[0][k] if not row.empty else 0 for k in PIE_FIELDS_TS]

        font_color = text_color(dark)

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
                orientation="h", y=-0.15, x=0.5, xanchor="center",
                font=dict(color=font_color),
            ),
        )
        return fig

    # Graphique en aires — évolution production + consommation 2014–2024
    # La version de base est mise en cache par (région, thème) ;
    # seul le marqueur de l'année sélectionnée est ajouté à chaque rendu.
    _area_base_cache: dict[tuple[str, bool], go.Figure] = {}

    def _build_area_base(region: str, dark: bool) -> go.Figure:
        df_long = d["long_by_region"].get(region)
        if df_long is None:
            sub = d["ts"][d["ts"]["regions"] == region].copy().sort_values("year")
            sub = sub[(sub["year"] >= 2014) & (sub["year"] <= 2024)]
            df_long = sub.melt(
                id_vars=["year", "conso"],
                value_vars=list(FILIERES_MAP.keys()),
                var_name="filiere",
                value_name="production",
            ).assign(filiere=lambda x: x["filiere"].map(FILIERES_MAP))

        df_conso = d["ts"][d["ts"]["regions"] == region].copy()
        df_conso = df_conso[(df_conso["year"] >= 2014) & (df_conso["year"] <= 2024)].sort_values("year")

        font_color = text_color(dark)
        gc         = grid_color(dark)

        fig = go.Figure()
        # Une trace par filière, empilées (stackgroup="one")
        for f in PIE_LABELS_FR:
            dff = df_long[df_long["filiere"] == f]
            fig.add_trace(
                go.Scatter(
                    x=dff["year"],
                    y=dff["production"],
                    mode="none",
                    stackgroup="one",
                    fill="tonexty",
                    name=f,
                    fillcolor=PIE_COLOR_MAP[f],
                    hovertemplate=f"<b>{f}</b><br>Année: %{{x}}<br>Prod: %{{y:.1f}} TWh<extra></extra>",
                )
            )

        # Ligne de consommation superposée aux aires de production
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

        fig.update_xaxes(rangeslider=dict(visible=False), range=[2014, 2024])
        fig.update_layout(
            autosize=True, height=250,
            xaxis=dict(
                title=dict(text="Année", font=dict(size=13, color=font_color)),
                tickfont=dict(size=11, color=font_color),
                gridcolor=gc, zerolinecolor=gc,
            ),
            yaxis=dict(
                title=dict(text="TWh", font=dict(size=13, color=font_color)),
                tickfont=dict(size=11, color=font_color),
                gridcolor=gc, zerolinecolor=gc,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="left", x=0,
                font=dict(size=11, color=font_color),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=36, r=16, t=8, b=8),
            font=dict(color=font_color, family="Poppins, Arial, sans-serif"),
        )
        return fig

    @output
    @sw.render_widget
    def area_chart():
        region   = _get_region(input)
        year_sel = int(input.year())
        dark     = is_dark(input)

        key  = (region, dark)
        base = _area_base_cache.get(key)
        if base is None:
            base = _build_area_base(region, dark)
            _area_base_cache[key] = base

        # Copie profonde pour ne pas modifier la version en cache
        fig = copy.deepcopy(base)
        fig.add_vline(x=year_sel, line_width=2, line_dash="dot", line_color="red")
        return fig

    # Sélecteur de région — construit dynamiquement avec les régions disponibles dans les données
    @output
    @render.ui
    def region_selector():
        return ui.input_select(
            "fr_region",
            "Choisir une région",
            choices=["France"] + d["regions"],
            selected="France",
        )

    # Titres dynamiques — mis à jour à chaque changement d'année ou de région
    @output
    @render.text
    def map_title():
        y = 2024
        year_fn = getattr(input, "year", None)
        if callable(year_fn):
            try: y = int(year_fn())
            except Exception: pass
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
        year   = int(input.year())
        return f"Production d'énergie par filière — {region} — {year}"
