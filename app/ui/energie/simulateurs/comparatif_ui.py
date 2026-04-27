# ui/energie/simulateurs/comparatif_ui.py — onglet "Analyse comparative"
#
# Ce simulateur répond à la question : "combien d'habitants faut-il pour
# consommer autant qu'un data center ?"
#
# L'utilisateur choisit des profils de consommation (Qatar, France, monde…)
# dans la barre latérale, et voit un graphique à barres comparer ces profils
# aux paliers du projet Data One (2025 → 2035).
#
# Un second outil permet une comparaison entièrement personnalisée.
# Les valeurs calculées viennent de server/energie/simulateurs/comparatif.py.
# Les textes viennent de www/texts/energie/simulateurs/comparatif.json.
from shiny import ui
import shinywidgets as sw

from ui._common import dropcard, load_texts, html, savoir_plus_label


def _encart_pays(pays: dict):
    """
    Encart de comparaison pour un pays : libellé, valeur en habitants,
    population totale et pourcentage de la population.
    Chaque champ output_* est rempli en temps réel par le serveur.
    """
    return ui.div(
        {"class": "metric"},
        ui.h4(pays.get("libelle", "")),
        ui.div({"class": "value"}, ui.output_text(pays.get("output_value", ""))),
        ui.tags.small(ui.output_text(pays.get("output_pop", ""))),
        ui.tags.small(ui.output_text(pays.get("output_pct", ""))),
    )


def panel():
    """Construit le panneau complet de l'onglet Analyse comparative."""
    tx      = load_texts("energie.simulateurs.comparatif")
    barre   = tx.get("barre_laterale", {})
    s1      = tx.get("section1", {})
    s2      = tx.get("section2", {})
    s3      = tx.get("section3", {})
    s4      = tx.get("section4", {})
    s5      = tx.get("section5", {})
    pays    = s4.get("pays", {})

    return ui.layout_sidebar(
        # Barre latérale : choix des profils de consommation + comparaison personnalisée
        ui.sidebar(
            ui.h4(barre.get("titre_profils",     "")),
            # checkbox_group_conso est rendu dynamiquement par le serveur
            # (il charge les profils disponibles depuis les données)
            ui.output_ui("checkbox_group_conso"),
            ui.hr(), ui.hr(), ui.hr(), ui.hr(), ui.hr(),
            ui.hr(), ui.hr(), ui.hr(), ui.hr(), ui.hr(),
            ui.hr(), ui.hr(), ui.hr(), ui.hr(), ui.hr(),
            ui.h4(barre.get("titre_personnalise", "")),
            # entites_dyn et entite_controls : interface de comparaison personnalisée
            ui.output_ui("entites_dyn"),
            ui.output_ui("entite_controls"),
            class_="sidebar",
        ),

        # Introduction
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2(s1.get("titre",            "")),
            ui.p(html(s1.get("introduction_html", ""))),
        ),

        # Encadré "Savoir plus" — jalons Data One + formule de conversion
        dropcard(
            s2.get("titre", savoir_plus_label()),
            html(s2.get("contenu_html", "")),
        ),

        # Graphique à barres par profil (rendu par server → barplot)
        ui.div(
            {"class": "card"},
            ui.h3(s3.get("titre", ""), class_="section-title"),
            sw.output_widget("barplot"),
            ui.p(html(s3.get("lecture_html", ""))),
        ),

        # Focus 3 pays : Qatar, France, Mali (pour un DC de 1 GW)
        ui.div(
            {"class": "card"},
            ui.h3(html(s4.get("titre_html", "")), class_="section-title"),
            ui.row(
                ui.column(4, _encart_pays(pays.get("qatar",  {}))),
                ui.column(4, _encart_pays(pays.get("france", {}))),
                ui.column(4, _encart_pays(pays.get("mali",   {}))),
            ),
        ),

        # Outil de comparaison personnalisée (rendu par server → barplot_personalisee)
        ui.div(
            {"class": "card", "id": "personalized-card"},
            ui.h3(s5.get("titre", ""), class_="section-title"),
            sw.output_widget("barplot_personalisee"),
        ),

        fillable=True,
    )
