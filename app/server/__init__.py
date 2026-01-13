# server/__init__.py — orchestration + navigation
from pathlib import Path
from shiny import reactive, render

from server import energie
from server import donnees 


def make_server(app_dir: Path):

    def server(input, output, session):

        # =========================================================
        # NAVIGATION INTERNE
        # =========================================================
        current_page = reactive.Value("home")

        # ---------- home → énergie ----------
        @reactive.effect
        @reactive.event(input.go_energie)
        def _go_energie():
            current_page.set("energie")

        # ---------- home → données ----------
        @reactive.effect
        @reactive.event(input.go_donnees)
        def _go_donnees():
            current_page.set("donnees")

        # ---------- énergie / données → home ----------
        @reactive.effect
        @reactive.event(input.back_home)
        def _back_home():
            current_page.set("home")

        # =========================================================
        # RENDU UI DYNAMIQUE
        # =========================================================
        @output
        @render.ui
        def page():

            page_name = current_page.get()

            if page_name == "home":
                from ui.home_ui import home_ui
                return home_ui()

            if page_name == "energie":
                from ui.energie_ui import energie_ui
                return energie_ui()

            if page_name == "donnees":
                from ui.donnees_ui import donnees_ui
                return donnees_ui()

        # =========================================================
        # SERVEURS PAR GRAND MODULE (LAZY)
        # =========================================================

        energie_loaded = reactive.Value(False)
        donnees_loaded = reactive.Value(False)

        # ---------- serveur ÉNERGIE ----------
        @reactive.effect
        def _load_energie_server():
            if current_page.get() == "energie" and not energie_loaded.get():
                energie.server(input, output, session, app_dir)
                energie_loaded.set(True)

        # ---------- serveur DONNÉES ----------
        @reactive.effect
        def _load_donnees_server():
            if current_page.get() == "donnees" and not donnees_loaded.get():
                donnees.server(input, output, session, app_dir)
                donnees_loaded.set(True)

    return server
