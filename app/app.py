# app.py — point d'entrée de l'application
#
# Shiny for Python fonctionne comme une application web classique :
# une partie "interface" (ce que l'utilisateur voit) et une partie "serveur"
# (ce qui calcule et répond aux interactions).
#
# App(app_ui, make_server(...)) assemble ces deux parties.
# Quand un utilisateur ouvre la page, Shiny appelle app_ui pour construire
# l'interface, puis crée une session serveur qui reste active tant que
# la page est ouverte.
#
# make_server() reçoit le chemin du dossier de l'application pour que
# les modules serveur puissent accéder aux fichiers de données (CSV, GeoJSON…)
# sans hardcoder leur emplacement.
from shiny import App
from pathlib import Path
from ui import app_ui
from server import make_server

app = App(app_ui, make_server(Path(__file__).parent))
