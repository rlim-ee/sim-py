# server/energie/__init__.py
from pathlib import Path


def server(input, output, session, app_dir: Path):
    """
    Serveur principal du module Énergie.
    Les sous-modules sont importés localement
    pour éviter toute circular import.
    """

    from . import repartition
    from . import flapd
    from . import bilan
    from . import echanges
    from . import simulateurs

    repartition.server(input, output, session, app_dir)
    flapd.server(input, output, session, app_dir)
    bilan.server(input, output, session, app_dir)
    echanges.server(input, output, session, app_dir)
    simulateurs.server(input, output, session, app_dir)
