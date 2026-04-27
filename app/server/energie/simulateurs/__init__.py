# server/energie/simulateurs/__init__.py — coordinateur du package Simulateurs
#
# Ce package regroupe les deux simulateurs énergétiques, chacun dans son fichier :
#
#   predictif.py   — simulateur "Analyse prédictive"
#                    pilote par trois curseurs (nb DC, facteur de charge, puissance)
#                    et affiche une projection de consommation nationale + équivalences
#
#   comparatif.py  — simulateur "Analyse comparative"
#                    convertit la consommation d'un DC en nombre d'habitants équivalents
#                    selon différents profils nationaux
#
# Les utilitaires communs (chargement CSV, style Plotly, constantes physiques)
# vivent dans _shared.py pour éviter la duplication entre les deux simulateurs.
from pathlib import Path


def server(input, output, session, app_dir: Path):
    from . import predictif
    from . import comparatif
    predictif.server(input, output, session, app_dir)
    comparatif.server(input, output, session, app_dir)
