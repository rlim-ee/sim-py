# server/donnees/__init__.py — serveur du module Données
#
# Ce module délègue intégralement au gestionnaire,
# qui analyse les sièges sociaux des opérateurs de data centers FLAP-D.
from pathlib import Path
from . import gestionnaire


def server(input, output, session, app_dir: Path):
    gestionnaire.server(input, output, session, app_dir)
