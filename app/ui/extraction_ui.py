# donnees_ui.py — Module Extraction
from shiny import ui
import shinywidgets as sw

from ui.energie_ui import dropcard, app_footer


# ---------- helper encadré déroulant ----------
def dropcard(title: str, *children, open: bool = False):
    attrs = {"class": "dropcard"}
    if open:
        attrs["open"] = "open"
    return ui.tags.details(
        ui.tags.summary(title),
        ui.div(*children, class_="dropbody"),
        **attrs,
    )


# =====================================================
# MODULE — EXTRACTION DES MATIÈRES PREMIÈRES
# =====================================================
def bloc_extraction():
    """Carte d'extraction des matières premières (sélection par métal)"""

    extraction_panel = ui.div(

        # ---------- Intro ----------
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2("Extraction des matières premières"),
            ui.p(
                "Ce module présente la ",
                ui.strong("répartition géographique de l’extraction des matières premières"),
                " à l’échelle mondiale. "
                "Il permet d’identifier les pays producteurs dominants selon le métal sélectionné "
                "et de mettre en évidence les dépendances géopolitiques associées."
            ),
        ),

        # ---------- Savoir plus ----------
        dropcard(
            "Savoir plus",
            ui.div(
                ui.p(
                    ui.strong("🔍 Enjeux stratégiques : "),
                    "les métaux critiques (lithium, cobalt, nickel, cuivre, terres rares, etc.) "
                    "sont indispensables aux technologies numériques, énergétiques et militaires. "
                    "Leur extraction est fortement concentrée dans un nombre limité de pays."
                ),
                ui.p(
                    ui.strong("🌍 Lecture spatiale : "),
                    "la carte permet d’observer les déséquilibres territoriaux entre pays producteurs "
                    "et pays consommateurs, ainsi que les risques liés à la dépendance aux importations."
                ),
            ),
        ),

        # ---------- Filtres ----------
        ui.div(
            ui.div(
                {"class": "panel"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": "fa-solid fa-sliders"}),
                    ui.h4("Paramètres", class_="panel-title"),
                ),
                ui.div(
                    ui.row(
                        ui.column(
                            4,
                            ui.input_select(
                                "metal_selected",
                                "Métal extrait",
                                choices={
                                    "lithium": "Lithium",
                                    "cobalt": "Cobalt",
                                    "nickel": "Nickel",
                                    "cuivre": "Cuivre",
                                    "terres_rares": "Terres rares",
                                },
                                selected="lithium",
                            ),
                        ),
                        ui.column(
                            8,
                            ui.p(
                                "La sélection d’un métal met à jour automatiquement la carte "
                                "afin d’afficher les volumes d’extraction correspondants.",
                                class_="form-text mt-4",
                            ),
                        ),
                    ),
                    class_="panel-body",
                ),
            ),
            class_="mb-4",
        ),

        # ---------- Carte ----------
        ui.div(
            ui.div(
                {"class": "panel"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": "fa-solid fa-map-location-dot"}),
                    ui.h4("Carte mondiale de l’extraction", class_="panel-title"),
                ),
                ui.div(
                    ui.output_ui("extraction_map"),
                    class_="panel-body",
                ),
                ui.div(
                    ui.p(
                        ui.strong("🗺️ Lecture de la carte : "),
                        "les teintes représentent les volumes d’extraction du métal sélectionné "
                        "(en tonnes). Les pays les plus foncés concentrent les plus fortes productions."
                    ),
                    class_="panel-foot",
                ),
            ),
            class_="mb-4",
        ),
    )

    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": "fa-solid fa-mountain me-2"}),
            "Extraction des matières premières",
        ),
        extraction_panel,
        class_="thematique-card",
    )


# =====================================================
# UI PRINCIPALE — EXTRACTION
# =====================================================
def extraction_ui():
    return ui.div(

        # ---------- Navigation ----------
        ui.div(
            ui.input_action_button(
                "back_home",
                "← Retour à l’accueil",
                class_="btn btn-outline-secondary mb-3",
            ),
            class_="container-fluid px-3 px-lg-4",
        ),

        # ---------- Présentation ----------
        ui.div(
            dropcard(
                "Présentation générale",
                ui.p(
                    "Ce module est dédié à l’analyse spatiale de l’extraction des matières premières "
                    "stratégiques. Il s’inscrit dans une réflexion plus large sur la matérialité du "
                    "numérique et la dépendance des infrastructures aux ressources minérales."
                ),
                open=False,
            ),
            class_="container-fluid mb-5",
        ),

        # ---------- Module Extraction ----------
        ui.div(
            bloc_extraction(),
            class_="container-fluid mb-5",
        ),

        class_="container-fluid px-0",
    )
