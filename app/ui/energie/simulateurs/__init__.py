# ui/energie/simulateurs/__init__.py — Coordinateur UI "Simulateurs"
#
# Cette carte regroupe les deux simulateurs en deux onglets :
#
#   Onglet 1 — Analyse prédictive (predictif_ui.py)
#     L'utilisateur règle le nombre de DC, la puissance et le facteur de charge.
#     Le graphique montre la consommation projetée face aux scénarios RTE 2025-2035.
#
#   Onglet 2 — Analyse comparative (comparatif_ui.py)
#     Traduit la consommation d'un DC en nombre d'habitants équivalents
#     selon plusieurs profils (France, Qatar, Mali, monde).
#
# Textes du cadre (titre carte, libellés onglets) : www/texts/energie/simulateurs/_frame.json
from shiny import ui

from ui._common import load_texts

from . import predictif_ui
from . import comparatif_ui


def card():
    """Construit la carte 'Simulateurs' à deux onglets."""
    cadre = load_texts("energie.simulateurs._frame")
    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.strong(cadre.get("titre_carte", "")),
        ),
        ui.navset_tab(
            ui.nav_panel(
                cadre.get("libelle_predictif",  ""),
                predictif_ui.panel(),
            ),
            ui.nav_panel(
                cadre.get("libelle_comparatif", ""),
                comparatif_ui.panel(),
            ),
            id="sim_tabs",
        ),
        class_="thematique-card",
    )
