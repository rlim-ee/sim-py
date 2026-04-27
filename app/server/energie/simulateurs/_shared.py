# server/energie/simulateurs/_shared.py — utilitaires communs aux deux simulateurs
#
# Ce fichier centralise tout ce qui est partagé entre le simulateur prédictif
# et le simulateur comparatif, pour éviter la duplication de code :
#
#   - Chargement et mise en cache des CSV de données (paliers DC, historiques
#     et projections de consommation/production nationale)
#   - SimData : conteneur structuré de toutes les séries temporelles
#   - style_fig() : mise en forme Plotly cohérente (thème clair/sombre)
#   - Constantes physiques des filières de production (pour les KPI du simulateur prédictif)
#   - COUNTRY_CONSO : consommation annuelle par habitant selon le pays (MWh/an)
#   - DC_LABELS, DC_PALIER_MWH, DC_1GW_MWH : paliers de puissance du projet Data One
from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

import pandas as pd
import plotly.graph_objects as go

from server._common import is_dark, text_color, grid_color, cached


# Couleurs principales utilisées dans les graphiques des simulateurs
COLORS = {
    "consumption":      "#1F6FEB",   # bleu — consommation nationale
    "consumption_dark": "#58A6FF",   # bleu clair pour le mode sombre
    "production":       "#2EA043",   # vert — production nationale
    "accent":           "#F97316",   # orange — consommation avec DC simulés
}


# =========================================================
# Chargement des fichiers CSV
# =========================================================
def _load_data(app_dir: Path):
    """Lit les cinq CSV nécessaires aux simulateurs."""
    data_dir = app_dir / "www" / "data"
    return {
        "dc_df":         pd.read_csv(data_dir / "dc_paliers.csv"),       # paliers Data One (MW, TWh)
        "conso_hist_df": pd.read_csv(data_dir / "conso_hist.csv"),       # conso nationale historique
        "prod_hist_df":  pd.read_csv(data_dir / "prod_hist.csv"),        # production nationale historique
        "conso_proj_df": pd.read_csv(data_dir / "conso_proj.csv"),       # projections conso RTE
        "prod_proj_df":  pd.read_csv(data_dir / "prod_proj.csv"),        # projections prod RTE
    }


def load_data(app_dir: Path):
    """Charge les CSV une seule fois et les met en cache au niveau du processus."""
    key = f"simulateurs::{Path(app_dir).resolve()}"
    d   = cached(key, lambda: _load_data(app_dir))
    return (
        d["dc_df"], d["conso_hist_df"], d["prod_hist_df"],
        d["conso_proj_df"], d["prod_proj_df"],
    )


@dataclass
class SimData:
    """
    Conteneur de toutes les séries utilisées par les deux sous-modules.
    Les listes dérivées sont extraites des DataFrames pour un accès plus direct
    dans les fonctions de rendu (évite de répéter .tolist() partout).
    """
    dc_df:          pd.DataFrame
    conso_hist_df:  pd.DataFrame
    prod_hist_df:   pd.DataFrame
    conso_proj_df:  pd.DataFrame
    prod_proj_df:   pd.DataFrame

    CONSO_HIST_Y:   list   # années de l'historique consommation
    CONSO_HIST_V:   list   # valeurs de l'historique consommation (TWh)
    PROD_HIST_Y:    list   # années de l'historique production
    PROD_HIST_V:    list   # valeurs de l'historique production (TWh)
    CONSO_PROJ_Y:   list   # années de projection consommation
    CONSO_PROJ_REF: list   # scénario de référence consommation (TWh)
    CONSO_PROJ_MIN: list   # borne basse consommation (TWh)
    CONSO_PROJ_MAX: list   # borne haute consommation (TWh)
    PROD_PROJ_Y:    list   # années de projection production
    PROD_PROJ_REF:  list   # scénario de référence production (TWh)
    PROD_PROJ_MIN:  list   # borne basse production (TWh)
    PROD_PROJ_MAX:  list   # borne haute production (TWh)
    DC_YEARS:       list   # années des paliers Data One
    DC_TWH_DC:      list   # conso par DC à chaque palier (TWh)
    consommation_actuelle: float  # dernière valeur historique (point d'attache de la simulation)


def prepare_sim_data(app_dir: Path) -> SimData:
    """Charge les données et construit le conteneur SimData."""
    dc_df, conso_hist_df, prod_hist_df, conso_proj_df, prod_proj_df = load_data(app_dir)
    return SimData(
        dc_df=dc_df,
        conso_hist_df=conso_hist_df,
        prod_hist_df=prod_hist_df,
        conso_proj_df=conso_proj_df,
        prod_proj_df=prod_proj_df,
        CONSO_HIST_Y   = conso_hist_df["year"].tolist(),
        CONSO_HIST_V   = conso_hist_df["value"].tolist(),
        PROD_HIST_Y    = prod_hist_df["year"].tolist(),
        PROD_HIST_V    = prod_hist_df["value"].tolist(),
        CONSO_PROJ_Y   = conso_proj_df["year"].tolist(),
        CONSO_PROJ_REF = conso_proj_df["ref"].tolist(),
        CONSO_PROJ_MIN = conso_proj_df["min"].tolist(),
        CONSO_PROJ_MAX = conso_proj_df["max"].tolist(),
        PROD_PROJ_Y    = prod_proj_df["year"].tolist(),
        PROD_PROJ_REF  = prod_proj_df["ref"].tolist(),
        PROD_PROJ_MIN  = prod_proj_df["min"].tolist(),
        PROD_PROJ_MAX  = prod_proj_df["max"].tolist(),
        DC_YEARS       = dc_df["year"].tolist(),
        DC_TWH_DC      = dc_df["twh_per_dc"].tolist(),
        consommation_actuelle = conso_hist_df["value"].tolist()[-1],
    )


