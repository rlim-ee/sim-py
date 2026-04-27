# server/energie/simulateurs/comparatif.py — simulateur "Analyse comparative"
#
# Ce module répond à la question : "combien d'habitants consomment autant
# d'électricité qu'un data center du projet Data One ?"
#
# L'idée : diviser la consommation annuelle du DC (en MWh) par la consommation
# annuelle par habitant dans un pays donné. Le résultat est le nombre d'habitants
# "équivalents".
#
# Outputs produits :
#   - france_1gw, qatar_1gw, mali_1gw  → habitants équivalents pour un DC de 1 GW
#   - france_pop, qatar_pop, mali_pop   → population totale du pays (texte statique)
#   - france_pct, qatar_pct, mali_pct   → % de la population nationale
#   - checkbox_group_conso             → liste de profils disponibles (rendu dynamique)
#   - barplot                          → graphique comparatif par profil sélectionné
#   - entites_dyn, entite_controls     → interface de comparaison personnalisée
#   - barplot_personalisee             → graphique de la comparaison personnalisée
from __future__ import annotations

from pathlib import Path

import plotly.graph_objects as go
from shiny import reactive, render, ui
import shinywidgets as sw

from ._shared import (
    prepare_sim_data,
    style_fig,
    COUNTRY_CONSO,
    DC_LABELS, DC_PALIER_MWH, DC_1GW_MWH,
    PALETTE,
)


