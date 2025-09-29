# server/bilan.py — Carte choroplèthe (solde), camembert & évolution 2014–2024
from __future__ import annotations

from shiny import render, reactive, ui
import shinywidgets as sw

import pandas as pd
import geopandas as gpd
import folium
import plotly.express as px
import plotly.graph_objects as go
import json
from io import StringIO
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
    "Nucléaire": "#FFE18B", "Hydraulique": "#2071B2", "Fossile": "#313334",
    "Éolien": "#8DCDBF", "Solaire": "#F4902E", "Autre": "#14682D",
}
NAME_FIX = {"Bourgogne-Franche-Compté": "Bourgogne-Franche-Comté"}

# ---------- Données 2014–2024 ----------
def _load_timeseries_df() -> pd.DataFrame:
    txt = """regions\tyear\tconso\tnuc\thyd\tfos\teol\tsol\tautre
Auvergne-Rhône-Alpes\t2014\t63,6\t87,9\t28,2\t1,1\t0,8\t0,6\t0,8
Bourgogne-Franche-Compté\t2014\t20,7\t0\t0,8\t0,5\t0,4\t0,2\t0,1
Bretagne\t2014\t21,6\t0\t0,6\t0,3\t1,4\t0,2\t0,3
Centre-Val de Loire\t2014\t17,1\t77,9\t0,1\t0,3\t1,6\t0,2\t0,4
Corse\t2014\t2,1\t0\t0,5\t0,8\t0\t0,1\t0
Grand Est\t2014\t45,3\t85,9\t8,7\t6,1\t4\t0,5\t0,5
Hauts-de-France\t2014\t50,1\t34,7\t0\t3,8\t3,7\t0,1\t0,8
Île-de-France\t2014\t71\t0\t0\t2,1\t0\t0,1\t1,1
Normandie\t2014\t27,5\t72,1\t0,1\t3\t1,1\t0,1\t0,5
Nouvelle-Aquitaine\t2014\t41,7\t42,5\t4,8\t0,4\t0,8\t1,2\t1
Occitanie\t2014\t35,8\t14,9\t12,9\t0,2\t2,1\t1,3\t0,7
Pays de la Loire\t2014\t26,1\t0\t0\t3,6\t1,1\t0,4\t0,4
Provence-Alpes-Côte d'Azur\t2014\t39,5\t0\t10,5\t2,4\t0,1\t1\t0,6
France\t2014\t462,7\t415,8\t67,5\t24,6\t17\t5,9\t7,1
Auvergne-Rhône-Alpes\t2015\t66,3\t90,9\t25,8\t2\t0,8\t0,8\t0,8
Bourgogne-Franche-Compté\t2015\t20,8\t0\t0,7\t0,6\t0,7\t0,2\t0,2
Bretagne\t2015\t21,9\t0\t0,5\t0,4\t1,6\t0,2\t0,4
Centre-Val de Loire\t2015\t18,1\t79,3\t0,1\t0,3\t1,9\t0,3\t0,5
Corse\t2015\t2,2\t0\t0,3\t1\t0\t0,2\t0
Grand Est\t2015\t45,8\t85,2\t8\t7,5\t5,2\t0,5\t0,6
Hauts-de-France\t2015\t50,4\t37,5\t0\t5,3\t5\t0,1\t0,9
Île-de-France\t2015\t73,2\t0\t0\t2,4\t0\t0,1\t1
Normandie\t2015\t27,8\t64,8\t0,1\t3,4\t1,3\t0,1\t0,5
Nouvelle-Aquitaine\t2015\t43,2\t40,4\t3,6\t0,7\t0,9\t1,8\t1,3
Occitanie\t2015\t37,1\t18,8\t10,6\t0,3\t2,3\t1,6\t0,7
Pays de la Loire\t2015\t26,6\t0\t0\t3,9\t1,2\t0,4\t0,4
Provence-Alpes-Côte d'Azur\t2015\t40,8\t0\t8,7\t5,2\t0,1\t1,2\t0,6
France\t2015\t474,1\t416,8\t58,8\t33\t21,1\t7,4\t7,7
Auvergne-Rhône-Alpes\t2016\t66,6\t75\t27,7\t2,5\t0,9\t0,8\t0,9
Bourgogne-Franche-Compté\t2016\t21,8\t0\t0,9\t0,7\t0,8\t0,2\t0,2
Bretagne\t2016\t22,4\t0\t0,6\t0,6\t1,5\t0,2\t0,3
Centre-Val de Loire\t2016\t18,4\t75,7\t0,1\t0,3\t1,8\t0,2\t0,4
Corse\t2016\t2,2\t0\t0,4\t0,9\t0\t0,2\t0
Grand Est\t2016\t47,1\t82,8\t9\t10,1\t4,9\t0,5\t0,8
Hauts-de-France\t2016\t51\t31,2\t0\t8,3\t4,9\t0,1\t1
Île-de-France\t2016\t74\t0\t0,1\t2,3\t0\t0,1\t1,2
Normandie\t2016\t28,7\t57,3\t0,1\t5,1\t1,2\t0,1\t0,5
Nouvelle-Aquitaine\t2016\t44\t42,2\t4,7\t0,9\t0,9\t2,3\t1,4
Occitanie\t2016\t37,8\t19,8\t11,1\t0,3\t2,6\t1,8\t0,7
Pays de la Loire\t2016\t27,4\t0\t0\t4\t1,3\t0,4\t0,4
Provence-Alpes-Côte d'Azur\t2016\t41\t0\t8,8\t9\t0,1\t1,4\t0,9
France\t2016\t482,4\t384\t63,6\t45\t21\t8,4\t8,6
Auvergne-Rhône-Alpes\t2017\t66,7\t80\t22,9\t2,3\t1\t0,9\t0,8
Bourgogne-Franche-Compté\t2017\t21,8\t0\t0,6\t0,7\t1,1\t0,2\t0,2
Bretagne\t2017\t22,3\t0\t0,6\t0,8\t1,6\t0,2\t0,4
Centre-Val de Loire\t2017\t18,4\t74,9\t0,1\t0,4\t1,9\t0,3\t0,5
Corse\t2017\t2,3\t0\t0,4\t1\t0\t0,2\t0
Grand Est\t2017\t47\t76,9\t8\t12,2\t5,6\t0,5\t0,8
Hauts-de-France\t2017\t50,8\t31,4\t0\t10,9\t5,7\t0,1\t0,9
Île-de-France\t2017\t72,3\t0\t0\t2,4\t0,1\t0,1\t1,3
Normandie\t2017\t28,1\t53\t0,1\t5\t1,3\t0,1\t0,5
Nouvelle-Aquitaine\t2017\t44,1\t45,1\t3,3\t1,1\t1,3\t2,5\t1,6
Occitanie\t2017\t38,5\t17,8\t9,4\t0,3\t3\t2,1\t0,7
Pays de la Loire\t2017\t27,3\t0\t0\t6,7\t1,3\t0,4\t0,4
Provence-Alpes-Côte d'Azur\t2017\t41,3\t0\t7,7\t9,5\t0,1\t1,5\t1,1
France\t2017\t480,8\t379,1\t53,2\t53,3\t24\t9,2\t9,3
Auvergne-Rhône-Alpes\t2018\t66\t80,2\t29,2\t1,5\t1,1\t1\t1,1
Bourgogne-Franche-Compté\t2018\t21,4\t0\t0,8\t0,7\t1,3\t0,3\t0,3
Bretagne\t2018\t22,5\t0\t0,6\t0,8\t1,8\t0,2\t0,4
Centre-Val de Loire\t2018\t18,1\t74,5\t0,1\t0,4\t2,1\t0,3\t0,5
Corse\t2018\t2,3\t0\t0,7\t0,8\t0\t0,2\t0
Grand Est\t2018\t46,1\t80,6\t7,3\t8,7\t6,3\t0,7\t0,9
Hauts-de-France\t2018\t50,8\t34,6\t0\t8,9\t7,1\t0,2\t1
Île-de-France\t2018\t71,7\t0\t0\t1,7\t0,1\t0,1\t1,3
Normandie\t2018\t28\t60,4\t0,1\t3,4\t1,5\t0,2\t0,5
Nouvelle-Aquitaine\t2018\t43,9\t45,8\t4,5\t0,9\t1,8\t3\t1,5
Occitanie\t2018\t38,7\t17,2\t13,9\t0,3\t3,3\t2,2\t0,7
Pays de la Loire\t2018\t27,4\t0\t0\t4,5\t1,6\t0,5\t0,4
Provence-Alpes-Côte d'Azur\t2018\t40,5\t0\t10,5\t5,8\t0,1\t1,6\t1,1
France\t2018\t477,2\t393,2\t67,8\t38,4\t28,1\t10,4\t9,5
Auvergne-Rhône-Alpes\t2019\t64,6\t85,8\t26,7\t2,1\t1,2\t1,2\t1
Bourgogne-Franche-Compté\t2019\t21,2\t0\t0,9\t0,8\t1,8\t0,4\t0,3
Bretagne\t2019\t22,6\t0\t0,6\t0,9\t1,9\t0,2\t0,4
Centre-Val de Loire\t2019\t18,2\t71,6\t0,1\t0,4\t2,6\t0,4\t0,5
Corse\t2019\t2,3\t0\t0,4\t1\t0\t0,2\t0
Grand Est\t2019\t45,7\t76,4\t8,6\t9,6\t7,7\t0,7\t1
Hauts-de-France\t2019\t49,6\t32,1\t0\t9,9\t8,9\t0,2\t1,1
Île-de-France\t2019\t70,4\t0\t0,1\t1,7\t0,1\t0,1\t1,3
Normandie\t2019\t27,8\t49,3\t0,1\t3,1\t1,8\t0,2\t0,5
Nouvelle-Aquitaine\t2019\t43,5\t47,3\t3,7\t0,9\t1,9\t3,3\t1,6
Occitanie\t2019\t38,3\t17\t10\t0,3\t3,7\t2,6\t0,7
Pays de la Loire\t2019\t27,2\t0\t0\t3,4\t2\t0,6\t0,4
Provence-Alpes-Côte d'Azur\t2019\t40,9\t0\t8,4\t7,6\t0,1\t1,9\t0,9
France\t2019\t472\t379,5\t59,6\t41,7\t33,8\t12\t9,5
Auvergne-Rhône-Alpes\t2020\t60,8\t77,2\t28,6\t2,5\t1,2\t1,4\t1
Bourgogne-Franche-Compté\t2020\t20,2\t0\t0,7\t0,7\t2\t0,4\t0,3
Bretagne\t2020\t21,9\t0\t0,6\t0,9\t2,3\t0,3\t0,5
Centre-Val de Loire\t2020\t17,5\t65,8\t0,1\t0,4\t3,1\t0,4\t0,5
Corse\t2020\t2,2\t0\t0,5\t0,8\t0\t0,2\t0
Grand Est\t2020\t42,9\t63,4\t7,7\t6,8\t8,7\t0,7\t1
Hauts-de-France\t2020\t47,3\t32,6\t0\t9,5\t11,7\t0,2\t1,1
Île-de-France\t2020\t65,8\t0\t0\t1,7\t0,1\t0,1\t1,1
Normandie\t2020\t26,5\t42\t0,1\t3\t2\t0,2\t0,6
Nouvelle-Aquitaine\t2020\t41,9\t38,2\t4,2\t0,8\t2,4\t3,5\t1,6
Occitanie\t2020\t36,8\t16,2\t11,4\t0,3\t3,6\t2,7\t0,7
Pays de la Loire\t2020\t26\t0\t0\t3\t2,4\t0,7\t0,5
Provence-Alpes-Côte d'Azur\t2020\t38,8\t0\t10,8\t6,9\t0,1\t2\t0,8
France\t2020\t448,5\t335,4\t64,9\t37,3\t39,7\t12,7\t9,6
Auvergne-Rhône-Alpes\t2021\t64,7\t84,33\t27,5\t2,3\t1,3\t1,5\t1
Bourgogne-Franche-Compté\t2021\t21,3\t0\t1\t0,7\t1,9\t0,4\t0,4
Bretagne\t2021\t22,7\t0\t0,6\t1\t2\t0,3\t0,5
Centre-Val de Loire\t2021\t18,2\t68,7\t0,1\t0,4\t2,9\t0,6\t0,5
Corse\t2021\t2,4\t0\t0,5\t1\t0\t0,3\t0
Grand Est\t2021\t45,5\t61,2\t8,4\t7,7\t7,6\t0,8\t1,2
Hauts-de-France\t2021\t49,7\t29,8\t0\t9,3\t10,4\t0,3\t0,9
Île-de-France\t2021\t69,2\t0\t0,1\t2\t0,3\t0,2\t1,3
Normandie\t2021\t27,5\t65,1\t0,1\t2,8\t1,8\t0,2\t0,7
Nouvelle-Aquitaine\t2021\t43,9\t36,7\t4,7\t0,9\t2,8\t3,8\t1,5
Occitanie\t2021\t38,2\t14,8\t10,3\t0,3\t3,5\t3\t0,7
Pays de la Loire\t2021\t27,4\t0\t0\t4,7\t2,2\t0,8\t0,5
Provence-Alpes-Côte d'Azur\t2021\t41,1\t0\t8,6\t5,7\t0,2\t2,1\t0,7
France\t2021\t471,5\t360,7\t62\t38,6\t36,9\t14,2\t10
Auvergne-Rhône-Alpes\t2022\t63,9\t73,1\t22,6\t2,9\t1,4\t2,2\t1
Bourgogne-Franche-Compté\t2022\t19,9\t0\t0,8\t0,6\t2\t0,7\t0,4
Bretagne\t2022\t21,3\t0\t0,6\t3,8\t2,1\t0,4\t0,5
Centre-Val de Loire\t2022\t17,5\t62,9\t0,1\t0,4\t2,9\t1\t0,5
Corse\t2022\t2,3\t0\t0,4\t1,1\t0\t0,3\t0
Grand Est\t2022\t43,7\t37,3\t7,4\t11,3\t8,3\t1,3\t1,3
Hauts-de-France\t2022\t47,2\t28,2\t0\t11\t11\t0,5\t0,9
Île-de-France\t2022\t66,5\t0\t0,1\t2,1\t0,3\t0,2\t1,3
Normandie\t2022\t26,4\t43,4\t0,1\t2,4\t1,8\t0,3\t0,7
Nouvelle-Aquitaine\t2022\t41,6\t21,9\t3,1\t1\t2,9\t4,8\t1,5
Occitanie\t2022\t37,4\t12,1\t9,1\t0,3\t3,1\t3,9\t0,8
Pays de la Loire\t2022\t26,4\t0\t0\t3,3\t2,9\t1\t0,5
Provence-Alpes-Côte d'Azur\t2022\t39,9\t0\t5,5\t8,9\t0,2\t2,7\t1,1
France\t2022\t453,9\t279\t49,6\t49,1\t38,9\t19,2\t10,6
Auvergne-Rhône-Alpes\t2023\t61\t83,6\t26,7\t1,4\t1,5\t2,5\t1
Bourgogne-Franche-Compté\t2023\t19,6\t0\t0,8\t0,7\t2,7\t0,9\t0,4
Bretagne\t2023\t21,4\t0\t0,6\t2,6\t2,7\t0,5\t0,5
Centre-Val de Loire\t2023\t17,3\t56,8\t0,1\t0,3\t3,7\t1,1\t0,5
Corse\t2023\t2,3\t0\t0,6\t0,8\t0\t0,3\t0
Grand Est\t2023\t41,1\t55,3\t7,8\t8,2\t11,2\t1,4\t1,2
Hauts-de-France\t2023\t46,3\t28,7\t0\t6,7\t14,5\t0,6\t1
Île-de-France\t2023\t63,2\t0\t0,1\t1,6\t0,4\t0,3\t1,1
Normandie\t2023\t25,6\t54,3\t0,1\t2,2\t2,6\t0,3\t0,7
Nouvelle-Aquitaine\t2023\t41\t37,2\t4,2\t0,7\t3,5\t5,5\t1,5
Occitanie\t2023\t36,1\t4,5\t9,3\t0,3\t3,5\t4,6\t0,9
Pays de la Loire\t2023\t25\t0\t0\t1,6\t4,3\t1,3\t0,5
Provence-Alpes-Côte d'Azur\t2023\t38,7\t0\t8,4\t4,8\t0,2\t3,2\t1
France\t2023\t438,5\t320,4\t58,8\t31,7\t50,9\t22,5\t10,3
Auvergne-Rhône-Alpes\t2024\t62,9\t80,2\t32,5\t1,1\t1,5\t2,9\t1
Bourgogne-Franche-Compté\t2024\t19,6\t0\t1,1\t0,6\t2,2\t1,1\t0,4
Bretagne\t2024\t21,7\t0\t0,6\t1,7\t3,4\t0,7\t0,5
Centre-Val de Loire\t2024\t17,7\t70,5\t0,2\t0,2\t3,2\t1,2\t0,5
Corse\t2024\t2,3\t0\t0,4\t0,9\t0\t0,3\t0
Grand Est\t2024\t41,6\t62,4\t9,5\t3,9\t9,2\t1,7\t1,3
Hauts-de-France\t2024\t46,2\t32,8\t0\t3,5\t12,5\t0,6\t0,9
Île-de-France\t2024\t64,7\t0\t0,1\t1,3\t0,3\t0,3\t1,2
Normandie\t2024\t26,2\t60,5\t0,1\t2,2\t3,4\t0,4\t0,7
Nouvelle-Aquitaine\t2024\t40,8\t38,6\t5,6\t0,7\t3,3\t5,8\t1,6
Occitanie\t2024\t35,9\t16,7\t12,9\t0,2\t3,7\t5,1\t1
Pays de la Loire\t2024\t25,3\t0\t0\t1,4\t3,9\t1,5\t0,5
Provence-Alpes-Côte d'Azur\t2024\t38,1\t0\t12,1\t2,6\t0,2\t3,3\t1
France\t2024\t442,3\t361,7\t75,1\t20\t46,9\t24,8\t10,5
"""
    df = pd.read_csv(StringIO(txt), sep="\t")
    for c in ["conso", *PIE_FIELDS_TS]:
        df[c] = df[c].astype(str).str.replace(",", ".", regex=False).astype(float)
    df["regions"] = df["regions"].replace(NAME_FIX)
    df["prod_tot"] = df[PIE_FIELDS_TS].sum(axis=1)
    df["balance"] = df["prod_tot"] - df["conso"]
    return df

