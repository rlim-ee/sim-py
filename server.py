# server.py — complet (jointure avec europe_map.rds + centroïdes pour cercles)
from __future__ import annotations

from shiny import App, reactive, render, ui
import shinywidgets as sw

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import pyreadr
import os

# Essayez d'utiliser shapely pour lire la géométrie WKT -> GeoJSON
try:
    from shapely import wkt as shp_wkt
    from shapely.geometry import mapping
    SHAPELY_OK = True
except Exception:
    SHAPELY_OK = False

from ui import app_ui

# ------------------------- utilitaires -------------------------
AURA_KM2 = 69_711
NUC_TOTAL_FR = 56

def fmt_int(n: float | int) -> str:
    try:
        return f"{int(round(n)):,}".replace(",", " ")
    except Exception:
        try:
            return f"{n:,}".replace(",", " ")
        except Exception:
            return str(n)

def _safe_read_rds(path: str) -> pd.DataFrame | None:
    try:
        if os.path.exists(path):
            res = pyreadr.read_r(path)
            return next(iter(res.values())).copy()
    except Exception:
        pass
    return None

# ------------------------- données Simu 1/2 -------------------------
consommation_actuelle = 442  # TWh (2025)

dc_data = pd.DataFrame({
    "Annee": [2025, 2026, 2028, 2035],
    "Conso": [0.131400, 1.752000, 3.504000, 8.760000],
})

production_data = pd.DataFrame({
    "Annee": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    "Min":   [538, 550, 560, 565, 568, 570, 572, 575, 578, 580, 585],
    "Max":   [538, 570, 580, 590, 595, 600, 610, 615, 620, 628, 636],
    "Ref":   [538, 560, 570, 577.5, 581.5, 585, 591, 595, 599, 604, 610.5],
})

consommation_data = pd.DataFrame({
    "Annee": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    "Ref":   [442, 455, 468, 481, 494, 508, 514, 520, 526, 532, 538],
})

