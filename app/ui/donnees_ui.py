# donnees_ui.py — Module Données
from shiny import ui
import shinywidgets as sw

from ui.energie_ui import dropcard, app_footer


# =========================================================
# BLOC FLAP-D — UI ORIGINALE (INCHANGÉE)
# =========================================================
def bloc_hq_flapd():

    def head_title_only(icon_class: str, title_ui):
        return ui.div(
            {"class": "panel-head"},
            ui.tags.i({"class": icon_class}),
            ui.div(title_ui, class_="panel-title"),
        )

    def help_accordion(title: str, content_ui):
        return ui.accordion(
            ui.accordion_panel(
                title,
                ui.div(
                    content_ui,
                    class_="text-muted",
                    style="font-size:13px;line-height:1.45;",
                ),
            )
        )

    instruction_map = ui.p(
        "Cliquez sur un ",
        ui.strong("hub"),
        " pour afficher la vue détaillée. ",
        "Re-cliquez sur le ",
        ui.strong("hub actif"),
        " pour revenir à la vue globale.",
        style="margin:0 0 10px 0;",
    )

    return ui.card(

        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": "fa-solid fa-globe me-2"}),
            "FLAP-D — Pays d’origine (HQ)",
        ),

        ui.div(
            {"class": "section-lead"},
            ui.h2("Europe"),
            ui.p(
                "Ce module explore l’origine géographique des entreprises opérant les data centers "
                "des cinq hubs FLAP-D : Francfort, Londres, Amsterdam, Paris et Dublin."
            ),
        ),

        # ===============================
        # LIGNE 1 — CARTE + TREEMAP
        # ===============================
        ui.div(
            ui.div(

                # ---- CARTE ----
                ui.div(
                    ui.div(
                        {"class": "panel"},

                        head_title_only(
                            "fa-solid fa-layer-group",
                            ui.output_text("titre_carte_hq"),
                        ),

                        ui.div(
                            instruction_map,

                            ui.div(
                                {
                                    "style": (
                                        "width:100%;height:0;padding-bottom:65%;"
                                        "position:relative;overflow:hidden;border-radius:8px;"
                                    )
                                },
                                ui.div(
                                    {
                                        "style": (
                                            "position:absolute;"
                                            "top:0;left:0;width:100%;height:100%;"
                                        )
                                    },
                                    ui.output_ui("map_hq_flapd"),
                                ),
                            ),
                            class_="panel-body",
                        ),

                        ui.div(
                            ui.div(ui.output_ui("commentaire_carte_hq"), style="color:#111;"),

                            ui.div(
                                {"class": "mt-2"},
                                help_accordion(
                                    "Comment lire cette carte ?",
                                    ui.div(
                                        ui.p("Coloration : part (%) des entreprises du hub."),
                                        ui.p("Flèches : pays siège → hub."),
                                        ui.p("Points gris : localisation des sièges."),
                                    ),
                                ),
                            ),
                            class_="panel-foot",
                        ),
                    ),
                    class_="col",
                ),

                # ---- TREEMAP ----
                ui.div(
                    ui.div(
                        {"class": "panel"},

                        head_title_only(
                            "fa-solid fa-chart-area",
                            ui.div("Répartition des entreprises"),
                        ),

                        ui.div(
                            ui.div(
                                ui.output_ui("treemap_hq"),
                                style="width:100%;height:420px;",
                                ),
                            class_="panel-body",
                            ),

                        ui.div(
                            ui.div(ui.output_ui("commentaire_treemap_hq"), style="color:#111;"),

                            ui.div(
                                {"class": "mt-2"},
                                help_accordion(
                                    "Lecture du treemap",
                                    ui.div(
                                        ui.p("Surface = importance relative."),
                                        ui.p("Cliquer pour zoomer."),
                                    ),
                                ),
                            ),
                            class_="panel-foot",
                        ),
                    ),
                    class_="col",
                ),

                class_="row gap-4 row-eq",
            ),
            class_="mt-3",
        ),

        ui.tags.hr(class_="section-sep"),

        # ===============================
        # LIGNE 2 — TOP 5
        # ===============================
        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},

                    head_title_only(
                        "fa-solid fa-ranking-star",
                        ui.output_text("titre_top5"),
                    ),

                    ui.div(
                        ui.output_data_frame("top5_table"),
                        class_="panel-body",
                    ),

                    ui.div(
                        ui.div(ui.output_ui("commentaire_top5_hq"), style="color:#111;"),

                        ui.div(
                            {"class": "mt-2"},
                            help_accordion(
                                "Que montre ce Top 5 ?",
                                ui.div(
                                    ui.p("Nombre de DC = présence."),
                                    ui.p("Score share_info = transparence."),
                                ),
                            ),
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col-12",
            ),
            class_="row",
        ),

        full_screen=True,
        class_="thematique-card",
    )


# =========================================================
# MODULE DONNÉES — CONTENEUR
# =========================================================
def bloc_donnees():

    return ui.div(

        dropcard(
            "Présentation du module Données",
            ui.p(
                "Ce module documente les sources et présente certains jeux "
                "de données clés utilisés dans les analyses."
            ),
        ),

        bloc_hq_flapd(),
    )


# =========================================================
# UI PRINCIPALE — DONNÉES
# =========================================================
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
            ui.input_action_button(
                "back_home",
                "← Retour à l’accueil",
                class_="btn btn-outline-secondary mb-3",
            ),
            class_="container-fluid px-3 px-lg-4",
        ),

        ui.div(
            bloc_donnees(),
            class_="container-fluid mb-5",
        ),

        ui.div(
            app_footer(),
            class_="container-fluid mb-5",
        ),
    )
