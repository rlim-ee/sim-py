# server/__init__.py — orchestration des 3 serveurs
from pathlib import Path
from . import repartition, bilan, simulateurs, echanges, FLAPD, gestionnaire_DC

def make_server(app_dir: Path):
    def server(input, output, session):
        # 1) Répartition des data centers (carte Europe)
        repartition.server(input, output, session, app_dir)
        # 2) Répartition des data centers (FLAPD)
        FLAPD.server(input, output, session, app_dir)
        # 3) Bilan énergétique (placeholders)
        bilan.server(input, output, session, app_dir)
        # 4) Bilan échanges
        echanges.server(input, output, session, app_dir)
        # 5) Simulateurs (ton server complet)
        simulateurs.server(input, output, session, app_dir)
        # 6) Gestionnaire de DC au sein des FLAPD
        gestionnaire_DC.module_gestionnaire_dc(input, output, session)

    return server
