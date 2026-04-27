# ui/energie/bilan_ui.py — onglet "France" du module Bilan énergétique
#
# Affiche trois visualisations côte à côte ou empilées :
#   1. Carte choroplèthe des régions françaises (solde prod - conso)
#   2. Camembert (mix énergétique de la région sélectionnée)
#   3. Graphique d'évolution en aires empilées (2014-2024)
#
# Toutes ces visualisations sont calculées par server/energie/bilan.py.
# L'utilisateur peut changer l'année avec un curseur et la région avec un menu.
# Les textes viennent de www/texts/energie/bilan.json.
from shiny import ui
import shinywidgets as sw

from ui._common import (
    dropcard, load_texts, html,
    interp_title, savoir_plus_label,
)


def _accordeon_aide(contenu_html: str, valeur: str):
    """
    Accordéon 'Aide à l'interprétation' replié par défaut.
    L'utilisateur clique pour déplier l'explication de la visualisation.
    """
    return ui.accordion(
        ui.accordion_panel(
            interp_title(),
            html(contenu_html),
            value=valeur,
        ),
        open=False,
        class_="interp-accordion",
    )


def panel():
    """Construit le panneau complet de l'onglet France (bilan énergétique régional)."""
    tx = load_texts("energie.bilan")
    s1 = tx.get("section1", {})
    s2 = tx.get("section2", {})
    s3 = tx.get("section3", {})
    s4 = tx.get("section4", {})
    s5 = tx.get("section5", {})

    return ui.div(

        # Titre + introduction
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2(s1.get("titre", "")),
            ui.p(html(s1.get("introduction_html", ""))),
        ),

        # Encadré "Savoir plus" — explique les régions excédentaires/déficitaires
        dropcard(
            s2.get("titre", savoir_plus_label()),
            html(s2.get("contenu_html", "")),
        ),

        # Ligne : carte régionale à gauche + camembert à droite
        ui.div(
            # Carte choroplèthe des régions françaises
            # output_ui("fr_map") est rempli par server/energie/bilan.py → fr_map
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s3.get("icone", "")}),
                        ui.div(
                            # id_titre est le nom de l'output Shiny qui fournit le titre dynamique
                            ui.output_text(s3.get("id_titre", "map_title")),
                            class_="panel-title",
                        ),
                    ),
                    ui.div(ui.output_ui("fr_map"), class_="panel-body"),
                    ui.div(
                        _accordeon_aide(
                            s3.get("aide_html",     ""),
                            s3.get("id_accordeon",  "interp-bilan-map"),
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            # Camembert du mix de production (par filière, pour la région sélectionnée)
            # output_widget("prod_pie") est rempli par server/energie/bilan.py → prod_pie
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s4.get("icone", "")}),
                        ui.div(
                            ui.output_text(s4.get("id_titre", "pie_title")),
                            class_="panel-title",
                        ),
                    ),
                    ui.div(
                        # Menu de sélection de région (rendu dynamiquement par le serveur)
                        ui.div({"class": "mb-2"}, ui.output_ui("region_selector")),
                        sw.output_widget("prod_pie"),
                        class_="panel-body",
                    ),
                    ui.div(
                        _accordeon_aide(
                            s4.get("aide_html",    ""),
                            s4.get("id_accordeon", "interp-bilan-pie"),
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            class_="row gap-4 row-eq",
        ),

        ui.tags.hr(class_="section-sep"),

        # Graphique d'évolution temporelle (aires empilées 2014-2024)
        # output_widget("area_chart") est rempli par server/energie/bilan.py → area_chart
        ui.div(
            ui.div(
                {"class": "panel panel-compact"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": s5.get("icone", "")}),
                    ui.div(
                        ui.output_text(s5.get("id_titre", "area_title")),
                        class_="panel-title",
                    ),
                ),
                ui.div(
                    # Curseur de sélection d'année — déclenche la mise à jour de la carte ET du camembert
                    ui.div(
                        {"class": "mb-2"},
                        ui.input_slider(
                            "year",
                            s5.get("libelle_curseur", ""),
                            min=2014, max=2024, value=2024,
                            step=1, width="100%", sep="",
                        ),
                    ),
                    ui.div(sw.output_widget("area_chart"), style="width:100%"),
                    ui.div(
                        _accordeon_aide(
                            s5.get("aide_html",    ""),
                            s5.get("id_accordeon", "interp-bilan-area"),
                        ),
                        class_="panel-foot",
                    ),
                    class_="panel-body",
                    style="width:100%",
                ),
            ),
            class_="col-12",
        ),
    )
