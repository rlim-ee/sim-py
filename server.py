# server.py — Simulations + Europe (RDS) + thème clair/sombre
from __future__ import annotations

from shiny import App, reactive, render, ui
import shinywidgets as sw

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --- RDS (dc_europe.rds)
try:
    import pyreadr
except Exception:  # pragma: no cover
    pyreadr = None

# ============================
# Import UI
# ============================
from ui import app_ui


# ============================
# Utilitaires / thème
# ============================
def is_dark_input(input) -> bool:
    """Renvoie True si l'utilisateur a choisi le mode sombre (radio id='theme_mode')."""
    try:
        return (input.theme_mode() or "dark") == "dark"
    except Exception:
        return False


# ============================
# Données de base — Simulation 1
# ============================
consommation_actuelle = 442  # TWh (2025)

dc_data = pd.DataFrame({
    "Annee": [2025, 2026, 2028, 2035],
    "Conso": [0.131400, 1.752000, 3.504000, 8.760000],  # TWh par DC
})

production_data = pd.DataFrame({
    "Annee": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    "Min":   [538,   550,   560,   565,   568,   570,   572,   575,   578,   580,   585],
    "Max":   [538,   570,   580,   590,   595,   600,   610,   615,   620,   628,   636],
    "Ref":   [538,   560,   570,   577.5, 581.5, 585,   591,   595,   599,   604,   610.5],
})

consommation_data = pd.DataFrame({
    "Annee": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    "Ref":   [442,  455,  468,  481,  494,  508,  514,  520,  526,  532,  538],
})

