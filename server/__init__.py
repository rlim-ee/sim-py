# server/__init__.py — orchestration des 3 serveurs
from pathlib import Path
from . import repartition, bilan, simulateurs

def make_server(app_dir: Path):
    def server(input, output, session):
        # 1) Répartition des data centers (carte Europe)
        repartition.server(input, output, session, app_dir)
        # 2) Bilan énergétique (placeholders)
        bilan.server(input, output, session, app_dir)
        # 3) Simulateurs (ton server complet)
        simulateurs.server(input, output, session)
    return server
