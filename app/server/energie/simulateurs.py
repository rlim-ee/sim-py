# server/simulateurs.py
from __future__ import annotations

import pandas as pd
from shiny import reactive, render, ui
import shinywidgets as sw
import plotly.graph_objects as go
from pathlib import Path

# --------- Couleurs ---------
COLORS = {
    "consumption": "#1F6FEB",
    "consumption_dark": "#58A6FF",
    "production":  "#2EA043",
    "accent":      "#F97316",
}

# ============================
# Données
# ============================

def load_data(app_dir: Path):
    data_dir = app_dir / "www" / "data"

    dc_df = pd.read_csv(data_dir / "dc_paliers.csv")
    conso_hist_df = pd.read_csv(data_dir / "conso_hist.csv")
    prod_hist_df = pd.read_csv(data_dir / "prod_hist.csv")
    conso_proj_df = pd.read_csv(data_dir / "conso_proj.csv")
    prod_proj_df = pd.read_csv(data_dir / "prod_proj.csv")

    return dc_df, conso_hist_df, prod_hist_df, conso_proj_df, prod_proj_df

# ============================
# Helpers affichage
# ============================
def _is_dark(input) -> bool:
    try:
        return bool(input.darkmode())
    except Exception:
        return True

def _theme_text_color(input) -> str:
    return "#0B162C" if not _is_dark(input) else "#F8FAFC"

def _grid_color(input) -> str:
    return "rgba(15,22,44,.08)" if not _is_dark(input) else "rgba(203,213,225,.28)"

def _consumption_color(input) -> str:
    return COLORS["consumption"] if not _is_dark(input) else COLORS["consumption_dark"]

def _style_fig(fig: go.Figure, input, *, height: int = 460) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Poppins, Arial, sans-serif", size=13, color=_theme_text_color(input)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(font_size=12, font_family="Poppins, Arial, sans-serif"),
        margin=dict(t=40, r=20, b=40, l=40),
        title_font=dict(color=_theme_text_color(input)),
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center",
                    bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                    font=dict(color=_theme_text_color(input))),
        height=height,
    )
    gc = _grid_color(input)
    fig.update_xaxes(showgrid=True, gridcolor=gc,
                     tickfont=dict(color=_theme_text_color(input)),
                     title_font=dict(color=_theme_text_color(input)))
    fig.update_yaxes(showgrid=True, gridcolor=gc,
                     tickfont=dict(color=_theme_text_color(input)),
                     title_font=dict(color=_theme_text_color(input)))
    return fig

# ========= Pré-calculs statiques =========
def _tendances_prepared() -> dict:
    # Lignes = historique + référence projetée
    lines_conso_x = CONSO_HIST_Y + CONSO_PROJ_Y
    lines_conso_y = CONSO_HIST_V + CONSO_PROJ_REF
    lines_prod_x  = PROD_HIST_Y  + PROD_PROJ_Y
    lines_prod_y  = PROD_HIST_V  + PROD_PROJ_REF

    # Rubans (Min/Max) pour conso & prod 
    ribbon_conso_x = CONSO_PROJ_Y
    ribbon_conso_min = CONSO_PROJ_MIN
    ribbon_conso_max = CONSO_PROJ_MAX

    ribbon_prod_x = PROD_PROJ_Y
    ribbon_prod_min = PROD_PROJ_MIN
    ribbon_prod_max = PROD_PROJ_MAX

    return {
        "lines_conso_x": lines_conso_x, "lines_conso_y": lines_conso_y,
        "lines_prod_x":  lines_prod_x,  "lines_prod_y":  lines_prod_y,
        "ribbon_conso_x": ribbon_conso_x, "ribbon_conso_min": ribbon_conso_min, "ribbon_conso_max": ribbon_conso_max,
        "ribbon_prod_x":  ribbon_prod_x,  "ribbon_prod_min":  ribbon_prod_min,  "ribbon_prod_max":  ribbon_prod_max,
    }