# Tendances 2000–2050
conso_hist = pd.DataFrame({
    "Annee": [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
    "Conso": [425,434,434,449,460,464,468,467,481,472,499,472,487,495,463,474,482,481,477,472,449,472,454,439,442],
})
conso_p = pd.DataFrame({
    "Annee": list(range(2025, 2051)),
    "Ref":   [442,455,468,481,494,508,514,520,526,532,538,544,550,556,562,568,574,580,586,592,598,604,610,616,622,628],
})
n = len(conso_p)
delta = np.linspace(0, 50, n)
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


# ============================
# Données — Simulation 2
# ============================
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


# ============================
# Europe — chargement RDS
# ============================
def load_dc_europe_df(path: str) -> pd.DataFrame:
    if pyreadr is None:
        raise RuntimeError("Le module 'pyreadr' n'est pas installé. Fais: pip install pyreadr")

    res = pyreadr.read_r(path)
    df = next(iter(res.values()))

    # Harmoniser -> Country, nb_dc, pop
    colmap = {
        "name": "Country", "pays": "Country", "country": "Country",
        "nb_dc": "nb_dc", "dc_count": "nb_dc",
        "pop": "pop", "population": "pop",
        "country_id": "iso2",
    }
    for k, v in colmap.items():
        if k in df.columns and v not in df.columns:
            df.rename(columns={k: v}, inplace=True)

    for c in ["nb_dc", "pop"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Indicateurs dérivés
    if "dc_per_million" not in df.columns and {"nb_dc", "pop"}.issubset(df.columns):
        df["dc_per_million"] = df["nb_dc"] / (df["pop"] / 1_000_000)

    if "Share" not in df.columns and "nb_dc" in df.columns:
        total = float(df["nb_dc"].sum())
        df["Share"] = (df["nb_dc"] / total) * 100.0

    # Taille (utile si plus tard tu ajoutes lat/lon)
    if "nb_dc" in df.columns:
        df["radius"] = np.sqrt(df["nb_dc"].astype(float)).fillna(0) * 4 + 4

    return df

# --- Charger dc_europe.rds
rds_path = "data/dc_europe.rds"
res = pyreadr.read_r(rds_path)
dc_eu = next(iter(res.values()))

# Harmoniser les colonnes
if "name" in dc_eu.columns and "Country" not in dc_eu.columns:
    dc_eu.rename(columns={"name": "Country"}, inplace=True)
if "nb_dc" not in dc_eu.columns:
    raise ValueError("Le fichier RDS doit contenir une colonne 'nb_dc'.")
if "pop" not in dc_eu.columns:
    raise ValueError("Le fichier RDS doit contenir une colonne 'pop' (population en habitants).")

# --- ISO-2 -> ISO-3 (selon country_id)
iso2_to_iso3 = {
    "AT":"AUT","BE":"BEL","BG":"BGR","CY":"CYP","CZ":"CZE","DE":"DEU","DK":"DNK","CH":"CHE",
    "FI":"FIN","FR":"FRA","EE":"EST","EL":"GRC","GR":"GRC","ES":"ESP","IE":"IRL","HR":"HRV",
    "HU":"HUN","IT":"ITA","NL":"NLD","LT":"LTU","LU":"LUX","LV":"LVA","MT":"MLT","NO":"NOR",
    "PL":"POL","PT":"PRT","RO":"ROU","SE":"SWE","SI":"SVN","SK":"SVK","TR":"TUR","UA":"UKR",
    "GB":"GBR","UK":"GBR","IS":"ISL","AL":"ALB","BA":"BIH","MK":"MKD","RS":"SRB","MD":"MDA",
    "BY":"BLR"
}
if "iso" not in dc_eu.columns:
    if "country_id" in dc_eu.columns:
        dc_eu["iso"] = dc_eu["country_id"].map(iso2_to_iso3)
    else:
        # si pas de country_id, on laisse iso absent (on pourra quand même buller)
        pass

# --- Centroïdes (lat/lon) par ISO-3 (approx.)
centroids = pd.DataFrame([
    ("AUT", 47.516, 14.550), ("BEL", 50.833,   4.000), ("BGR", 42.733, 25.485),
    ("CYP", 35.126, 33.430), ("CZE", 49.817, 15.473), ("DEU", 51.165, 10.451),
    ("DNK", 56.263,  9.501), ("CHE", 46.818,  8.227), ("FIN", 61.924, 25.748),
    ("FRA", 46.227,  2.213), ("EST", 58.595, 25.013), ("GRC", 39.074, 21.824),
    ("ESP", 40.463, -3.749), ("IRL", 53.142, -7.692), ("HRV", 45.100, 15.200),
    ("HUN", 47.162, 19.503), ("ITA", 41.871, 12.567), ("NLD", 52.132,  5.291),
    ("POL", 51.919, 19.145), ("PRT", 39.399, -8.224), ("ROU", 45.943, 24.966),
    ("SWE", 60.128, 18.643), ("NOR", 60.472,  8.468), ("LTU", 55.169, 23.881),
    ("LVA", 56.879, 24.603), ("LUX", 49.815,  6.129), ("MLT", 35.937, 14.375),
    ("SVN", 46.152, 14.995), ("SVK", 48.669, 19.699), ("TUR", 38.963, 35.243),
    ("UKR", 48.379, 31.165), ("GBR", 55.378, -3.436), ("ISL", 64.963,-19.020),
    ("ALB", 41.153, 20.168), ("BIH", 43.915, 17.679), ("MKD", 41.608, 21.745),
    ("SRB", 44.016, 21.006), ("MDA", 47.411, 28.369), ("BLR", 53.709, 27.953)
], columns=["iso","lat","lon"])

if "iso" in dc_eu.columns:
    dc_eu = dc_eu.merge(centroids, on="iso", how="left")

# Métriques dérivées
if "dc_per_million" not in dc_eu.columns and {"nb_dc","pop"}.issubset(dc_eu.columns):
    dc_eu["dc_per_million"] = dc_eu["nb_dc"] / (dc_eu["pop"] / 1_000_000)

# Taille des cercles (racine pour rester lisible)
if "nb_dc" in dc_eu.columns:
    dc_eu["radius"] = np.sqrt(dc_eu["nb_dc"].astype(float)).fillna(0) * 4 + 4



# ============================
# SERVER
# ============================
def server(input, output, session):

    # ---- DF Europe (RDS)
    rds_path = "data/dc_europe.rds"
    dc_eu_val = reactive.Value(load_dc_europe_df(rds_path))

    @reactive.calc
    def dc_eu():
        return dc_eu_val.get()

    # ======================================================
    # Simulation 1
    # ======================================================
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

    # ---- Tendances 2000–2050
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
        for typ, line_color in [("Consommation", "#0072B2"), ("Production", "#009E73")]:
            d = data_lines[data_lines["Type"] == typ]
            fig.add_trace(go.Scatter(x=d["Annee"], y=d["Value"], mode="lines", name=typ,
                                     line=dict(color=line_color, width=2)))

        fig.add_vline(x=2025, line_dash="dash", line_color="gray")
        fig.add_vline(x=2035, line_dash="dash", line_color="gray")
        fig.update_layout(height=420, margin=dict(l=10,r=10,t=30,b=10), legend_title_text="",
                          xaxis_title=None, yaxis_title="TWh")
        return fig

    # ---- Graphique principal (2025–2035)
    @output
    @sw.render_widget
    def energy_plot():
        conso_tot = consommation_totale()
        conso_sub = conso_p[(conso_p["Annee"] >= 2025) & (conso_p["Annee"] <= 2035)]

        p = go.Figure()
        # Production
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
        # Consommation
        p.add_trace(go.Scatter(x=consommation_data["Annee"], y=consommation_data["Ref"], mode="lines",
                               line=dict(color="#0072B2", width=4), name="Projection de consommation de référence"))
        p.add_trace(go.Scatter(
            x=list(conso_sub["Annee"]) + list(conso_sub["Annee"][::-1]),
            y=list(conso_sub["Max"])   + list(conso_sub["Min"][::-1]),
            fill="toself", mode="none", fillcolor="rgba(34,109,104,0.2)",
            line=dict(color="rgba(0,0,0,0)"), name="Zone de consommation", hoverinfo="skip"
        ))
        # Points simulés
        p.add_trace(go.Scatter(
            x=conso_tot["Annee"], y=conso_tot["Conso_Totale"], mode="markers+text",
            text=conso_tot["Annee"], textposition="top center",
            marker=dict(color="#D46F4D", size=14, symbol="diamond-open-dot", line=dict(color="#D46F4D", width=3)),
            name="Consommation simulée : Consommation 2024 + conso DC par palier",
            hovertemplate="<b>Consommation simulée</b><br>Année: %{x}<br>Consommation: %{y:.1f} TWh/an<extra></extra>"
        ))
        p.update_layout(
            xaxis=dict(title="Année", showgrid=True, gridcolor="#e9ecef", tickmode="linear", dtick=1, tickfont=dict(size=12)),
            yaxis=dict(title="Énergie (TWh/an)", showgrid=True, gridcolor="#e9ecef", tickfont=dict(size=12)),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center", font=dict(size=12)),
            plot_bgcolor="#ffffff", paper_bgcolor="#ffffff", hovermode="closest",
            margin=dict(t=20, r=40, b=100, l=60), height=460,
        )
        return p

    # ---- Infos
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

    # ---- Équivalents 2035
    energy_per_dc_gwh = 8700  # GWh par DC

    AURA_KM2 = 67_711 
    N_REACTEURS_FR = 56

    @render.text
    def wind_surface():
        production_par_eolienne_gwh = 6.8
        surface_par_eolienne_km2 = 0.78
        total_gwh = input.nb_dc() * energy_per_dc_gwh
        nb_eoliennes = total_gwh / production_par_eolienne_gwh
        surface_km2 = nb_eoliennes * surface_par_eolienne_km2
        pct_fr = (surface_km2 / AURA_KM2) * 100
        return f"≈ {surface_km2:,.2f} km² occupés — soit {pct_fr:.2f} % de la surface de l'Auvergne-Rhône-Alpes".replace(",", " ")

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
        return f"≈ {surface_km2:,.2f} km² occupés — soit {pct_fr:.2f} % de l'Auvergne-Rhône-Alpes".replace(",", " ")

    @output
    @render.ui
    def surface_info():
        return ui.HTML(
            """
            <p><em><strong>Note :</strong> La surface indiquée pour l'éolien correspond à la surface totale mobilisée (espacement, sécurité), qui n'est pas entièrement artificialisée.</em></p>
            <p><em>Pour le solaire, la surface correspond à une estimation plus proche de la surface réellement artificialisée au sol.</em></p>
            """
        )

    capacities = {
        "nuke": 8.2,       # TWh/an par réacteur
        "hydro": 1.5,      # TWh/an par barrage
        "wind": 0.004,     # TWh/an par éolienne
        "solar": 0.00004,  # TWh/an par installation PV
        "coal": 3.0,       # TWh/an par centrale
        "bio": 0.1,        # TWh/an par centrale
    }

    def calculate_equivalent(source: str) -> int:
        nb_dc = input.nb_dc() or 1
        facteur = input.facteur_charge() / 100.0
        conso_2035_twh = float(dc_data.loc[dc_data["Annee"] == 2035, "Conso"].iloc[0] * nb_dc * facteur)
        return int(round(conso_2035_twh / capacities[source]))

    @render.text
    def nuke_value():  return f"{calculate_equivalent('nuke'):,}".replace(",", " ")

    @render.text
    def hydro_value(): return f"{calculate_equivalent('hydro'):,}".replace(",", " ")

    @render.text
    def coal_value():  return f"{calculate_equivalent('coal'):,}".replace(",", " ")

    @render.text
    def wind_value():  return f"{calculate_equivalent('wind'):,}".replace(",", " ")

    @render.text
    def solar_value(): return f"{calculate_equivalent('solar'):,}".replace(",", " ")

    @render.text
    def bio_value():   return f"{calculate_equivalent('bio'):,}".replace(",", " ")

    @render.text
    def nuke_pct_total():
        nuke_eq = calculate_equivalent("nuke")
        pct = (nuke_eq / N_REACTEURS_FR) * 100
        return f"{nuke_eq} au total — soit {pct:.2f} % du nombre total"

    # ======================================================
    # Simulation 2
    # ======================================================
    @render.text
    def france_1gw():
        france_mwh = consommation_habitants.loc[
            consommation_habitants["Pays"].str.contains("France"), "Conso_MWh"
        ].values
        return f"{int(round(dc_1gw_conso / france_mwh[0])):,}".replace(",", " ") if len(france_mwh) else ""

    @render.text
    def qatar_1gw():
        qatar_mwh = consommation_habitants.loc[
            consommation_habitants["Pays"].str.contains("Qatar"), "Conso_MWh"
        ].values
        return f"{int(round(dc_1gw_conso / qatar_mwh[0])):,}".replace(",", " ") if len(qatar_mwh) else ""

    @render.text
    def mali_1gw():
        mali_mwh = consommation_habitants.loc[
            consommation_habitants["Pays"].str.contains("Mali"), "Conso_MWh"
        ].values
        return f"{int(round(dc_1gw_conso / mali_mwh[0])):,}".replace(",", " ") if len(mali_mwh) else ""

    @render.text
    def france_pop(): return "Population totale : 68 290 000"

    @render.text
    def qatar_pop():  return "Population totale : 2 660 000"

    @render.text
    def mali_pop():   return "Population totale : 28 243 609"

    @render.text
    def france_pct():
        france_mwh = consommation_habitants.loc[
            consommation_habitants["Pays"].str.contains("France"), "Conso_MWh"
        ].values
        habitants = dc_1gw_conso / france_mwh[0]
        pct = round(habitants / 68_290_000 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @render.text
    def qatar_pct():
        qatar_mwh = consommation_habitants.loc[
            consommation_habitants["Pays"].str.contains("Qatar"), "Conso_MWh"
        ].values
        habitants = dc_1gw_conso / qatar_mwh[0]
        pct = round(habitants / 2_660_000 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @render.text
    def mali_pct():
        mali_mwh = consommation_habitants.loc[
            consommation_habitants["Pays"].str.contains("Mali"), "Conso_MWh"
        ].values
        habitants = dc_1gw_conso / mali_mwh[0]
        pct = round(habitants / 28_243_609 * 100, 2)
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
        selected_data = consommation_habitants[consommation_habitants["Pays"].isin(sel)].copy()
        if selected_data.empty:
            return px.bar(title="Sélectionnez au moins un profil")

        comparison = (
            selected_data.assign(key=1)
            .merge(dc_paliers.assign(key=1), on="key")
            .drop(columns=["key"])
        )
        comparison["Habitants_equivalents"] = comparison["Conso_MWh_An"] / comparison["Conso_MWh"]
        comparison["DC"] = pd.Categorical(comparison["Nom"], categories=dc_paliers["Nom"], ordered=True)
        comparison["NomPays"] = comparison["Pays"].str.replace(r" \((.*)\)", "", regex=True) + \
                                " (" + comparison["Conso_MWh"].astype(str) + " MWh/an)"

        max_val = float(comparison["Habitants_equivalents"].max())
        if max_val >= 1e6:
            scale_factor, y_title, hover_suffix = 1e6, "Nombre d'habitants équivalents (en millions)", " millions"
        elif max_val >= 1e3:
            scale_factor, y_title, hover_suffix = 1e3, "Nombre d'habitants équivalents (en milliers)", " milliers"
        else:
            scale_factor, y_title, hover_suffix = 1, "Nombre d'habitants équivalents", ""
        comparison["Habitants_equivalents_scaled"] = comparison["Habitants_equivalents"] / scale_factor

        unique_pays = list(dict.fromkeys(comparison["NomPays"]))
        colors = {p: palette_colors[i % len(palette_colors)] for i, p in enumerate(unique_pays)}

        fig = px.bar(
            comparison, x="DC", y="Habitants_equivalents_scaled", color="NomPays",
            color_discrete_map=colors, title="Nombre d'habitants équivalents par palier"
        )
        fig.update_layout(xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group", height=460)
        fig.update_traces(
            hovertemplate="Profil : %{legendgroup}<br>Palier : %{x}<br>"
            "Habitants équivalents : %{y:,.2f}"
            + hover_suffix +
            "<extra></extra>"
            )
        return fig

    # Perso (2 entrées modifiables dans l'UI)
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
        custom_data = _collect_personal_entries()
        if custom_data.empty:
            return px.bar(title="Ajoutez des entrées dans la sidebar")

        comparison = (
            custom_data.assign(key=1)
            .merge(dc_paliers.assign(key=1), on="key")
            .drop(columns=["key"])
        )
        comparison["Habitants_equivalents"] = comparison["Conso_MWh_An"] / comparison["Conso_MWh"]
        comparison["DC"] = pd.Categorical(comparison["Nom"], categories=dc_paliers["Nom"], ordered=True)

        max_val = float(comparison["Habitants_equivalents"].max())
        if max_val >= 1e6:
            scale_factor, y_title, hover_suffix = 1e6, "Nombre d'individus équivalents (en millions)", " millions"
        elif max_val >= 1e3:
            scale_factor, y_title, hover_suffix = 1e3, "Nombre d'individus équivalents (en milliers)", " milliers"
        else:
            scale_factor, y_title, hover_suffix = 1, "Nombre d'individus équivalents", ""
        comparison["Habitants_equivalents_scaled"] = comparison["Habitants_equivalents"] / scale_factor

        fig = px.bar(comparison, x="DC", y="Habitants_equivalents_scaled", color="Pays",
                     title="Nombre d'individus équivalents — projections Data One")
        fig.update_layout(xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group", height=420)
        fig.update_traces(
            hovertemplate="Nom : %{legendgroup}<br>Palier : %{x}<br>"
            "Habitants équivalents : %{y:,.2f}"
            + hover_suffix +
            "<extra></extra>"
            )
        return fig

    # ======================================================
    # Europe — carte + barres + évolution
    # ======================================================
    @output
    @sw.render_widget
    def eu_map():
        df = dc_eu.copy()

        fig = go.Figure()

        # Choroplèthe "DC par million d'hab." si ISO disponible
        if "iso" in df.columns and "dc_per_million" in df.columns:
            fig.add_trace(go.Choropleth(
                locations=df["iso"], z=df["dc_per_million"], locationmode="ISO-3",
                colorscale="Blues", showscale=True, colorbar_title="DC / million",
                marker_line_color="white", marker_line_width=0.6,
                customdata=np.stack([df.get("Country", df["iso"])], axis=-1),
                hovertemplate="<b>%{customdata[0]}</b><br>DC / million : %{z:.2f}<extra></extra>"
            ))

        # Cercles proportionnels au nombre total de DC (si lat/lon dispos)
        if {"lat","lon"}.issubset(df.columns):
            fig.add_trace(go.Scattergeo(
                lon=df["lon"], lat=df["lat"], mode="markers",
                marker=dict(
                    size=df["radius"], color="#FF7B72", opacity=0.70,
                    line=dict(width=0.8, color="white")
                ),
                name="Nombre total de DC",
                customdata=np.stack([df.get("Country", df.get("iso", "")), df["nb_dc"]], axis=-1),
                hovertemplate="<b>%{customdata[0]}</b><br>DC totaux : %{customdata[1]:,}<extra></extra>"
            ))

        fig.update_geos(
            scope="europe",
            showland=True, landcolor="#f0f2f5",
            showcountries=True, countrycolor="white",
            projection_type="natural earth",
            fitbounds="locations"
        )
        fig.update_layout(
            margin=dict(l=0, r=0, t=0, b=0),
            height=460,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h", y=0.01)
        )
        return fig


    @output
    @sw.render_widget
    def barPlot():
        df = dc_eu().copy()
        if "Share" not in df.columns:
            return px.bar(title="Données insuffisantes pour calculer la part (%)")

        dark = is_dark_input(input)
        df = df.sort_values("Share")

        fig = px.bar(
            df, x="Share", y="Country",
            orientation="h",
            color="Share",
            color_continuous_scale="Blues" if not dark else "Teal",
            labels={"Share": "", "Country": ""}
        )
        fig.update_layout(
            coloraxis_showscale=False,
            xaxis=dict(ticksuffix="%", showgrid=True, gridcolor="#eaeef3" if not dark else "#243042"),
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

    @output
    @sw.render_widget
    def dc_demand_plot():
        df = pd.DataFrame({"Année": ["2024","2035"], "TWh": [96, 236]})
        fig = px.bar(df, x="Année", y="TWh",
                     color="Année",
                     color_discrete_map={"2024": "#3B556D", "2035": "#5FC2BA"})
        fig.update_traces(opacity=0.9, text=df["TWh"].astype(str)+" TWh", textposition="outside")
        fig.update_layout(
            yaxis_title="Demande (TWh)", xaxis_title=None,
            margin=dict(l=40, r=20, t=10, b=40),
            height=420,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        fig.update_yaxes(range=[0, float(df["TWh"].max()) * 1.25])
        return fig


# Lancer l'app
app = App(app_ui, server)
