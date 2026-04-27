# server/energie/simulateurs/predictif.py — simulateur "Analyse prédictive"
#
# Ce module répond à la question : "si l'on construit X data centers de Y MW
# avec un facteur de charge Z %, combien de TWh supplémentaires consomme-t-on,
# et combien d'unités de production faudrait-il pour les alimenter ?"
#
# L'utilisateur règle trois curseurs dans la barre latérale :
#   - nb_dc          : nombre de data centers (input.nb_dc)
#   - facteur_charge : facteur de charge en % (input.facteur_charge)
#   - puissance_mw   : puissance unitaire en MW (input.puissance_mw)
#
# Ces trois valeurs déclenchent la mise à jour de tous les outputs dès qu'une
# valeur change (comportement réactif automatique de Shiny).
#
# Outputs produits :
#   - energiePlot          → graphique principal : historique + projections + courbe simulée
#   - info_conso_totale    → consommation nationale totale avec les DC (TWh)
#   - nuke_value, hydro_value, coal_value, wind_value, solar_value, bio_value
#                          → nombre d'unités de production équivalentes
#   - nuke_pct_total, hydro_pct_total, wind_pct_total, solar_pct_total,
#     coal_pct_total, bio_pct_total  → pourcentage du parc national correspondant
#   - wind_surface, solar_surface   → surface au sol mobilisée (km²)
#   - surface_info         → note de bas de page sur les sources et hypothèses
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
from shiny import reactive, render, ui
import shinywidgets as sw

from ._shared import (
    COLORS,
    prepare_sim_data,
    style_fig,
    equivalent_units,
    AURA_KM2,
    NUC_REACTORS_TOTAL, HYDRO_BARRAGES_TOTAL, WIND_PARCS_TOTAL,
    SOLAR_CENTRALES_TOTAL, COAL_PLANTS_ACTIVE, BIO_PLANTS_TOTAL,
    capacities_twh_per_unit,
    COUNTRY_CONSO,
    DC_1GW_MWH,
)