# ---- Conso totale aux paliers
def _consommation_totale_points(nb_dc: int, facteur_pct: float) -> tuple[list[int], list[float]]:
    fc = max(0.0, min(1.0, (facteur_pct or 0)/100.0))
    y_vals = [consommation_actuelle + (twh * nb_dc * fc) for twh in DC_TWH_DC]
    return DC_YEARS, y_vals

# ============================
# Equivalences (KPI)
# ============================
energy_per_dc_gwh = 8700.0  # GWh par DC ~ 1 GW * 8760h ≈ 8.7 TWh
NUC_REACTORS_TOTAL = 56
AURA_KM2 = 69_711.0
capacities_twh_per_unit = {
    "nuke": 8.2, "hydro": 1.5, "wind": 0.004, "solar": 0.00004, "coal": 3.0, "bio": 0.1
}

def _equivalent_units(
    source: str,
    nb_dc: int,
    facteur_pct: float,
    puissance_mw: float
) -> int:

    fc = max(0.0, min(1.0, (facteur_pct or 0) / 100.0))

    # Calcul TWh basé sur la vraie formule
    twh_2035 = (puissance_mw * 8760 * fc / 1e6) * max(1, nb_dc)

    unit_twh = capacities_twh_per_unit[source]

    return int(round(twh_2035 / unit_twh)) if unit_twh > 0 else 0


# ============================
# Simulation 2 : Habitants équivalents
# ============================
# Conso moyenne par personne (MWh/an)
COUNTRY_CONSO = {
    "Mondial": 2.674,
    "France (68,29 M)": 2.223,
    "Qatar (2,66 M)": 226.848,
    "Mali (28,24 M)": 0.173,
    "Etats-Unis (340,1 M)": 12.705,
    "Chine (1 411,41 M)": 6.113,
    "Inde (1438,60 M)": 1.395,
    "Russie (143,8 M)": 6.961,
}
# DC paliers (MWh/an)
DC_LABELS = ["15 MW", "200 MW", "400 MW", "1 GW"]
DC_PALIER_MWH = [15*24*365, 200*24*365, 400*24*365, 1000*24*365]
DC_1GW_MWH = 8_760_000.0

