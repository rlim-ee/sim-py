# ui/energie/flapd_ui.py — onglet "FLAP-D" du module Répartition
#
# Affiche une carte détaillée des data centers dans les 5 hubs européens
# (Francfort, Londres, Amsterdam, Paris, Dublin) et un tableau de synthèse.
#
# Des boutons permettent de zoomer sur chaque hub — quand l'utilisateur clique,
# le serveur (server/energie/flapd.py) recalcule la carte pour ce hub.
# Les textes viennent de www/texts/energie/flapd.json.
from shiny import ui

from ui._common import dropcard, load_texts, html, savoir_plus_label


def _bouton(btn: dict):
    """
    Construit un bouton de navigation hub à partir d'un bloc JSON.
    Le libellé peut être du texte simple (`libelle`) ou du HTML (`libelle_html`).
    Le clic est capté par le serveur via l'id du bouton (btn["id"]).
    """
    libelle = html(btn["libelle_html"]) if "libelle_html" in btn else btn.get("libelle", "")
    return ui.div(
        ui.input_action_button(
            btn.get("id",     ""),
            libelle,
            class_=btn.get("classe", ""),
        ),
        class_="col",
    )


def panel():
    """Construit le panneau complet de l'onglet FLAP-D."""
    tx   = load_texts("energie.flapd")
    s1   = tx.get("section1",  {})
    s2   = tx.get("section2",  {})
    s3   = tx.get("section3",  {})
    s4   = tx.get("section4",  {})
    btns = tx.get("boutons",   {})

    return ui.div(
        {"class": "pt-2"},

        # Titre + introduction
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2(s1.get("titre",            "")),
            ui.p(html(s1.get("introduction_html", ""))),
        ),

        # Encadré "Savoir plus" — explique la méthode de construction des données
        dropcard(
            s2.get("titre", savoir_plus_label()),
            html(s2.get("contenu_html", "")),
        ),

        # Carte FLAP-D — les cercles sont rendus par server/energie/flapd.py → map_flapd_sites
        ui.div(
            {"class": "panel"},
            ui.div(
                {"class": "panel-head"},
                ui.tags.i({"class": s3.get("icone", "")}),
                ui.h4(s3.get("titre", ""), class_="panel-title"),
            ),
            ui.div(
                {"class": "panel-body"},
                ui.div(
                    {"style": "padding: 16px; border-radius: 8px;"},

                    # Boutons de sélection du hub — un clic = le serveur recharge la carte
                    ui.div(
                        {"class": "row gap-2 mb-3"},
                        _bouton(btns.get("frankfurt", {})),
                        _bouton(btns.get("london",    {})),
                        _bouton(btns.get("amsterdam", {})),
                        _bouton(btns.get("paris",     {})),
                        _bouton(btns.get("dublin",    {})),
                        _bouton(btns.get("reset",     {})),
                    ),

                    # Carte Folium injectée par le serveur
                    ui.output_ui("map_flapd_sites", class_="mt-3"),
                ),
            ),
            ui.div(
                {"class": "panel-foot"},
                ui.p(html(s3.get("note_html", ""))),
            ),
        ),

        # Tableau synthétique par hub (rendu par server → encarts_villes)
        ui.div(
            {"class": "panel mt-4"},
            ui.div(
                {"class": "panel-head"},
                ui.tags.i({"class": s4.get("icone", "")}),
                ui.h4(s4.get("titre", ""), class_="panel-title"),
            ),
            ui.div(
                {"class": "panel-body"},
                ui.output_ui("encarts_villes"),
            ),
            ui.div(
                {"class": "panel-foot"},
                ui.p(html(s4.get("note_html", ""))),
            ),
        ),
    )