# ---------- Chargement + préparation ----------
def _load_data_prepared(app_dir: Path):
    path = app_dir / "www" / "data" / "regions_simplified.geojson"
    gj_text = path.read_text(encoding="utf-8")

    gdf = gpd.read_file(path)
    if gdf.crs is None:
        gdf = gdf.set_crs(4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(4326)

    rep = gdf.geometry.representative_point()
    gdf["lon"] = rep.x.astype(float)
    gdf["lat"] = rep.y.astype(float)

    try:
        gdf_simpl = gdf.to_crs(3857).copy()
        gdf_simpl["geometry"] = gdf_simpl.geometry.simplify(400)
        gj_text = gdf_simpl.to_crs(4326).to_json()
    except Exception:
        pass

    df_ts = _load_timeseries_df()
    regions = sorted([r for r in df_ts["regions"].unique() if r != "France"])
    years = sorted(df_ts["year"].unique())

    fr_by_year = (
        df_ts[df_ts["regions"] == "France"]
        .set_index("year")[["conso", *PIE_FIELDS_TS, "prod_tot", "balance"]]
    )

    return {
        "gdf": gdf,
        "gj_text": gj_text,     # contours simplifiés
        "regions": regions,
        "years": years,
        "ts": df_ts,
        "fr_by_year": fr_by_year,
    }

# ---------- Carte (choroplèthe, tooltips complets) ----------
def _build_balance_choropleth_html(
    gdf_base: gpd.GeoDataFrame, df_year: pd.DataFrame, dark: bool
) -> str:
    # Join (exclure France), et reconstruire un GeoJSON avec les indicateurs dans properties
    df_reg = df_year[df_year["regions"] != "France"].copy()
    df_reg = df_reg.rename(columns={"regions": "NOM"})
    gdf = gdf_base.merge(
        df_reg[["NOM", "conso", "prod_tot", "balance"]],
        on="NOM", how="left"
    ).copy()

    # bornes et palette
    vmin = float(np.nanmin(gdf["balance"])) if len(gdf) else -1.0
    vmax = float(np.nanmax(gdf["balance"])) if len(gdf) else 1.0
    vmax = max(vmax, 0.1); vmin = min(vmin, -0.1)
    cmap = branca.colormap.LinearColormap(
        colors=["#DC2626", "#F3F4F6", "#16A34A"], vmin=vmin, vmax=vmax
    )
    cmap.caption = "Solde (TWh)"

    # champs texte pour tooltips
    def fmt(x): 
        try: return f"{float(x):,.1f}".replace(",", " ")
        except: return "0,0"

    gdf["prod_txt"] = gdf["prod_tot"].apply(fmt)
    gdf["conso_txt"] = gdf["conso"].apply(fmt)
    gdf["balance_txt"] = gdf["balance"].apply(fmt)

    # GeoJSON dynamique avec indicateurs
    gjson = json.loads(gdf[["NOM","conso","prod_tot","balance","prod_txt","conso_txt","balance_txt","geometry"]].to_json())

    tiles = "cartodbdark_matter" if dark else "cartodbpositron"
    contour_color = "#6B7280" if not dark else "#94A3B8"
    highlight_color = "#111827" if not dark else "#E2E8F0"

    m = folium.Map(location=[46.8, 2.5], zoom_start=5, tiles=tiles, control_scale=True, width="100%")

    def _style_fn(feat):
        val = feat["properties"].get("balance", 0.0)
        return {"fillColor": cmap(val), "color": contour_color, "weight": 1,
                "fillOpacity": 0.7 if not dark else 0.6}

    folium.GeoJson(
        data=gjson,
        name="Régions",
        style_function=_style_fn,
        highlight_function=lambda feat: {"weight": 2, "color": highlight_color, "fillOpacity": 0.85},
        tooltip=folium.features.GeoJsonTooltip(
            fields=["NOM","prod_txt","conso_txt","balance_txt"],
            aliases=["Région","Production (TWh)","Consommation (TWh)","Solde (TWh)"],
            localize=True, sticky=False, labels=True
        ),
    ).add_to(m)

    cmap.add_to(m)
    return m._repr_html_()

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

    # Remplir le select (geo_select ou fr_region)
    @reactive.effect
    def _init_selects():
        d = data()
        choices = ["France"] + d["regions"]
        try:
            ui.update_select("geo_select", choices=choices, selected="France")
        except Exception:
            try:
                ui.update_select("fr_region", choices=choices, selected="France")
            except Exception:
                pass

    # ---------------- Carte (choroplèthe solde) ----------------
    @output
    @render.ui
    def fr_map():
        d = data()
        year = int(input.year())
        dark = _is_dark(input)
        key = (year, dark)

        if not hasattr(fr_map, "_cache"):
            fr_map._cache = {}
        cache = fr_map._cache

        if key not in cache:
            df_year = d["ts"][d["ts"]["year"] == year]
            cache[key] = _build_balance_choropleth_html(d["gdf"], df_year, dark)

        return ui.HTML(cache[key])

    @reactive.effect
    def _invalidate_map_cache():
        _ = input.year()
        _ = _is_dark(input)
        if hasattr(fr_map, "_cache"):
            fr_map._cache.clear()

    # ---------------- Camembert ----------------
    @output
    @sw.render_widget
    def prod_pie():
        d = data()

        # Sécurité : si le select n’a qu’un seul choix, on le met à jour ici aussi.
        try:
            # on tente sur geo_select
            cur = input.geo_select()
            if cur is not None:
                # impossible de lire les "choices", donc on renvoie la MàJ inconditionnelle
                ui.update_select("geo_select", choices=["France"] + d["regions"], selected=cur or "France")
        except Exception:
            try:
                cur = input.fr_region()
                ui.update_select("fr_region", choices=["France"] + d["regions"], selected=cur or "France")
            except Exception:
                pass

        region = _get_region(input)
        year = int(input.year())

        if region == "France":
            row = d["fr_by_year"].loc[year]
            s_vals = [row["nuc"], row["hyd"], row["fos"], row["eol"], row["sol"], row["autre"]]
            title = f"Production par filière — France — {year}"
        else:
            row = d["ts"][(d["ts"]["regions"] == region) & (d["ts"]["year"] == year)]
            if row.empty:
                s_vals = [0, 0, 0, 0, 0, 0]
            else:
                rr = row.iloc[0]
                s_vals = [rr[k] for k in PIE_FIELDS_TS]
            title = f"Production par filière — {region} — {year}"

        df_pie = pd.DataFrame({"Filière": PIE_LABELS_FR, "TWh": s_vals})
        fig = px.pie(
            df_pie, names="Filière", values="TWh", title=title, hole=0.15,
            color="Filière", color_discrete_map=PIE_COLOR_MAP,
        )

        dark = _is_dark(input)
        font_color = "#F8FAFC" if dark else "#0B162C"
        fig.update_traces(textinfo="percent+label", hovertemplate="%{label}: %{value:.1f} TWh<extra></extra>")
        fig.update_layout(
            autosize=True,
            height=340,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color=font_color, family="Poppins, Arial, sans-serif"),
            legend=dict(title="", font=dict(color=font_color)),
            title=dict(font=dict(color=font_color)),
            margin=dict(t=44, r=8, b=8, l=8),
        )
        return fig

    # ---------------- Évolution ----------------
    @output
    @sw.render_widget
    def area_chart():
        d = data()
        geo = _get_region(input)
        year_sel = int(input.year())

        df = d["ts"]
        df_g = (df[df["regions"] == "France"] if geo == "France" else df[df["regions"] == geo]).copy()
        df_g = df_g[(df_g["year"] >= 2014) & (df_g["year"] <= 2024)].sort_values("year")

        filieres_map = {"nuc": "Nucléaire", "hyd": "Hydraulique", "fos": "Fossile",
                        "eol": "Éolien", "sol": "Solaire", "autre": "Autre"}
        colors = {"Nucléaire": "#FFE18B", "Hydraulique": "#2071B2", "Fossile": "#313334",
                  "Éolien": "#8DCDBF", "Solaire": "#F4902E", "Autre": "#14682D"}

        df_long = df_g.melt(id_vars=["year", "conso"], value_vars=list(filieres_map.keys()),
                            var_name="filiere", value_name="production") \
                     .assign(filiere=lambda x: x["filiere"].map(filieres_map))

        dark = _is_dark(input)
        font_color = "#F8FAFC" if dark else "#0B162C"
        grid_color = "rgba(203,213,225,.26)" if dark else "rgba(15,23,42,.08)"

        fig = go.Figure()
        for f in ["Nucléaire", "Hydraulique", "Fossile", "Éolien", "Solaire", "Autre"]:
            dff = df_long[df_long["filiere"] == f]
            fig.add_trace(go.Scatter(
                x=dff["year"], y=dff["production"],
                mode="none", stackgroup="one", fill="tonexty",
                name=f, fillcolor=colors[f],
                hovertemplate=f"<b>{f}</b><br>Année: %{{x}}<br>Prod: %{{y:.1f}} TWh<extra></extra>",
            ))

        fig.add_trace(go.Scatter(
            x=df_g["year"], y=df_g["conso"], mode="lines",
            name="Consommation", line=dict(color="red", width=3, dash="dash"),
            hovertemplate="<b>Consommation</b><br>Année: %{x}<br>%{y:.1f} TWh<extra></extra>",
        ))

        fig.add_vline(x=year_sel, line_width=2, line_dash="dot", line_color="red")
        fig.update_xaxes(rangeslider=dict(visible=False), range=[2014, 2024])
        fig.update_layout(
            autosize=True,
            height=250,
            xaxis=dict(title=dict(text="Année", font=dict(size=13, color=font_color)),
                       tickfont=dict(size=11, color=font_color),
                       gridcolor=grid_color, zerolinecolor=grid_color),
            yaxis=dict(title=dict(text="TWh", font=dict(size=13, color=font_color)),
                       tickfont=dict(size=11, color=font_color),
                       gridcolor=grid_color, zerolinecolor=grid_color),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                        font=dict(size=11, color=font_color)),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=36, r=16, t=8, b=8),
            font=dict(color=font_color, family="Poppins, Arial, sans-serif"),
        )
        return fig
