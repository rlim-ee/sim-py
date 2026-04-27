# server/energie/__init__.py — serveur du module Énergie
#
# Ce fichier initialise tous les sous-modules du module Énergie
# quand l'utilisateur navigue pour la première fois vers cette section.
#
# Les imports sont faits à l'intérieur de la fonction server() (et non
# au niveau du module) pour éviter les imports circulaires : chaque
# sous-module importe lui-même des choses de server._common, et si tout
# était importé au niveau global, Python ne saurait plus dans quel ordre
# charger les fichiers.
#
# Chaque sous-module expose sa propre fonction server() qui enregistre
# ses outputs Shiny auprès de l'objet "output" partagé par toute la session.
from pathlib import Path


def server(input, output, session, app_dir: Path):
    from . import repartition
    from . import flapd
    from . import bilan
    from . import echanges
    from . import simulateurs

    # Chaque appel enregistre les outputs de ce sous-module.
    # L'ordre n'a pas d'importance fonctionnelle : Shiny résout
    # les dépendances entre outputs au moment de l'exécution.
    repartition.server(input, output, session, app_dir)
    flapd.server(input, output, session, app_dir)
    bilan.server(input, output, session, app_dir)
    echanges.server(input, output, session, app_dir)
    simulateurs.server(input, output, session, app_dir)
