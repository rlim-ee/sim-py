# ui/donnees/__init__.py — Coordinateur du module "Données"
# Textes : www/texts/donnees/gestionnaire.json
from shiny import ui

from ui._common import dropcard, app_footer, back_home_button, load_texts

from . import gestionnaire_ui


def _bloc_donnees():
    tx = load_texts("donnees.gestionnaire")
    return ui.div(
        dropcard(
            tx.get("presentation_summary", ""),
            ui.p(tx.get("module_intro", "")),
        ),
        gestionnaire_ui.bloc_hq_flapd(),
    )


def donnees_ui():
    return ui.div(

        # =====================================================
        # SCRIPT GLOBAL — CLICS FOLIUM (OBLIGATOIRE)
        # =====================================================
        ui.tags.script(
            """
(function () {
  window.addEventListener("message", function (event) {
    if (!event.data) return;

    if (event.data.type === "hub_click") {
      if (window.Shiny && Shiny.setInputValue) {
        Shiny.setInputValue(
          "hub_click",
          event.data.hub,
          { priority: "event" }
        );
      }
    }
  });
})();
"""
        ),

        # =====================================================
        # CONTENU
        # =====================================================
        ui.div(
            ui.br(),
            back_home_button(),
            class_="container-fluid px-3 px-lg-4 mb-3",
        ),

        ui.div(
            _bloc_donnees(),
            class_="container-fluid mb-5",
        ),

        ui.div(
            app_footer(),
            class_="container-fluid mb-5",
        ),
    )
