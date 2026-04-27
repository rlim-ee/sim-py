# ui/extraction/__init__.py — Coordinateur du module "Extraction"
# Textes : www/texts/extraction/matieres_premieres.json
from shiny import ui

from ui._common import dropcard, app_footer, back_home_button, load_texts

from . import matieres_premieres_ui


def extraction_ui():
    tx = load_texts("extraction.matieres_premieres")
    return ui.div(

        # ---------- Navigation ----------
        ui.div(
            back_home_button(),
            class_="container-fluid px-3 px-lg-4 mb-3",
        ),

        # ---------- Présentation ----------
        ui.div(
            dropcard(
                tx.get("presentation_summary", ""),
                ui.p(tx.get("page_intro", "")),
                open=False,
            ),
            class_="container-fluid mb-5",
        ),

        # ---------- Module Extraction ----------
        ui.div(
            matieres_premieres_ui.card(),
            class_="container-fluid mb-5",
        ),

        # ---------- Footer ----------
        ui.div(
            app_footer(),
            class_="container-fluid mb-5",
        ),

        class_="container-fluid px-0",
    )
