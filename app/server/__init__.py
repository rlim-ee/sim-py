# server/__init__.py — chef d'orchestre du serveur
#
# Ce fichier gère deux choses fondamentales :
#
#   1. LA NAVIGATION entre les grandes pages (accueil, énergie, données)
#      Chaque bouton de navigation (go_energie, go_donnees…) déclenche
#      une mise à jour de current_page, ce qui provoque un re-rendu de la page.
#
#   2. LE CHARGEMENT PARESSEUX ("lazy") des serveurs de modules
#      Les calculs du module Énergie ne démarrent qu'au premier clic sur
#      "Énergie", pas au lancement de l'application. Cela évite de charger
#      les données de tous les modules d'un coup au démarrage.
#
# Comment ça marche avec Shiny :
#   - reactive.Value() stocke une valeur observable. Quand elle change,
#     tous les outputs qui en dépendent se recalculent automatiquement.
#   - @reactive.effect lance du code en réponse à un changement.
#     @reactive.event(input.mon_bouton) restreint ce déclenchement à
#     un clic spécifique sur un bouton.
#   - @output + @render.ui produit du HTML que Shiny place dans la page
#     à l'endroit défini par output_ui("page") dans l'interface.
from pathlib import Path
from shiny import reactive, render

from server import energie
from server import donnees


def make_server(app_dir: Path):

    def server(input, output, session):

        # =========================================================
        # NAVIGATION INTERNE
        # current_page est la source de vérité : quand elle change,
        # le rendu de la page change automatiquement.
        # =========================================================
        current_page = reactive.Value("home")

        # Quand l'utilisateur clique sur "Énergie" depuis l'accueil
        @reactive.effect
        @reactive.event(input.go_energie)
        def _go_energie():
            current_page.set("energie")

        # Quand l'utilisateur clique sur "Données" depuis l'accueil
        @reactive.effect
        @reactive.event(input.go_donnees)
        def _go_donnees():
            current_page.set("donnees")

        # Retour à l'accueil depuis n'importe quel module
        # (le bouton back_home est présent dans chaque en-tête de module)
        @reactive.effect
        @reactive.event(input.back_home)
        def _back_home():
            current_page.set("home")

        # =========================================================
        # RENDU UI DYNAMIQUE
        # Ce bloc fabrique le contenu principal de la page en fonction
        # du module actif. output_ui("page") dans ui/__init__.py
        # est le conteneur qui accueille ce rendu.
        # =========================================================
        @output
        @render.ui
        def page():
            page_name = current_page.get()

            # Les imports sont à l'intérieur du if pour éviter les
            # imports circulaires et accélérer le démarrage.
            if page_name == "home":
                from ui.home_ui import home_ui
                return home_ui()

            if page_name == "energie":
                from ui.energie import energie_ui
                return energie_ui()

            if page_name == "donnees":
                from ui.donnees import donnees_ui
                return donnees_ui()

        # =========================================================
        # SERVEURS PAR GRAND MODULE (LAZY)
        # Chaque module a un drapeau *_loaded qui empêche de
        # réinitialiser le serveur si l'utilisateur revient sur la page.
        # Les calculs lourds (chargement CSV, GeoJSON…) ne se font
        # donc qu'une seule fois par session.
        # =========================================================

        energie_loaded = reactive.Value(False)
        donnees_loaded = reactive.Value(False)

        @reactive.effect
        def _load_energie_server():
            # Se déclenche à chaque changement de page, mais n'agit
            # que si on est sur "energie" ET que c'est la première visite.
            if current_page.get() == "energie" and not energie_loaded.get():
                energie.server(input, output, session, app_dir)
                energie_loaded.set(True)

        @reactive.effect
        def _load_donnees_server():
            if current_page.get() == "donnees" and not donnees_loaded.get():
                donnees.server(input, output, session, app_dir)
                donnees_loaded.set(True)

    return server