def server(input, output, session, app_dir: Path):
    sim = prepare_sim_data(app_dir)

    # --- Focus 1 GW : France, Qatar, Mali ---
    # Ces trois pays illustrent l'écart de consommation entre pays riches/pauvres.
    # Les valeurs sont calculées une seule fois (les inputs sont des constantes).
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
        v   = COUNTRY_CONSO.get("France (68,29 M)", 1.0)
        pct = round((DC_1GW_MWH / v) / 68_290_000 * 100.0, 2)
        return f"Soit {pct} % de la population totale du pays"

    @output
    @render.text
    def qatar_pct():
        v   = COUNTRY_CONSO.get("Qatar (2,66 M)", 1.0)
        pct = round((DC_1GW_MWH / v) / 2_660_000 * 100.0, 2)
        return f"Soit {pct} % de la population totale du pays"

    @output
    @render.text
    def mali_pct():
        v   = COUNTRY_CONSO.get("Mali (28,24 M)", 1.0)
        pct = round((DC_1GW_MWH / v) / 28_243_609 * 100.0, 2)
        return f"Soit {pct} % de la population totale du pays"

    # --- Sélecteur de profils (rendu dynamique pour pouvoir évoluer sans toucher l'UI) ---
    @output
    @render.ui
    def checkbox_group_conso():
        return ui.input_checkbox_group(
            "pays_selection",
            "Choisissez les pays (Population totale en Million) à afficher :",
            choices=list(COUNTRY_CONSO.keys()),
            selected=["Mondial"],
        )

    # --- Graphique comparatif ---
    # Pour chaque profil sélectionné et chaque palier de puissance,
    # on calcule le nombre d'habitants équivalents = conso_DC / conso_par_habitant.
    def _scale_labels(max_val: float):
        """Choisit l'unité d'affichage (habitants, milliers, millions) selon l'ordre de grandeur."""
        if max_val >= 1e6:
            return 1e6, "Nombre d'habitants équivalents (en millions)", " millions"
        if max_val >= 1e3:
            return 1e3, "Nombre d'habitants équivalents (en milliers)", " milliers"
        return 1.0, "Nombre d'habitants équivalents", ""

    @output
    @sw.render_widget
    def barplot():
        sel  = input.pays_selection() or ["Mondial"]
        vals = [(p, COUNTRY_CONSO[p]) for p in sel if p in COUNTRY_CONSO]
        if not vals:
            fig = go.Figure()
            fig.update_layout(title_text="Sélectionnez au moins un profil")
            return style_fig(fig, input, height=420)

        pays_names = [p for p, _ in vals]
        pays_conso = [v for _, v in vals]

        # Habitants équivalents par pays et par palier de puissance
        he_by_pays: dict[str, list[float]] = {p: [] for p in pays_names}
        for j, p in enumerate(pays_names):
            c = pays_conso[j]
            for mwh in DC_PALIER_MWH:
                he_by_pays[p].append(mwh / c if c > 0 else 0.0)

        max_val = max((max(v) if v else 0.0) for v in he_by_pays.values())
        scale, y_title, hover_suffix = _scale_labels(max_val)

        fig = go.Figure()
        for idx, p in enumerate(pays_names):
            yvals = [v / scale for v in he_by_pays[p]]
            fig.add_trace(go.Bar(
                x=DC_LABELS, y=yvals, name=p,
                marker=dict(color=PALETTE[idx % len(PALETTE)]),
                hovertemplate=(
                    "Profil : " + p +
                    "<br>Palier : %{x}<br>Habitants équivalents : %{y:,.2f}" +
                    hover_suffix + "<extra></extra>"
                ),
            ))

        fig.update_layout(
            legend_title_text="",
            xaxis_title="Paliers de puissance du Data Center de Eybens",
            yaxis_title=y_title, barmode="group",
        )
        return style_fig(fig, input, height=460)

    # --- Comparaison personnalisée ---
    # L'utilisateur définit ses propres entités (nom + consommation en kWh/MWh/GWh)
    # et compare leur consommation avec les paliers du DC.
    entite_count   = reactive.Value(2)   # nombre de lignes de saisie (1 à 5)
    committed_rows = reactive.Value([])  # données validées (déclenchées par le bouton)

    def _to_float(x):
        try:
            return float(x)
        except (TypeError, ValueError):
            return None

    def _to_mwh(value: float, unit: str) -> float:
        """Convertit kWh, MWh ou GWh vers MWh (unité interne)."""
        u = (unit or "").lower()
        if "kwh" in u:
            return float(value) / 1000.0
        if "gwh" in u:
            return float(value) * 1000.0
        return float(value)

    def _read_personalisee_rows():
        """Lit les champs de saisie et retourne une liste (nom, consommation_mwh)."""
        n    = entite_count()
        rows = []
        for i in range(1, n + 1):
            nom  = getattr(input, f"nom_perso_{i}")()
            val  = _to_float(getattr(input, f"val_perso_{i}")())
            unit = getattr(input, f"unit_perso_{i}")()
            if nom and val is not None and val > 0:
                rows.append((str(nom), _to_mwh(val, unit)))
        return rows

    # Boutons + / − pour gérer le nombre de lignes de saisie
    @output
    @render.ui
    def entite_controls():
        n     = entite_count()
        maxed = n >= 5
        mined = n <= 1
        return ui.div(
            ui.div(
                ui.input_action_button(
                    "add_entite", "", icon=ui.tags.i({"class": "fa-solid fa-plus"}),
                    disabled=maxed, class_="btn-round",
                ),
                ui.input_action_button(
                    "rm_entite", "", icon=ui.tags.i({"class": "fa-solid fa-minus"}),
                    disabled=mined, class_="btn-round",
                ),
                style="display:flex;gap:8px",
            ),
            ui.div(
                ui.input_action_button(
                    "validate_personalisee", "Valider",
                    icon=ui.tags.i({"class": "fa-solid fa-check"}),
                    class_="btn btn-primary",
                    style="background:#1F6FEB;border-color:#1F6FEB;color:#fff;",
                ),
                style="margin-top:8px",
            ),
        )

    # Le bouton "Valider" fige les données saisies dans committed_rows,
    # ce qui déclenche le re-rendu de barplot_personalisee.
    # Un message JavaScript fait défiler la page jusqu'au graphique.
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

    # Génération dynamique des champs de saisie
    @output
    @render.ui
    def entites_dyn():
        n     = entite_count()
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

    # Graphique de la comparaison personnalisée
    @output
    @sw.render_widget
    def barplot_personalisee():
        rows = committed_rows()
        if not rows:
            fig = go.Figure()
            fig.update_layout(title_text="Renseignez les champs puis cliquez sur « Valider » pour afficher/mettre à jour le diagramme.")
            return style_fig(fig, input, height=420)

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
                    x=DC_LABELS, y=yvals, name=name,
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
        return style_fig(fig, input, height=420)