def server(input, output, session, app_dir: Path):
    sim = prepare_sim_data(app_dir)

    # Raccourcis locaux pour alléger la lecture du code
    CONSO_HIST_Y   = sim.CONSO_HIST_Y
    CONSO_HIST_V   = sim.CONSO_HIST_V
    PROD_HIST_Y    = sim.PROD_HIST_Y
    PROD_HIST_V    = sim.PROD_HIST_V
    CONSO_PROJ_Y   = sim.CONSO_PROJ_Y
    CONSO_PROJ_REF = sim.CONSO_PROJ_REF
    CONSO_PROJ_MIN = sim.CONSO_PROJ_MIN
    CONSO_PROJ_MAX = sim.CONSO_PROJ_MAX
    PROD_PROJ_Y    = sim.PROD_PROJ_Y
    PROD_PROJ_REF  = sim.PROD_PROJ_REF
    PROD_PROJ_MIN  = sim.PROD_PROJ_MIN
    PROD_PROJ_MAX  = sim.PROD_PROJ_MAX
    DC_YEARS       = sim.DC_YEARS
    DC_TWH_DC      = sim.DC_TWH_DC
    consommation_actuelle = sim.consommation_actuelle

    # --- Graphique principal ---
    # Trois couches visuelles :
    #   1. Bandes min/max (enveloppe de scénarios RTE)
    #   2. Lignes de référence conso/prod (scénario médian RTE)
    #   3. Courbe simulée (référence + impact des DC, à partir de 2025)
    @output
    @sw.render_widget
    def energiePlot():
        nb_dc      = int(input.nb_dc())
        facteur    = float(input.facteur_charge()) / 100
        puissance_mw = float(input.puissance_mw())

        # Impact total des DC simulés en TWh/an
        twh_dc = (puissance_mw * 8760 * facteur / 1e6) * nb_dc

        fig = go.Figure()

        # Bandes d'incertitude (fill="toself" = zone fermée entre min et max)
        fig.add_trace(go.Scatter(
            x=CONSO_PROJ_Y + list(reversed(CONSO_PROJ_Y)),
            y=CONSO_PROJ_MAX + list(reversed(CONSO_PROJ_MIN)),
            fill="toself", mode="none",
            fillcolor="rgba(31,111,235,0.14)",
            name="Estimation min/max de consommation",
            hoverinfo="skip",
        ))

        fig.add_trace(go.Scatter(
            x=PROD_PROJ_Y + list(reversed(PROD_PROJ_Y)),
            y=PROD_PROJ_MAX + list(reversed(PROD_PROJ_MIN)),
            fill="toself", mode="none",
            fillcolor="rgba(46,160,67,0.16)",
            name="Estimation min/max de production",
            hoverinfo="skip",
        ))

        # Lignes de référence (historique + projection)
        fig.add_trace(go.Scatter(
            x=CONSO_HIST_Y + CONSO_PROJ_Y,
            y=CONSO_HIST_V + CONSO_PROJ_REF,
            mode="lines",
            line=dict(width=3, color="#1F6FEB"),
            name="Consommation nationale (référence)",
        ))

        fig.add_trace(go.Scatter(
            x=PROD_HIST_Y + PROD_PROJ_Y,
            y=PROD_HIST_V + PROD_PROJ_REF,
            mode="lines",
            line=dict(width=3, color="#2EA043"),
            name="Production nationale (référence)",
        ))

        # Courbe simulée : part du scénario de référence + surconsommation des DC
        # Le point d'attache est en 2025 (valeur identique à la référence),
        # puis chaque année suivante = référence + impact DC.
        simulated_x = CONSO_PROJ_Y
        simulated_y = []
        for year, ref in zip(CONSO_PROJ_Y, CONSO_PROJ_REF):
            if year < 2025:
                simulated_y.append(None)
            elif year == 2025:
                simulated_y.append(ref)
            else:
                simulated_y.append(ref + twh_dc)

        fig.add_trace(go.Scatter(
            x=simulated_x, y=simulated_y,
            mode="lines",
            line=dict(width=3, dash="dash", color="#F97316"),
            name="Consommation avec Data Centers",
        ))

        fig.update_layout(
            xaxis_title="Année",
            yaxis_title="TWh",
            height=460,
            legend=dict(orientation="h", y=-0.2, x=0.5,
                        xanchor="center", yanchor="top"),
        )
        return style_fig(fig, input, height=460)

    @output
    @render.text
    def info_conso_totale():
        nb_dc        = int(input.nb_dc())
        facteur      = float(input.facteur_charge()) / 100
        puissance_mw = float(input.puissance_mw())
        twh_dc       = (puissance_mw * 8760 * facteur / 1e6) * nb_dc
        total        = consommation_actuelle + twh_dc
        return f"{total:.0f} TWh"

    # --- KPI équivalents de production (horizon 2035) ---
    # _eq() calcule le nombre d'unités pour chaque filière
    def _eq(source: str) -> str:
        return f"{equivalent_units(source, int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw())):,}".replace(",", " ")

    @output
    @render.text
    def nuke_value():  return _eq("nuke")
    @output
    @render.text
    def hydro_value(): return _eq("hydro")
    @output
    @render.text
    def coal_value():  return _eq("coal")
    @output
    @render.text
    def wind_value():  return _eq("wind")
    @output
    @render.text
    def solar_value(): return _eq("solar")
    @output
    @render.text
    def bio_value():   return _eq("bio")

    # Pourcentages du parc national par filière
    @output
    @render.text
    def nuke_pct_total():
        eq  = equivalent_units("nuke", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        pct = (eq / NUC_REACTORS_TOTAL) * 100.0
        return f"sur {NUC_REACTORS_TOTAL} réacteurs en France — soit {pct:.1f} %"

    @output
    @render.text
    def hydro_pct_total():
        eq  = equivalent_units("hydro", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        pct = (eq / HYDRO_BARRAGES_TOTAL) * 100.0
        return f"sur ~{HYDRO_BARRAGES_TOTAL} grands barrages hydroélectriques — soit {pct:.1f} %"

    @output
    @render.text
    def wind_pct_total():
        eq  = equivalent_units("wind", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        pct = (eq / WIND_PARCS_TOTAL) * 100.0
        return f"sur {WIND_PARCS_TOTAL:,} parcs éoliens en France — soit {pct:.1f} %".replace(",", " ")

    @output
    @render.text
    def solar_pct_total():
        eq  = equivalent_units("solar", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        pct = (eq / SOLAR_CENTRALES_TOTAL) * 100.0
        return f"sur ~{SOLAR_CENTRALES_TOTAL} centrales PV ≥ 5 MW — soit {pct:.1f} %"

    @output
    @render.text
    def coal_pct_total():
        eq = equivalent_units("coal", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        return f"sur {COAL_PLANTS_ACTIVE} centrales encore actives (fermeture 2027) — x{eq / COAL_PLANTS_ACTIVE:.1f}"

    @output
    @render.text
    def bio_pct_total():
        eq  = equivalent_units("bio", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        pct = (eq / BIO_PLANTS_TOTAL) * 100.0
        return f"sur ~{BIO_PLANTS_TOTAL} centrales biomasse électriques — soit {pct:.1f} %"

    # Surface au sol pour l'éolien et le solaire
    # (seules deux filières avec une emprise foncière significative)
    @output
    @render.text
    def wind_surface():
        # 50 turbines/parc × 0,78 km²/turbine (espacement + sécurité inclus)
        nb_parcs             = equivalent_units("wind", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        turbines_par_parc    = 50
        surface_par_turbine_km2 = 0.78
        surface_km2          = nb_parcs * turbines_par_parc * surface_par_turbine_km2
        pct_fr               = (surface_km2 / AURA_KM2) * 100.0
        return f"≈ {surface_km2:,.0f} km² mobilisés — {pct_fr:.1f} % d'Auvergne-Rhône-Alpes".replace(",", " ")

    @output
    @render.text
    def solar_surface():
        # Centrale type 10 MW ≈ 12 ha artificialisés (sans compter les espaces entre rangées)
        nb_centrales             = equivalent_units("solar", int(input.nb_dc()), float(input.facteur_charge()), float(input.puissance_mw()))
        surface_par_centrale_km2 = 0.12
        surface_km2              = nb_centrales * surface_par_centrale_km2
        pct_fr                   = (surface_km2 / AURA_KM2) * 100.0
        return f"≈ {surface_km2:,.0f} km² artificialisés — {pct_fr:.1f} % d'Auvergne-Rhône-Alpes".replace(",", " ")

    # Note de bas de page : sources et hypothèses de calcul
    @output
    @render.ui
    def surface_info():
        return ui.div(
            ui.p(
                ui.em(
                    ui.strong("Sources des références : "),
                    "SDES (Service des données et études statistiques, ministère de la Transition écologique), ",
                    "RTE (Bilan électrique 2024), France Hydro-Électricité, Atlas Bioénergie International 2024.",
                )
            ),
            ui.p(
                ui.em(
                    ui.strong("Hypothèses d'unités : "),
                    "1 réacteur nucléaire ≈ 8,2 TWh/an · 1 grand barrage ≈ 1,5 TWh/an · ",
                    "1 parc éolien (≈ 50 turbines) ≈ 0,20 TWh/an · 1 centrale photovoltaïque ≥ 5 MW ≈ 0,012 TWh/an · ",
                    "1 centrale charbon ≈ 3 TWh/an (type Cordemais) · 1 centrale biomasse ≈ 0,1 TWh/an.",
                )
            ),
            ui.p(
                ui.em(
                    ui.strong("Surface au sol : "),
                    "pour l'éolien, il s'agit de la surface totale mobilisée (espacement, sécurité), ",
                    "non entièrement artificialisée ; pour le solaire, il s'agit de la surface artificialisée. ",
                    "Le pourcentage est calculé par rapport à une surface de référence de ",
                    ui.strong("69 711 km²"),
                    " (Région Auvergne-Rhône-Alpes).",
                ),
                style="opacity:.9",
            ),
            class_="surface-note",
        )
