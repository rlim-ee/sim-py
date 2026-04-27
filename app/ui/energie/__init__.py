# ui/energie/__init__.py — Coordinateur du module "Énergie"
#
# Ce fichier assemble les six sous-modules d'interface en une seule page structurée.
# Chaque sous-module correspond à un fichier ui/ ET un fichier server/ :
#
#   ui/energie/repartition_ui.py  ←→  server/energie/repartition.py
#   ui/energie/flapd_ui.py        ←→  server/energie/flapd.py
#   ui/energie/bilan_ui.py        ←→  server/energie/bilan.py
#   ui/energie/echanges_ui.py     ←→  server/energie/echanges.py
#   ui/energie/simulateurs/       ←→  server/energie/simulateurs/
#       ├── predictif_ui.py       ←→     ├── predictif.py
#       └── comparatif_ui.py      ←→     └── comparatif.py
#
# Les textes (titres, introductions, aides) viennent de www/texts/energie/.
# La structure visuelle : trois grandes "cartes" thématiques, chacune à onglets.
from shiny import ui

from ui._common import dropcard, app_footer, back_home_button, load_texts, html

from . import repartition_ui
from . import flapd_ui
from . import bilan_ui
from . import echanges_ui
from . import simulateurs   # sous-package contenant predictif_ui + comparatif_ui


# =====================================================================
# Carte 1 — Répartition des data centers
# =====================================================================
def _carte_repartition():
    """
    Carte à deux onglets : vue Europe (tous pays) et vue FLAP-D (5 hubs).
    Les titres des onglets viennent des JSON respectifs via libelle_onglet.
    """
    tx_repartition = load_texts("energie.repartition")
    tx_flapd       = load_texts("energie.flapd")
    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": tx_repartition.get("icone_carte", "")}),
            tx_repartition.get("titre_carte", ""),
        ),
        ui.navset_tab(
            ui.nav_panel(tx_repartition.get("libelle_onglet", ""), repartition_ui.panel()),
            ui.nav_panel(tx_flapd.get("libelle_onglet",       ""), flapd_ui.panel()),
            id="tabs_repartition",
        ),
        class_="thematique-card",
    )


# =====================================================================
# Carte 2 — Bilan énergétique
# =====================================================================
def _carte_bilan():
    """
    Carte à deux onglets : bilan régional France et échanges France-Europe.
    Les textes viennent de energie/bilan.json et energie/echanges.json.
    """
    tx_bilan   = load_texts("energie.bilan")
    tx_echanges = load_texts("energie.echanges")
    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": tx_bilan.get("icone_carte", "")}),
            tx_bilan.get("titre_carte", ""),
        ),
        ui.navset_tab(
            ui.nav_panel(tx_bilan.get("libelle_onglet",    ""), bilan_ui.panel()),
            ui.nav_panel(tx_echanges.get("libelle_onglet", ""), echanges_ui.panel()),
            id="tabs_bilan",
        ),
        class_="thematique-card",
    )


# =====================================================================
# Page principale du module Énergie
# =====================================================================
def energie_ui():
    """
    Assemble la page complète du module Énergie :
      1. Bouton retour accueil
      2. Encadré de présentation générale (rétractable)
      3. Carte Répartition
      4. Carte Bilan énergétique
      5. Carte Simulateurs
      6. Pied de page
    """
    intro = load_texts("energie._intro")
    return ui.div(

        ui.div(

            # Bouton retour — navigue vers l'accueil sans rechargement de page
            ui.br(),
            ui.div(
                back_home_button(),
                class_="container-fluid px-3 px-lg-4 mb-3",
            ),

            # Introduction générale repliable
            ui.div(
                dropcard(
                    html(intro.get("resume_html", "")),
                    html(intro.get("corps_html",  "")),
                    ouvert=False,
                ),
                class_="container-fluid mb-5",
            ),

            # Carte 1 — Répartition géographique
            ui.div(
                _carte_repartition(),
                class_="container-fluid mb-5",
            ),

            # Carte 2 — Bilan et échanges électriques
            ui.div(
                _carte_bilan(),
                class_="container-fluid mb-5",
            ),

            # Carte 3 — Simulateurs (prédictif + comparatif)
            ui.div(
                simulateurs.card(),
                class_="container-fluid mb-5",
            ),

            ui.div(
                app_footer(),
                class_="container-fluid mb-5",
            ),

            class_="container-fluid px-0",
        ),
    )
