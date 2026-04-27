# ui/energie/echanges_ui.py — onglet "Échanges France-Europe" du module Bilan
#
# Affiche deux blocs de visualisation liés par des filtres communs :
#
#   Bloc A — Comparaison temporelle (graphique linéaire)
#     Exportations / importations / solde entre la France et ses voisins,
#     filtrable par pays, période, agrégation et lissage.
#
#   Bloc B — Mix énergétique (filtres communs)
#     Une carte Folium avec des camemberts par pays
#     + un graphique à barres empilées (mode % ou TWh)
#
# Les visualisations sont calculées par server/energie/echanges.py.
# Les textes viennent de www/texts/energie/echanges.json.
from shiny import ui
import shinywidgets as sw

from ui._common import (
    dropcard, load_texts, html,
    interp_title, savoir_plus_label,
)


def _accordeon_aide(contenu_html: str, valeur: str, titre_html: str | None = None):
    """
    Accordéon 'Aide à l'interprétation'.
    Si `titre_html` est fourni, il remplace le titre générique de _common.json.
    """
    noeud_titre = html(titre_html) if titre_html else interp_title()
    return ui.accordion(
        ui.accordion_panel(
            noeud_titre,
            html(contenu_html),
            value=valeur,
        ),
        open=False,
        class_="interp-accordion",
    )


