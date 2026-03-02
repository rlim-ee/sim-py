# server/extraction/__init__.py
from pathlib import Path


def server(input, output, session, app_dir: Path):
    """
    Serveur principal du module Extraction.
    Les sous-modules sont importés localement
    pour éviter toute circular import.
    """

    from . import matieres_premieres

    matieres_premieres.server(input, output, session, app_dir)
