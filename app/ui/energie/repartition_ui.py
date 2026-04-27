# ui/energie/repartition_ui.py — onglet "Europe" du module Répartition
#
# Affiche :
#   - une carte interactive (Folium) colorée par densité de data centers / habitant
#   - un graphique à barres horizontales classant les pays par nombre de DC
#   - trois encarts KPI (total DC, pays leader, concentration Top 10)
#
# La carte et le graphique sont calculés par server/energie/repartition.py.
# Les textes viennent de www/texts/energie/repartition.json.
from shiny import ui
import shinywidgets as sw

from ui._common import (
    dropcard, load_texts, html,
    interp_title, savoir_plus_label,
)


def _encart_kpi(kpi: dict):
    """
    Construit un encart KPI à partir d'un bloc JSON.
    La valeur affichée (output_id) est calculée en temps réel par le serveur.
    """
    return ui.div(
        ui.div(
            {"class": f"kpi-card {kpi.get('accent', '')}"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": kpi.get("icone", "")}),
            ),
            ui.div({"class": "kpi-title"}, kpi.get("titre", "")),
            # output_text() est un emplacement Shiny : le serveur y injecte la valeur calculée
            ui.div({"class": "kpi-value"}, ui.output_text(kpi.get("output_id", ""))),
            ui.p(kpi.get("description", ""), class_="mb-0"),
        ),
        class_="col",
    )


def _accordeon_aide(contenu_html: str, valeur: str):
    """
    Accordéon 'Aide à l'interprétation' replié par défaut.
    L'utilisateur clique pour déplier le texte explicatif.
    `valeur` est un identifiant interne pour Shiny (ne s'affiche pas).
    """
    return ui.accordion(
        ui.accordion_panel(
            interp_title(),       # titre partagé depuis _common.json
            html(contenu_html),
            value=valeur,
        ),
        open=False,
        class_="interp-accordion",
    )


def panel():
    """Construit le panneau complet de l'onglet Europe."""
    tx   = load_texts("energie.repartition")
    s1   = tx.get("section1", {})
    s2   = tx.get("section2", {})
    s3   = tx.get("section3", {})
    s4   = tx.get("section4", {})
    kpis = tx.get("kpis",     {})

    return ui.div(

        # Titre + introduction
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2(s1.get("titre", "")),
            ui.p(html(s1.get("introduction_html", ""))),
        ),

        # Encadré "Savoir plus" (rétractable)
        dropcard(
            s2.get("titre", savoir_plus_label()),
            html(s2.get("contenu_html", "")),
        ),

        # Ligne : carte Folium à gauche, graphique à barres à droite
        ui.div(
            # Carte choroplèthe (rendue par server/energie/repartition.py → repartition_map)
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s3.get("icone", "")}),
                        ui.h4(s3.get("titre", ""), class_="panel-title"),
                    ),
                    ui.div(
                        ui.div(ui.output_ui("repartition_map"), class_="map-wrap"),
                        class_="panel-body",
                    ),
                    ui.div(
                        _accordeon_aide(
                            s3.get("aide_html", ""),
                            "interp-repartition-map",
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            # Graphique à barres (rendu par server → dc_share_plot)
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s4.get("icone", "")}),
                        ui.h4(s4.get("titre", ""), class_="panel-title"),
                    ),
                    ui.div(
                        sw.output_widget("dc_share_plot"),
                        class_="panel-body",
                    ),
                    ui.div(
                        _accordeon_aide(
                            s4.get("aide_html", ""),
                            "interp-dc-share",
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            class_="row gap-4 row-eq",
        ),

        # Ligne de trois encarts KPI sous les visualisations
        ui.div(
            _encart_kpi(kpis.get("total",  {})),
            _encart_kpi(kpis.get("leader", {})),
            _encart_kpi(kpis.get("top10",  {})),
            class_="row gap-4 mt-3",
        ),
    )