def panel():
    """Construit le panneau complet de l'onglet Échanges France-Europe."""
    tx = load_texts("energie.echanges")
    s1 = tx.get("section1", {})
    s2 = tx.get("section2", {})
    s3 = tx.get("section3", {})
    s4 = tx.get("section4", {})
    s5 = tx.get("section5", {})
    s6 = tx.get("section6", {})

    # Paramètres des deux blocs de filtres (noms de champs depuis le JSON)
    p_comparaison = s3.get("parametres", {})
    p_filtres     = s4.get("parametres", {})

    return ui.div(

        # Titre + introduction
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2(s1.get("titre",            "")),
            ui.p(html(s1.get("introduction_html", ""))),
        ),

        # Encadré "Savoir plus" — contexte sur les échanges électriques France-Europe
        dropcard(
            s2.get("titre", savoir_plus_label()),
            html(s2.get("contenu_html", "")),
        ),

        # ====== Bloc A — Comparaison temporelle (graphique linéaire) ======
        # Le graphique "comp_plot" est produit par server/energie/echanges.py
        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s3.get("icone", "")}),
                        ui.h4(s3.get("titre", ""), class_="panel-title"),
                    ),
                    # Ligne 1 : sélection des pays + curseur de lissage
                    ui.div(
                        ui.row(
                            ui.column(
                                9,
                                # Groupe de cases à cocher pour choisir les pays à comparer.
                                # Les choix sont initialisés dynamiquement par le serveur
                                # en fonction des données disponibles (voir server/energie/echanges.py).
                                ui.input_checkbox_group(
                                    "ech_countries",
                                    p_comparaison.get("libelle_pays", ""),
                                    choices=[],
                                    selected=[],
                                    inline=True,
                                ),
                            ),
                            ui.column(
                                3,
                                # Lissage glissant (rolling mean) sur 1 à 6 mois
                                ui.input_slider(
                                    "ech_roll",
                                    p_comparaison.get("libelle_lissage", ""),
                                    min=1, max=6, value=1, step=1,
                                ),
                            ),
                        ),
                        class_="mb-2",
                    ),
                    # Ligne 2 : période, flux et temporalité
                    ui.div(
                        ui.row(
                            ui.column(
                                4,
                                # Sélecteur de période (date de début et de fin)
                                ui.input_date_range(
                                    "ech_cmp_period",
                                    p_comparaison.get("libelle_periode", ""),
                                    start="2019-01-01",
                                    end="2025-12-31",
                                    min="2005-01-01",
                                    max="2025-12-31",
                                    weekstart=1,
                                ),
                            ),
                            ui.column(
                                4,
                                # Choix du flux : exportations, importations ou solde net
                                ui.input_radio_buttons(
                                    "ech_cmp_metric",
                                    p_comparaison.get("libelle_flux", ""),
                                    choices=p_comparaison.get("choix_flux",       []),
                                    selected=p_comparaison.get("flux_defaut",     None),
                                    inline=True,
                                ),
                            ),
                            ui.column(
                                4,
                                # Agrégation mensuelle ou annuelle
                                ui.input_radio_buttons(
                                    "ech_cmp_agg",
                                    p_comparaison.get("libelle_temporalite", ""),
                                    choices=p_comparaison.get("choix_temporalite",   []),
                                    selected=p_comparaison.get("temporalite_defaut", None),
                                    inline=True,
                                ),
                            ),
                        ),
                        class_="mb-2",
                    ),
                    ui.div(sw.output_widget("comp_plot"), class_="panel-body"),
                    ui.div(
                        _accordeon_aide(
                            s3.get("aide_html",         ""),
                            s3.get("id_accordeon",      "interp-ech-compare"),
                            titre_html=s3.get("titre_accordeon_html"),
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col-12",
            ),
            class_="row gap-4",
        ),

        ui.hr(),

        # ====== Filtres communs au Bloc B (carte + graphique mix) ======
        ui.div(
            ui.div(
                {"class": "panel"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": s4.get("icone", "")}),
                    ui.h4(s4.get("titre", ""), class_="panel-title"),
                ),
                ui.div(
                    ui.row(
                        # Filtre 1 : année du mix (données Our World in Data)
                        ui.column(
                            4,
                            ui.input_select(
                                "ech_mix_year",
                                ui.tags.span(
                                    p_filtres.get("texte_avant_annee", ""),
                                    ui.tags.a(
                                        p_filtres.get("libelle_lien", ""),
                                        href=p_filtres.get("url_lien", "#"),
                                        target="_blank",
                                        rel="noopener noreferrer",
                                    ),
                                    p_filtres.get("texte_apres_annee", ""),
                                ),
                                choices=[str(a) for a in range(2014, 2025)],
                                selected="2024",
                            ),
                        ),
                        # Filtre 2 : filière de production à isoler (ou toutes)
                        ui.column(
                            4,
                            ui.input_select(
                                "ech_mix_filiere",
                                p_filtres.get("libelle_filiere", ""),
                                choices=p_filtres.get("choix_filieres", {}),
                                selected="all",
                            ),
                        ),
                        # Filtre 3 : mode d'affichage du graphique (% ou TWh)
                        ui.column(
                            4,
                            ui.input_switch(
                                "ech_plot_mode",
                                p_filtres.get("libelle_mode", ""),
                                value=True,
                            ),
                            ui.div(
                                p_filtres.get("aide_mode", ""),
                                class_="form-text",
                            ),
                        ),
                    ),
                    class_="panel-body",
                ),
            ),
            class_="mb-3",
        ),

        # ====== Bloc B — Carte mix + Graphique mix (côte à côte) ======
        ui.div(
            # Carte Folium avec camemberts par pays (rendu par server → map_elec)
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s5.get("icone", "")}),
                        ui.h4(s5.get("titre", ""), class_="panel-title"),
                    ),
                    ui.div(ui.output_ui("map_elec"), class_="panel-body"),
                    ui.div(
                        _accordeon_aide(
                            s5.get("aide_html",    ""),
                            s5.get("id_accordeon", "interp-mix-map"),
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            # Graphique à barres empilées (rendu par server → bar_exports)
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": s6.get("icone", "")}),
                        ui.h4(s6.get("titre", ""), class_="panel-title"),
                    ),
                    ui.div(sw.output_widget("bar_exports"), class_="panel-body"),
                    ui.div(
                        ui.p(html(s6.get("note_html", "")), class_="mt-2 mb-0"),
                        class_="panel-foot",
                    ),
                    ui.div(
                        _accordeon_aide(
                            s6.get("aide_html",    ""),
                            s6.get("id_accordeon", "interp-mix-bar"),
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            class_="row gap-4 row-eq",
        ),

        ui.hr(),
    )