conso_hist = pd.DataFrame({
    "Annee": [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
    "Conso": [425,434,434,449,460,464,468,467,481,472,499,472,487,495,463,474,482,481,477,472,449,472,454,439,442],
})
conso_p = pd.DataFrame({
    "Annee": list(range(2025, 2051)),
    "Ref":   [442,455,468,481,494,508,514,520,526,532,538,544,550,556,562,568,574,580,586,592,598,604,610,616,622,628],
})
delta = np.linspace(0, 50, len(conso_p))
conso_p["Min"] = (conso_p["Ref"] - delta).round(1)
conso_p["Max"] = (conso_p["Ref"] + delta).round(1)

prod_hist = pd.DataFrame({
    "Annee": [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
    "Prod":  [517,522,533,539,546,547,546,541,545,515,550,543,542,550,538,545,531,528,548,536,500,522,446,495,539],
})
prod_p = pd.DataFrame({
    "Annee": [2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037,2038,2039,2040,2041,2042,2043,2044,2045,2046,2047,2048,2049,2050],
    "Min":   [538,550,560,565,568,570,572,575,578,580,585,590,595,600,610,620,630,640,650,660,665,670,675,680,685,690],
    "Max":   [538,570,580,590,595,600,610,615,620,628,636,645,655,665,675,685,695,705,715,725,735,740,745,750,755,760],
    "Ref":   [538,560,570,577.5,581.5,585,591,595,599,604,610.5,617.5,625,632.5,642.5,652.5,662.5,672.5,682.5,692.5,700,705,710,715,720,725],
})

# ------------------------- DC Europe -------------------------
DC_RDS = "data/dc_europe.rds"
MAP_RDS = "data/europe_map.rds"

dc_eu = _safe_read_rds(DC_RDS)
if dc_eu is None:
    dc_eu = pd.DataFrame(columns=["name", "nb_dc", "pop"])

# harmonisation minimale
if "name" not in dc_eu.columns:
    for c in ("Country", "country", "pays"):
        if c in dc_eu.columns:
            dc_eu.rename(columns={c: "name"}, inplace=True)
            break
if "nb_dc" not in dc_eu.columns:
    for c in ("nb", "count", "dc_count"):
        if c in dc_eu.columns:
            dc_eu.rename(columns={c: "nb_dc"}, inplace=True)
            break
if "pop" not in dc_eu.columns:
    for c in ("population", "Population", "pop_total"):
        if c in dc_eu.columns:
            dc_eu.rename(columns={c: "pop"}, inplace=True)
            break

for c in ("nb_dc", "pop"):
    if c in dc_eu.columns:
        dc_eu[c] = pd.to_numeric(dc_eu[c], errors="coerce")

if {"nb_dc", "pop"}.issubset(dc_eu.columns):
    dc_eu["dc_per_million"] = dc_eu["nb_dc"] / (dc_eu["pop"] / 1_000_000)

# --- Lecture du fond "europe_map.rds" et conversion GeoJSON + centroïdes
emap_geojson = None
emap_centroids = None
emap_raw = _safe_read_rds(MAP_RDS)

if SHAPELY_OK and emap_raw is not None and {"name", "geometry"}.issubset(emap_raw.columns):
    emap = emap_raw[["name", "geometry"]].dropna().copy()

    def _load_geom(wkt_str):
        try:
            return shp_wkt.loads(str(wkt_str))
        except Exception:
            return None

    emap["geom"] = emap["geometry"].apply(_load_geom)
    emap = emap[emap["geom"].notnull()].copy()

    # centroïdes pour les cercles
    emap["lon"] = emap["geom"].apply(lambda g: float(g.centroid.x))
    emap["lat"] = emap["geom"].apply(lambda g: float(g.centroid.y))
    emap_centroids = emap[["name", "lat", "lon"]].copy()

    # GeoJSON feature collection (featureid = name)
    features = []
    for _, r in emap.iterrows():
        try:
            features.append({
                "type": "Feature",
                "id": r["name"],
                "properties": {"name": r["name"]},
                "geometry": mapping(r["geom"])
            })
        except Exception:
            continue
    if features:
        emap_geojson = {"type": "FeatureCollection", "features": features}

# merge des centroïdes si disponibles
if emap_centroids is not None and "name" in dc_eu.columns:
    dc_eu = dc_eu.merge(emap_centroids, on="name", how="left")

# rayon pour les cercles
if "nb_dc" in dc_eu.columns:
    dc_eu["radius"] = np.sqrt(dc_eu["nb_dc"].clip(lower=0).fillna(0)) * 4 + 4

# ------------------------- serveur -------------------------
def server(input, output, session):

    # ====== Simulation 1 ======
    @reactive.calc
    def consommation_totale():
        nb_dc = input.nb_dc()
        facteur = input.facteur_charge() / 100.0
        df = dc_data.copy()
        df["Conso_Totale"] = consommation_actuelle + (df["Conso"] * nb_dc * facteur)
        return df

    @render.text
    def facteur_charge_affiche():
        return f"⚙️ Facteur de charge appliqué : {input.facteur_charge()} %"

    @output
    @sw.render_widget
    def energiePlot():
        conso_hist2 = conso_hist.assign(Type="Consommation").rename(columns={"Conso": "Value"})
        prod_hist2  = prod_hist.assign(Type="Production").rename(columns={"Prod": "Value"})
        conso_proj  = conso_p.assign(Type="Consommation").rename(columns={"Ref": "Value"})
        prod_proj   = prod_p.assign(Type="Production").rename(columns={"Ref": "Value"})

        data_lines = pd.concat([
            conso_hist2[["Annee","Value","Type"]],
            prod_hist2 [["Annee","Value","Type"]],
            conso_proj [["Annee","Value","Type"]],
            prod_proj  [["Annee","Value","Type"]],
        ])
        data_ribbons = pd.concat([
            conso_p[["Annee"]].assign(ymin=conso_p["Min"], ymax=conso_p["Max"], Type="Consommation"),
            prod_p [["Annee"]].assign(ymin=prod_p ["Min"], ymax=prod_p ["Max"], Type="Production"),
        ])

        fig = go.Figure()
        for typ, color in [("Consommation", "rgba(0,114,178,0.2)"), ("Production", "rgba(0,158,115,0.2)")]:
            d = data_ribbons[data_ribbons["Type"] == typ]
            fig.add_trace(go.Scatter(
                x=list(d["Annee"]) + list(d["Annee"][::-1]),
                y=list(d["ymax"]) + list(d["ymin"][::-1]),
                fill="toself", mode="none", fillcolor=color, hoverinfo="skip", name=f"Zone {typ}"
            ))
        for typ, col in [("Consommation", "#0072B2"), ("Production", "#009E73")]:
            d = data_lines[data_lines["Type"] == typ]
            fig.add_trace(go.Scatter(x=d["Annee"], y=d["Value"], mode="lines", name=typ,
                                     line=dict(color=col, width=2)))
        fig.add_vline(x=2025, line_dash="dash", line_color="gray")
        fig.add_vline(x=2035, line_dash="dash", line_color="gray")
        fig.update_layout(height=420, margin=dict(l=10,r=10,t=30,b=10), legend_title_text="",
                          xaxis_title=None, yaxis_title="TWh")
        return fig

    @output
    @sw.render_widget
    def energy_plot():
        conso_tot = consommation_totale()
        nb_dc = input.nb_dc()
        conso_sub = conso_p[(conso_p["Annee"] >= 2025) & (conso_p["Annee"] <= 2035)]

        p = go.Figure()
        p.add_trace(go.Scatter(
            x=list(production_data["Annee"]) + list(production_data["Annee"][::-1]),
            y=list(production_data["Max"])   + list(production_data["Min"][::-1]),
            fill="toself", mode="none", fillcolor="rgba(34,109,104,0.2)",
            line=dict(color="rgba(0,0,0,0)"), name="Zone de production", hoverinfo="skip"
        ))
        p.add_trace(go.Scatter(x=production_data["Annee"], y=production_data["Ref"], mode="lines",
                               line=dict(color="#009E73", width=4), name="Projection de production de référence"))
        p.add_trace(go.Scatter(x=production_data["Annee"], y=production_data["Min"], mode="lines",
                               line=dict(color="#009E73", width=2, dash="dash"),
                               name="Projection de production minimum de référence"))
        p.add_trace(go.Scatter(x=production_data["Annee"], y=production_data["Max"], mode="lines",
                               line=dict(color="#009E73", width=2, dash="dash"),
                               name="Projection de production maximum de référence"))

        p.add_trace(go.Scatter(x=consommation_data["Annee"], y=consommation_data["Ref"], mode="lines",
                               line=dict(color="#0072B2", width=4), name="Projection de consommation de référence"))
        p.add_trace(go.Scatter(
            x=list(conso_sub["Annee"]) + list(conso_sub["Annee"][::-1]),
            y=list(conso_sub["Max"])   + list(conso_sub["Min"][::-1]),
            fill="toself", mode="none", fillcolor="rgba(34,109,104,0.2)",
            line=dict(color="rgba(0,0,0,0)"), name="Zone de consommation", hoverinfo="skip"
        ))
        p.add_trace(go.Scatter(
            x=conso_tot["Annee"], y=conso_tot["Conso_Totale"], mode="markers+text",
            text=conso_tot["Annee"], textposition="top center",
            marker=dict(color="#D46F4D", size=14, symbol="diamond-open-dot", line=dict(color="#D46F4D", width=3)),
            name=f"Consommation simulée : Consommation 2024 + consommation de {nb_dc} DC par palier",
            hovertemplate="<b>Consommation simulée</b><br>Année: %{x}<br>Consommation: %{y:.1f} TWh/an<extra></extra>"
        ))
        p.update_layout(
            xaxis=dict(title="Année", showgrid=True, gridcolor="#e9ecef", tickmode="linear", dtick=1),
            yaxis=dict(title="Énergie (TWh/an)", showgrid=True, gridcolor="#e9ecef"),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
            margin=dict(t=20, r=40, b=100, l=60), height=460,
        )
        return p

    @render.text
    def info_conso_dc():
        nb_dc = input.nb_dc()
        facteur = input.facteur_charge() / 100.0
        conso_dc_2025 = dc_data.loc[0, "Conso"] * nb_dc * facteur
        return f"{conso_dc_2025:.3f} TWh"

    @render.text
    def info_conso_totale():
        nb_dc = input.nb_dc()
        facteur = input.facteur_charge() / 100.0
        conso_dc_2035 = dc_data.loc[dc_data["Annee"] == 2035, "Conso"].iloc[0] * nb_dc * facteur
        conso_totale_2035 = consommation_actuelle + conso_dc_2035
        return f"{conso_totale_2035:.0f} TWh"

    energy_per_dc_gwh = 8700

    @render.text
    def wind_surface():
        production_par_eolienne_gwh = 6.8
        surface_par_eolienne_km2 = 0.78
        total_gwh = input.nb_dc() * energy_per_dc_gwh
        nb_eoliennes = total_gwh / production_par_eolienne_gwh
        surface_km2 = nb_eoliennes * surface_par_eolienne_km2
        pct_fr = (surface_km2 / AURA_KM2) * 100
        return f"≈ {surface_km2:,.2f} km² — soit {pct_fr:.3f} % de la surface de la France".replace(",", " ")

    @render.text
    def solar_surface():
        taille_m2 = 140
        production_totale_twh_fr = 25
        nb_installations_fr = 600_000
        prod_par_install_twh = production_totale_twh_fr / nb_installations_fr
        total_twh = (input.nb_dc() * energy_per_dc_gwh) / 1000.0
        nb_inst = total_twh / prod_par_install_twh
        surface_km2 = (nb_inst * taille_m2) / 1e6
        pct_fr = (surface_km2 / AURA_KM2) * 100
        return f"≈ {surface_km2:,.2f} km² — soit {pct_fr:.3f} % de la surface de la France".replace(",", " ")

    @output
    @render.ui
    def surface_info():
        return ui.HTML("""
            <p><em><strong>Note :</strong> La surface indiquée pour l'éolien correspond à la surface totale mobilisée (espacement, sécurité), qui n'est pas entièrement artificialisée.</em></p>
            <p><em>Pour le solaire, la surface correspond à une estimation plus proche de la surface réellement artificialisée au sol.</em></p>
        """)

    capacities = {"nuke": 8.2, "hydro": 1.5, "wind": 0.004, "solar": 0.00004, "coal": 3.0, "bio": 0.1}

    def calculate_equivalent(source: str) -> int:
        nb_dc = input.nb_dc() or 1
        facteur = input.facteur_charge() / 100.0
        conso_2035_twh = float(dc_data.loc[dc_data["Annee"] == 2035, "Conso"].iloc[0] * nb_dc * facteur)
        return int(round(conso_2035_twh / capacities[source]))

    @render.text
    def nuke_value():  return fmt_int(calculate_equivalent("nuke"))
    @render.text
    def hydro_value(): return fmt_int(calculate_equivalent("hydro"))
    @render.text
    def coal_value():  return fmt_int(calculate_equivalent("coal"))
    @render.text
    def wind_value():  return fmt_int(calculate_equivalent("wind"))
    @render.text
    def solar_value(): return fmt_int(calculate_equivalent("solar"))
    @render.text
    def bio_value():   return fmt_int(calculate_equivalent("bio"))

    @render.text
    def nuke_pct_total():
        nuke_eq = calculate_equivalent("nuke")
        pct = min(100.0, (nuke_eq / NUC_TOTAL_FR) * 100.0)
        return f"sur {NUC_TOTAL_FR} réacteurs en France — soit {pct:.1f} % du total"

    # ====== Simulation 2 ======
    consommation_habitants = pd.DataFrame({
        "Pays": [
            "Mondial", "France (68,29 M)", "Qatar (2,66 M)", "Mali (28,24 M)",
            "Etats-Unis (340,1 M)", "Chine (1 411,41 M)", "Inde (1438,60 M)", "Russie (143,8 M)"
        ],
        "Conso_MWh": [2.674, 2.223, 226.848, 0.173, 12.705, 6.113, 1.395, 6.961],
    })
    autres_pays = consommation_habitants[consommation_habitants["Pays"] != "Mondial"].copy().sort_values("Pays")
    consommation_habitants = pd.concat(
        [consommation_habitants[consommation_habitants["Pays"] == "Mondial"], autres_pays],
        ignore_index=True
    )

    dc_paliers = pd.DataFrame({
        "Nom": ["15 MW", "200 MW", "400 MW", "1 GW"],
        "Puissance_MW": [15, 200, 400, 1000],
    })
    dc_paliers["Conso_MWh_An"] = dc_paliers["Puissance_MW"] * 24 * 365

    palette_colors = ["#60CCEC", "#FEE552", "#A1C740", "#E75C38", "#FB7A25", "#084C64", "#720019", "#226D68"]
    dc_1gw_conso = 8_760_000  # MWh/an

    @render.text
    def france_1gw():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("France"), "Conso_MWh"].values
        return fmt_int(dc_1gw_conso / v[0]) if len(v) else ""

    @render.text
    def qatar_1gw():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Qatar"), "Conso_MWh"].values
        return fmt_int(dc_1gw_conso / v[0]) if len(v) else ""

    @render.text
    def mali_1gw():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Mali"), "Conso_MWh"].values
        return fmt_int(dc_1gw_conso / v[0]) if len(v) else ""

    @render.text
    def france_pop(): return "Population totale : 68 290 000"
    @render.text
    def qatar_pop():  return "Population totale : 2 660 000"
    @render.text
    def mali_pop():   return "Population totale : 28 243 609"

    @render.text
    def france_pct():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("France"), "Conso_MWh"].values
        hab = dc_1gw_conso / v[0]; pct = round(hab / 68_290_000 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @render.text
    def qatar_pct():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Qatar"), "Conso_MWh"].values
        hab = dc_1gw_conso / v[0]; pct = round(hab / 2_660_000 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @render.text
    def mali_pct():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Mali"), "Conso_MWh"].values
        hab = dc_1gw_conso / v[0]; pct = round(hab / 28_243_609 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @output
    @render.ui
    def checkbox_group_conso():
        return ui.input_checkbox_group(
            "pays_selection",
            "Choisissez les pays (Population totale en Million) à afficher :",
            choices=list(consommation_habitants["Pays"].values),
            selected=["Mondial"],
        )

    @output
    @sw.render_widget
    def barplot():
        sel = input.pays_selection() or ["Mondial"]
        selected = consommation_habitants[consommation_habitants["Pays"].isin(sel)].copy()
        if selected.empty:
            return px.bar(title="Sélectionnez au moins un profil")

        comparison = (
            selected.assign(key=1)
            .merge(dc_paliers.assign(key=1), on="key")
            .drop(columns=["key"])
        )
        comparison["Habitants_equivalents"] = comparison["Conso_MWh_An"] / comparison["Conso_MWh"]
        comparison["DC"] = pd.Categorical(comparison["Nom"], categories=dc_paliers["Nom"], ordered=True)
        comparison["NomPays"] = comparison["Pays"].str.replace(r" \((.*)\)", "", regex=True) + \
                                " (" + comparison["Conso_MWh"].astype(str) + " MWh/an)"

        max_val = float(comparison["Habitants_equivalents"].max())
        if max_val >= 1e6:
            scale, y_title, suf = 1e6, "Nombre d'habitants équivalents (en millions)", " millions"
        elif max_val >= 1e3:
            scale, y_title, suf = 1e3, "Nombre d'habitants équivalents (en milliers)", " milliers"
        else:
            scale, y_title, suf = 1, "Nombre d'habitants équivalents", ""
        comparison["Habitants_equivalents_scaled"] = comparison["Habitants_equivalents"] / scale

        uniq = list(dict.fromkeys(comparison["NomPays"]))
        colors = {p: palette_colors[i % len(palette_colors)] for i, p in enumerate(uniq)}

        fig = px.bar(comparison, x="DC", y="Habitants_equivalents_scaled", color="NomPays",
                     color_discrete_map=colors, title="Nombre d'habitants équivalents par palier")
        fig.update_layout(xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group", height=460)
        fig.update_traces(hovertemplate=f"Profil : %{legendgroup}<br>Palier : %{x}<br>Habitants équivalents : %{y:,.2f}{suf}<extra></extra>")
        return fig

    def _collect_personal_entries():
        rows = []
        for i in (1, 2):
            nom = getattr(input, f"nom_perso_{i}")()
            val = getattr(input, f"val_perso_{i}")()
            unit = getattr(input, f"unit_perso_{i}")()
            if not nom or val is None:
                continue
            if unit == "kWh/an":
                mwh = val / 1000.0
            elif unit == "MWh/an":
                mwh = val
            else:
                mwh = val * 1000.0
            rows.append({"Pays": nom, "Conso_MWh": mwh})
        return pd.DataFrame(rows)

    @output
    @sw.render_widget
    def barplot_personalisee():
        custom = _collect_personal_entries()
        if custom.empty:
            return px.bar(title="Ajoutez des entrées dans la sidebar")

        comparison = (
            custom.assign(key=1)
            .merge(dc_paliers.assign(key=1), on="key")
            .drop(columns=["key"])
        )
        comparison["Habitants_equivalents"] = comparison["Conso_MWh_An"] / comparison["Conso_MWh"]
        comparison["DC"] = pd.Categorical(comparison["Nom"], categories=dc_paliers["Nom"], ordered=True)

        max_val = float(comparison["Habitants_equivalents"].max())
        if max_val >= 1e6:
            scale, y_title, suf = 1e6, "Nombre d'individus équivalents (en millions)", " millions"
        elif max_val >= 1e3:
            scale, y_title, suf = 1e3, "Nombre d'individus équivalents (en milliers)", " milliers"
        else:
            scale, y_title, suf = 1, "Nombre d'individus équivalents", ""
        comparison["Habitants_equivalents_scaled"] = comparison["Habitants_equivalents"] / scale

        fig = px.bar(comparison, x="DC", y="Habitants_equivalents_scaled", color="Pays",
                     title="Nombre d'individus équivalents — projections Data One")
        fig.update_layout(xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group", height=420)
        fig.update_traces(hovertemplate=f"Nom : %{legendgroup}<br>Palier : %{x}<br>Habitants équivalents : %{y:,.2f}{suf}<extra></extra>")
        return fig

    # ====== DC en Europe (jointure fond + cercles centroïdes) ======
    @output
    @sw.render_widget
    def eu_map():
        df = dc_eu.copy()

        if emap_geojson is not None and "dc_per_million" in df.columns and "name" in df.columns:
            # Choroplèthe par GeoJSON (clé = properties.name)
            fig = px.choropleth(
                df, geojson=emap_geojson,
                locations="name", featureidkey="properties.name",
                color="dc_per_million", color_continuous_scale="Blues",
                labels={"dc_per_million": "DC / million"}
            )
            fig.update_traces(marker_line_color="white", marker_line_width=0.6)
            fig.update_geos(fitbounds="locations", projection_type="natural earth", visible=False)
        else:
            # Fallback (noms de pays)
            fig = go.Figure()
            if {"name", "dc_per_million"}.issubset(df.columns):
                fig.add_trace(go.Choropleth(
                    locations=df["name"], locationmode="country names",
                    z=df["dc_per_million"], colorscale="Blues",
                    marker_line_color="white", marker_line_width=0.6,
                    colorbar_title="DC / million",
                    hovertemplate="<b>%{location}</b><br>DC / million : %{z:.2f}<extra></extra>"
                ))
            fig.update_geos(scope="europe", projection_type="natural earth",
                            showcountries=True, countrycolor="white",
                            showland=True, landcolor="#f0f2f5")

        # Cercles proportionnels (centroïdes si dispos / sinon lat/lon existants)
        mask = df["nb_dc"].notna()
        if "lat" in df.columns and "lon" in df.columns:
            mask &= df["lat"].notna() & df["lon"].notna()
        if mask.any():
            d = df.loc[mask].copy()
            if "radius" not in d.columns:
                d["radius"] = np.sqrt(d["nb_dc"].clip(lower=0).fillna(0)) * 4 + 4
            hover = (
                "<b>" + d["name"].astype(str) + "</b><br>" +
                "Nombre de DC : " + d["nb_dc"].fillna(0).astype(int).astype(str) + "<br>" +
                "Population : " + d["pop"].fillna(0).astype(int).map(lambda x: f"{x:,}".replace(",", " ")) +
                "<extra></extra>"
            )
            fig.add_trace(go.Scattergeo(
                lon=d["lon"], lat=d["lat"], text=hover, hoverinfo="text",
                mode="markers", name="",
                marker=dict(size=d["radius"], color="#1f6feb", opacity=0.65,
                            line=dict(width=1, color="white")),
            ))

        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=460,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h"),
        )
        return fig

    @output
    @sw.render_widget
    def barPlot_eu():
        df = dc_eu.copy()
        if "nb_dc" in df.columns and "name" in df.columns:
            tot = float(df["nb_dc"].sum()) if df["nb_dc"].notna().any() else 0.0
            if tot <= 0:
                return px.bar(title="Données insuffisantes")
            df = df.assign(Share=(df["nb_dc"] / tot) * 100).sort_values("Share")
            fig = px.bar(
                df, x="Share", y="name",
                orientation="h", color="Share", color_continuous_scale="Blues",
                labels={"Share": "", "name": ""},
            )
            fig.update_layout(
                coloraxis_showscale=False,
                xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#eaeef3"),
                yaxis=dict(showgrid=False),
                margin=dict(l=120, r=30, t=20, b=30),
                height=460,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                annotations=[dict(
                    x=0, y=-0.2, xref="paper", yref="paper",
                    showarrow=False, text="Source : ICIS (DataCentreMap, Statista)",
                    font=dict(size=12, color="gray")
                )],
            )
            return fig
        return px.bar(title="Données insuffisantes")

    @output
    @sw.render_widget
    def dc_demand_plot():
        df = pd.DataFrame({"Année": ["2024","2035"], "TWh": [96, 236]})
        fig = px.bar(df, x="Année", y="TWh",
                     color="Année", color_discrete_map={"2024": "#3B556D", "2035": "#5FC2BA"})
        fig.update_traces(opacity=0.9, text=df["TWh"].astype(str)+" TWh", textposition="outside")
        fig.update_layout(
            yaxis_title="Demande (TWh)", xaxis_title=None,
            margin=dict(l=40, r=20, t=10, b=40),
            height=420, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        fig.update_yaxes(range=[0, float(df["TWh"].max()) * 1.25])
        return fig


# -------- App --------
app = App(app_ui, server)
