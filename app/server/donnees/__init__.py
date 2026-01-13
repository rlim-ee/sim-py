# server/donnees/__init__.py — wrapper module Données (FLAP-D)
from pathlib import Path
from . import gestionnaire


def server(input, output, session, app_dir: Path):
    # Appel STRICT du serveur FLAP-D (modulaire, identique au rendu original)
    gestionnaire.server(input, output, session, app_dir)
