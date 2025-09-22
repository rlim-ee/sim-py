# server/bilan.py — placeholders vides (à remplir plus tard)
from shiny import render, ui
from pathlib import Path

def server(input, output, session, app_dir: Path):
    @output
    @render.ui
    def bilan_panel1():
        return ui.markdown("*(Bientôt : indicateurs et graphiques de bilan)*")

    @output
    @render.ui
    def bilan_panel2():
        return ui.markdown("*(Bientôt : explorations, filtres, téléchargements)*")
