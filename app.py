# app.py — point d’entrée
from shiny import App
from pathlib import Path
from ui import app_ui
from server import make_server

# app.py
import os
os.environ["SHINY_SUPPRESS_CLIENT_ERRORS"] = "1"   # désactive l’overlay si la version le supporte


app = App(app_ui, make_server(Path(__file__).parent))
