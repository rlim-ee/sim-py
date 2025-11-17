# server/__init__.py 
from pathlib import Path
from . import repartition, bilan, simulateurs, FLAPD

def make_server(app_dir: Path):
    def server(input, output, session):
        repartition.server(input, output, session, app_dir),
        bilan.server(input, output, session, app_dir),
        simulateurs.server(input, output, session),
        FLAPD.carte_flapd_server(input, output, session)
    return server