PALETTE = ["#3B82F6", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#84CC16", "#F97316"]

# ============================
# SERVER
# ============================
def server(input, output, session, app_dir: Path):

    # ============================
    # Chargement des données
    # ============================

    dc_df, conso_hist_df, prod_hist_df, conso_proj_df, prod_proj_df = load_data(app_dir)

    # Historique
    CONSO_HIST_Y = conso_hist_df["year"].tolist()
    CONSO_HIST_V = conso_hist_df["value"].tolist()

    PROD_HIST_Y = prod_hist_df["year"].tolist()
    PROD_HIST_V = prod_hist_df["value"].tolist()

    # Projections
    CONSO_PROJ_Y = conso_proj_df["year"].tolist()
    CONSO_PROJ_REF = conso_proj_df["ref"].tolist()
    CONSO_PROJ_MIN = conso_proj_df["min"].tolist()
    CONSO_PROJ_MAX = conso_proj_df["max"].tolist()

    PROD_PROJ_Y = prod_proj_df["year"].tolist()
    PROD_PROJ_REF = prod_proj_df["ref"].tolist()
    PROD_PROJ_MIN = prod_proj_df["min"].tolist()
    PROD_PROJ_MAX = prod_proj_df["max"].tolist()

    DC_YEARS = dc_df["year"].tolist()
    DC_TWH_DC = dc_df["twh_per_dc"].tolist()

    consommation_actuelle = CONSO_HIST_V[-1]


    # ---------- TENDANCES 2000–2050 ----------
    @reactive.calc
    def _tendances():
        return _tendances_prepared()

    @output
    @sw.render_widget
    def energiePlot():

        nb_dc = int(input.nb_dc())
        facteur = float(input.facteur_charge()) / 100
        puissance_mw = float(input.puissance_mw())

        # Impact DC en TWh
        twh_dc = (puissance_mw * 8760 * facteur / 1e6) * nb_dc

        fig = go.Figure()

        # =====================================================
        # BANDES MIN / MAX
        # =====================================================

        # Bande consommation
        fig.add_trace(go.Scatter(
            x=CONSO_PROJ_Y + list(reversed(CONSO_PROJ_Y)),
            y=CONSO_PROJ_MAX + list(reversed(CONSO_PROJ_MIN)),
            fill="toself",
            mode="none",
            fillcolor="rgba(31,111,235,0.14)",
            name="Estimation min/max de consommation",
           hoverinfo="skip"
        ))

        # Bande production
        fig.add_trace(go.Scatter(
            x=PROD_PROJ_Y + list(reversed(PROD_PROJ_Y)),
            y=PROD_PROJ_MAX + list(reversed(PROD_PROJ_MIN)),
            fill="toself",
            mode="none",
            fillcolor="rgba(46,160,67,0.16)",
            name="Estimation min/max de production",
            hoverinfo="skip"
        ))

        # =====================================================
        # LIGNES RÉFÉRENCE
        # =====================================================

        # Consommation référence
        fig.add_trace(go.Scatter(
            x=CONSO_HIST_Y + CONSO_PROJ_Y,
            y=CONSO_HIST_V + CONSO_PROJ_REF,
            mode="lines",
            line=dict(width=3, color="#1F6FEB"),
            name="Consommation nationale (référence)"
        ))

         # Production référence
        fig.add_trace(go.Scatter(
            x=PROD_HIST_Y + PROD_PROJ_Y,
            y=PROD_HIST_V + PROD_PROJ_REF,
            mode="lines",
            line=dict(width=3, color="#2EA043"),
            name="Production nationale (référence)"
        ))

        # =====================================================
        # CONSOMMATION SIMULÉE (à partir de 2024)
        # =====================================================

        simulated_x = CONSO_PROJ_Y
        simulated_y = []

        for year, ref in zip(CONSO_PROJ_Y, CONSO_PROJ_REF):
            if year < 2025:
                simulated_y.append(None)
            elif year == 2025:
                # point d'attache
                simulated_y.append(ref)
            else:
                # ajout DC à partir de 2026
                simulated_y.append(ref + twh_dc)

    
        fig.add_trace(go.Scatter(
            x=simulated_x,
            y=simulated_y,
            mode="lines",
            line=dict(
                width=3,
                dash="dash",
                color="#F97316"
            ),
            name="Consommation avec Data Centers"
        ))

        fig.update_layout(
            xaxis_title="Année",
            yaxis_title="TWh",
            height=460,
            legend=dict(
                orientation="h",         
                y=-0.2,                  
                x=0.5,                    
                xanchor="center",
                yanchor="top"
            )
        )
        return _style_fig(fig, input, height=460)

    @output
    @render.text
    def info_conso_totale():
        nb_dc = int(input.nb_dc())
        facteur = float(input.facteur_charge()) / 100
        puissance_mw = float(input.puissance_mw())

        twh_dc = (puissance_mw * 8760 * facteur / 1e6) * nb_dc
        total = consommation_actuelle + twh_dc
        return f"{total:.0f} TWh"


    # ---------- KPI équivalents (2035) ----------
    @output
    @render.text
    def nuke_value():
        return f"{_equivalent_units(
            'nuke',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        ):,}".replace(",", " ")

    @output
    @render.text
    def hydro_value(): 
        return f"{_equivalent_units(
            'hydro',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        ):,}".replace(",", " ")
    @output
    @render.text
    def coal_value():
        return f"{_equivalent_units(
            'coal',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        ):,}".replace(",", " ")
    @output
    @render.text
    def wind_value():
        return f"{_equivalent_units(
            'wind',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        ):,}".replace(",", " ")
    @output
    @render.text
    def solar_value():
        return f"{_equivalent_units(
            'solar',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        ):,}".replace(",", " ")
    @output
    @render.text
    def bio_value():
        return f"{_equivalent_units(
            'bio',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        ):,}".replace(",", " ")

    @output
    @render.text
    def nuke_pct_total():
        eq = _equivalent_units(
            'nuke',
            int(input.nb_dc()),
            float(input.facteur_charge()),
            float(input.puissance_mw())
        )
        pct = (eq / NUC_REACTORS_TOTAL) * 100.0
        return f"{NUC_REACTORS_TOTAL} au total — soit {pct:.2f} % du nombre total"

    @output
    @render.text
    def wind_surface():
        production_par_eolienne_gwh = 6.8
        surface_par_eolienne_km2 = 0.78
        total_gwh = int(input.nb_dc()) * energy_per_dc_gwh
        nb_eoliennes = total_gwh / production_par_eolienne_gwh if production_par_eolienne_gwh > 0 else 0
        surface_km2 = nb_eoliennes * surface_par_eolienne_km2
        pct_fr = (surface_km2 / AURA_KM2) * 100.0
        return f"≈ {surface_km2:,.2f} km² occupés — soit {pct_fr:,.2f} % de l'Auvergne-Rhône-Alpes".replace(",", " ")

    @output
    @render.text
    def solar_surface():
        taille_m2 = 140.0
        production_totale_twh_fr = 25.0
        nb_installations_fr = 600_000.0
        prod_par_install_twh = production_totale_twh_fr / nb_installations_fr if nb_installations_fr > 0 else 0.0
        total_twh = (int(input.nb_dc()) * energy_per_dc_gwh) / 1000.0  # GWh → TWh
        nb_inst = total_twh / prod_par_install_twh if prod_par_install_twh > 0 else 0.0
        surface_km2 = (nb_inst * taille_m2) / 1e6
        pct_fr = (surface_km2 / AURA_KM2) * 100.0
        return f"≈ {surface_km2:,.2f} km² occupés — soit {pct_fr:,.2f} % de l'Auvergne-Rhône-Alpes".replace(",", " ")

    @output
    @render.ui
    def surface_info():
        return ui.div(
            ui.p(
                ui.em(
                    ui.strong("Note : "),
                    "La surface indiquée pour l'éolien correspond à la surface totale mobilisée ",
                    "(espacement, sécurité), qui n'est pas entièrement artificialisée."
                )
            ),
            ui.p(
                ui.em(
                    "Pour le solaire, la surface correspond à une estimation plus proche ",
                    "de la surface réellement artificialisée au sol."
                )
            ),
            ui.p(
                ui.em(
                    "Le pourcentage affiché est calculé par rapport à une surface de référence de ",
                    ui.strong("69 711 km²"),
                    " (Région Auvergne-Rhône-Alpes)."
                ),
                style="opacity:.9"
            ),
            class_="surface-note"
        )

    # ---------- Focus 1 GW (pays) ----------
    @output
    @render.text
    def france_1gw():
        v = COUNTRY_CONSO.get("France (68,29 M)")
        return f"{int(round(DC_1GW_MWH / v)):,}".replace(",", " ") if v else ""

    @output
    @render.text
    def qatar_1gw():
        v = COUNTRY_CONSO.get("Qatar (2,66 M)")
        return f"{int(round(DC_1GW_MWH / v)):,}".replace(",", " ") if v else ""

    @output
    @render.text
    def mali_1gw():
        v = COUNTRY_CONSO.get("Mali (28,24 M)")
        return f"{int(round(DC_1GW_MWH / v)):,}".replace(",", " ") if v else ""

    @output
    @render.text
    def france_pop(): return "Population totale : 68 290 000"

    @output
    @render.text
    def qatar_pop():  return "Population totale : 2 660 000"

    @output
    @render.text
    def mali_pop():   return "Population totale : 28 243 609"

    @output
    @render.text
    def france_pct():
        v = COUNTRY_CONSO.get("France (68,29 M)", 1.0)
        pct = round((DC_1GW_MWH / v) / 68_290_000 * 100.0, 2)
        return f"Soit {pct} % de la population totale du pays"

    @output
    @render.text
    def qatar_pct():
        v = COUNTRY_CONSO.get("Qatar (2,66 M)", 1.0)
        pct = round((DC_1GW_MWH / v) / 2_660_000 * 100.0, 2)
        return f"Soit {pct} % de la population totale du pays"

    @output
    @render.text
    def mali_pct():
        v = COUNTRY_CONSO.get("Mali (28,24 M)", 1.0)
        pct = round((DC_1GW_MWH / v) / 28_243_609 * 100.0, 2)
        return f"Soit {pct} % de la population totale du pays"

    # ---------- Sélecteur profils ----------
    @output
    @render.ui
    def checkbox_group_conso():
        return ui.input_checkbox_group(
            "pays_selection",
            "Choisissez les pays (Population totale en Million) à afficher :",
            choices=list(COUNTRY_CONSO.keys()),
            selected=["Mondial"],
        )

    # ---------- Barplot profils sélectionnés ----------
    def _scale_labels(max_val: float):
        if max_val >= 1e6:
            return 1e6, "Nombre d'habitants équivalents (en millions)", " millions"
        if max_val >= 1e3:
            return 1e3, "Nombre d'habitants équivalents (en milliers)", " milliers"
        return 1.0, "Nombre d'habitants équivalents", ""

    @output
    @sw.render_widget
    def barplot():
        sel = input.pays_selection() or ["Mondial"]
        vals = [(p, COUNTRY_CONSO[p]) for p in sel if p in COUNTRY_CONSO]
        if not vals:
            fig = go.Figure()
            fig.update_layout(title_text="Sélectionnez au moins un profil")
            return _style_fig(fig, input, height=420)

        pays_names = [p for p, _ in vals]
        pays_conso = [v for _, v in vals]

        # HE = conso_DC_palier / conso_par_personne
        he_by_pays: dict[str, list[float]] = {p: [] for p in pays_names}
        for j, p in enumerate(pays_names):
            c = pays_conso[j]
            for mwh in DC_PALIER_MWH:
                he_by_pays[p].append(mwh / c if c > 0 else 0.0)

        max_val = max((max(v) if v else 0.0) for v in he_by_pays.values())
        scale, y_title, hover_suffix = _scale_labels(max_val)

        fig = go.Figure()
        for idx, p in enumerate(pays_names):
            yvals = [v/scale for v in he_by_pays[p]]
            fig.add_trace(go.Bar(
                x=DC_LABELS, y=yvals, name=p,
                marker=dict(color=PALETTE[idx % len(PALETTE)]),
                hovertemplate=("Profil : " + p +
                               "<br>Palier : %{x}<br>Habitants équivalents : %{y:,.2f}" +
                               hover_suffix + "<extra></extra>")
            ))

        fig.update_layout(legend_title_text="",
                          xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group")
        return _style_fig(fig, input, height=460)
    
    
    entite_count = reactive.Value(2)

    committed_rows = reactive.Value([])

    def _read_personalisee_rows():
        n = entite_count()
        rows = []
        for i in range(1, n + 1):
            nom  = getattr(input, f"nom_perso_{i}")()
            val  = _to_float(getattr(input, f"val_perso_{i}")())
            unit = getattr(input, f"unit_perso_{i}")()
            if nom and val is not None and val > 0:
                rows.append((str(nom), _to_mwh(val, unit)))
        return rows
    
    @output
    @render.ui
    def entite_controls():
        n = entite_count()
        maxed = n >= 5
        mined = n <= 1
        return ui.div(
            ui.div(
                ui.input_action_button(
                    "add_entite", "", icon=ui.tags.i({"class": "fa-solid fa-plus"}),
                    disabled=maxed, class_="btn-round"
                ),
                ui.input_action_button(
                    "rm_entite", "", icon=ui.tags.i({"class": "fa-solid fa-minus"}),
                    disabled=mined, class_="btn-round"
                ),
                style="display:flex;gap:8px"
            ),
            ui.div(
                ui.input_action_button(
                    "validate_personalisee", "Valider",
                    icon=ui.tags.i({"class": "fa-solid fa-check"}),
                    class_="btn btn-primary",
                    style="background:#1F6FEB;border-color:#1F6FEB;color:#fff;"
                ),
                style="margin-top:8px"
            )
        )
                
    @reactive.Effect
    @reactive.event(input.validate_personalisee)
    async def _commit_personalisee():
        committed_rows.set(_read_personalisee_rows())
        await session.send_custom_message("scrollto", {"selector": "#personalized-card"})


    @reactive.Effect
    @reactive.event(input.add_entite)
    def _add_entite():
        entite_count.set(min(5, entite_count() + 1))

    @reactive.Effect
    @reactive.event(input.rm_entite)
    def _rm_entite():
        entite_count.set(max(1, entite_count() - 1))

    @output
    @render.ui
    def entites_dyn():
        n = entite_count()
        blocs = []
        for i in range(1, n + 1):
            blocs.append(
                ui.div(
                    ui.input_text(f"nom_perso_{i}", f"Nom {i}", f"Nom {i}"),
                    ui.input_numeric(f"val_perso_{i}", "Valeur", 1.0),
                    ui.input_select(
                        f"unit_perso_{i}",
                        "Unité",
                        ["kWh/an", "MWh/an", "GWh/an"],
                        selected="MWh/an",
                    ),
                    class_="mb-3",
                )
            )
        return ui.div(*blocs)

    def _to_float(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    def _to_mwh(value: float, unit: str) -> float:
        """Convertit kWh/MWh/GWh -> MWh."""
        u = (unit or "").lower()
        if "kwh" in u:
            return float(value) / 1000.0
        if "gwh" in u:
            return float(value) * 1000.0
        return float(value)  # MWh

    @output
    @sw.render_widget
    def barplot_personalisee():
        rows = committed_rows()  
        if not rows:
            fig = go.Figure()
            fig.update_layout(title_text="Renseignez les champs puis cliquez sur « Valider » pour afficher/mettre à jour le diagramme.")
            return _style_fig(fig, input, height=420)
        
        he_by_name: dict[str, list[float]] = {name: [] for name, _ in rows}
        for name, mwh in rows:
            for dc_mwh in DC_PALIER_MWH:
                he_by_name[name].append(dc_mwh / mwh if mwh > 0 else 0.0)
                
        max_val = max((max(v) if v else 0.0) for v in he_by_name.values())
        scale, y_title, hover_suffix = _scale_labels(max_val)

        fig = go.Figure()
        for name, vals in he_by_name.items():
            yvals = [v / scale for v in vals]
            fig.add_trace(
                go.Bar(
                    x=DC_LABELS,
                    y=yvals,
                    name=name,
                    hovertemplate=(
                        "Nom : " + name
                        + "<br>Palier : %{x}"
                        + "<br>Individus équivalents : %{y:,.2f}"
                        + hover_suffix
                        + "<extra></extra>"
                    ),
                )
            )

        fig.update_layout(
            legend_title_text="",
            xaxis_title="Paliers de puissance du Data Center de Eybens",
            yaxis_title=y_title,
            barmode="group",
            title="Nombre d'individus équivalents — projections Data One",
            )
        return _style_fig(fig, input, height=420)
