# app.py — point d’entrée
from shiny import App
from pathlib import Path
from ui import app_ui
from server import make_server

app = App(app_ui, make_server(Path(__file__).parent))
