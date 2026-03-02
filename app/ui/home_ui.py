# ui/home.py
from shiny import ui
from ui.energie_ui import app_footer

def home_ui():
    return ui.div(
        {"class": "container-app"},

        # =========================================================
        # HERO / INTRO
        # =========================================================
        ui.div(
            {"class": "section-lead"},
            ui.h1("Matérialité du numérique"),
            ui.p(
                "blabla"
            ),
        ),

        # =========================================================
        # ACCÈS AUX MODULES
        # =========================================================
        ui.div(
            {"class": "row gap-4 row-eq"},

            # ---------- MODULE ÉNERGIE ----------
            ui.div(
                {"class": "col"},
                ui.div(
                    {"class": "card"},
                    ui.div(
                        {"class": "card-title"},
                        ui.tags.i({"class": "fa-solid fa-bolt me-2"}),
                        "Énergie & Data Centers",
                    ),
                    ui.p(
                        "blabla"
                    ),
                    ui.hr(),
                    ui.input_action_button(
                        "go_energie",
                        "Accéder au module",
                        class_="btn btn-primary",
                    ),
                ),
            ),

            # ---------- MODULE DONNÉES ----------
            ui.div(
                {"class": "col"},
                ui.div(
                    {"class": "card"},
                    ui.div(
                        {"class": "card-title"},
                        ui.tags.i({"class": "fa-solid fa-microchip me-2"}),
                        "Données",
                    ),
                    ui.p(
                        "blabla"
                    ),
                    ui.hr(),
                    ui.input_action_button(
                        "go_donnees",
                        "Accéder au module",
                        class_="btn btn-primary",
                    ),
                ),
            ),
            
            
            # ---------- MODULE EXTRACTION ----------
            #ui.div(
             #   {"class": "col"},
              #  ui.div(
               #     {"class": "card"},
                #    ui.div(
                 #       {"class": "card-title"},
                  #      ui.tags.i({"class": "fa-solid fa-bolt me-2"}),
                   #     "Extraction",
                    #),
                    #ui.p(
                     #   "blabla"
                   # ),
                    #ui.hr(),
                    #ui.input_action_button(
                     #   "go_extraction",
                      #  "Accéder au module",
                       # class_="btn btn-primary",
                   # ),
                #),
            #),
            
            
        ),
        app_footer(),

    )