# =========================================================
# Mise en forme Plotly (thème adaptatif)
# =========================================================
def style_fig(fig: go.Figure, input, *, height: int = 460) -> go.Figure:
    """
    Applique le thème clair/sombre à une figure Plotly.
    À appeler en dernier, après avoir construit toutes les traces.
    """
    dark = is_dark(input)
    tc   = text_color(dark)
    gc   = grid_color(dark)
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Poppins, Arial, sans-serif", size=13, color=tc),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_size=12, font_family="Poppins, Arial, sans-serif"),
        margin=dict(t=40, r=20, b=40, l=40),
        title_font=dict(color=tc),
        legend=dict(
            orientation="h", y=-0.2, x=0.5, xanchor="center",
            bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
            font=dict(color=tc),
        ),
        height=height,
    )
    fig.update_xaxes(showgrid=True, gridcolor=gc,
                     tickfont=dict(color=tc), title_font=dict(color=tc))
    fig.update_yaxes(showgrid=True, gridcolor=gc,
                     tickfont=dict(color=tc), title_font=dict(color=tc))
    return fig


# =========================================================
# Constantes physiques — simulateur prédictif
# =========================================================

# Consommation annuelle d'un DC de 1 GW (référence brute avant facteur de charge)
energy_per_dc_gwh = 8700.0   # GWh ≈ 1 GW × 8 760 h/an

# Surface de référence pour exprimer les équivalences en % d'une région
AURA_KM2 = 69_711.0  # km² — Région Auvergne-Rhône-Alpes

# Parcs français existants par filière (source : SDES, RTE, FHE, ADEME)
NUC_REACTORS_TOTAL    = 56
HYDRO_BARRAGES_TOTAL  = 220
WIND_PARCS_TOTAL      = 2_262
SOLAR_CENTRALES_TOTAL = 900
COAL_PLANTS_ACTIVE    = 2
BIO_PLANTS_TOTAL      = 80

# Production annuelle type par unité de production (TWh/unité)
capacities_twh_per_unit = {
    "nuke":  8.2,    # 1 réacteur nucléaire
    "hydro": 1.5,    # 1 grand barrage hydraulique
    "wind":  0.20,   # 1 parc éolien (≈ 50 turbines)
    "solar": 0.012,  # 1 centrale PV ≥ 5 MW
    "coal":  3.0,    # 1 centrale charbon (type Cordemais)
    "bio":   0.1,    # 1 centrale biomasse électrique
}


def equivalent_units(source: str, nb_dc: int, facteur_pct: float, puissance_mw: float) -> int:
    """
    Calcule combien d'unités de production (réacteurs, barrages, parcs…) seraient
    nécessaires pour alimenter nb_dc data centers de puissance_mw MW avec un facteur
    de charge facteur_pct %.
    """
    fc         = max(0.0, min(1.0, (facteur_pct or 0) / 100.0))
    twh_2035   = (puissance_mw * 8760 * fc / 1e6) * max(1, nb_dc)
    unit_twh   = capacities_twh_per_unit[source]
    return int(round(twh_2035 / unit_twh)) if unit_twh > 0 else 0


# =========================================================
# Constantes du simulateur comparatif — habitants équivalents
# =========================================================

# Consommation électrique annuelle par habitant (MWh/habitant/an)
# Source : Our World In Data / IEA (données 2022–2023 selon les pays)
COUNTRY_CONSO = {
    "Mondial":           2.674,
    "France (68,29 M)":  2.223,
    "Qatar (2,66 M)":    226.848,
    "Mali (28,24 M)":    0.173,
    "Etats-Unis (340,1 M)": 12.705,
    "Chine (1 411,41 M)":   6.113,
    "Inde (1438,60 M)":      1.395,
    "Russie (143,8 M)":      6.961,
}

# Paliers de puissance du projet Data One (Eybens) et consommation annuelle correspondante
DC_LABELS    = ["15 MW", "200 MW", "400 MW", "1 GW"]
DC_PALIER_MWH = [15*24*365, 200*24*365, 400*24*365, 1000*24*365]
DC_1GW_MWH   = 8_760_000.0  # MWh/an pour un DC de 1 GW à pleine charge

# Palette de couleurs pour les barres du simulateur comparatif
PALETTE = [
    "#3B82F6", "#22C55E", "#F59E0B", "#EF4444",
    "#8B5CF6", "#06B6D4", "#84CC16", "#F97316",
]
