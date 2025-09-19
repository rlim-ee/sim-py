# ui.py — Accueil + DC Europe + Énergie France (carte simple + camembert + évolution + bivariée + radar)
from pathlib import Path
from shiny import ui
import shinywidgets as sw

head = ui.tags.head(
    ui.tags.link(rel="preconnect", href="https://fonts.googleapis.com"),
    ui.tags.link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
    ui.tags.link(
        rel="stylesheet",
        href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800;900&display=swap",
    ),
    ui.tags.link(
        rel="stylesheet",
        href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
    ),
    ui.include_css(str(Path(__file__).parent / "www" / "custom.css")),
    ui.tags.script(
        """
        (function(){
          const root = document.documentElement;
          function apply(theme){
            root.classList.remove('theme-light','theme-dark');
            root.classList.add(theme === 'dark' ? 'theme-dark' : 'theme-light');
          }
          document.addEventListener('change', function(e){
            if (e.target && e.target.name === 'theme_mode') apply(e.target.value);
          });
          document.addEventListener('DOMContentLoaded', function(){
            const r = document.querySelector("input[name='theme_mode']:checked");
            if (r) apply(r.value);
          });
        })();
        """
    ),
)

# Sélecteur d’onglet (accueil/Europe/France)
page_selector = ui.div(
    {"class": "card"},
    ui.h3("Navigation", class_="section-title"),
    ui.input_radio_buttons(
        "page",
        None,
        {"home": "Accueil", "eu": "DC — Europe", "fr": "Énergie — France"},
        selected="home",
        inline=True,
    ),
)

# Accueil
home_panel = ui.panel_conditional(
    "input.page === 'home'",
    ui.div(
        {"class": "container-app"},
        ui.div(
            {"class": "card"},
            ui.h2("Matérialités du numérique — Tableau de bord", class_="mb-2"),
            ui.p(
                "Choisissez un onglet ci-dessus : (1) DC en Europe ; (2) Bilan énergétique France.",
                class_="section-text",
            ),
        ),
        ui.row(
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Répartition des DC (Europe)"),
                    ui.p("Choroplèthe DC/million + bulles (nb total de DC)."),
                    ui.tags.button(
                        "Ouvrir l’onglet Europe",
                        class_="btn btn-primary mt-2",
                        onclick="Shiny.setInputValue('page','eu',{priority:'event'})",
                    ),
                ),
            ),
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Bilan énergétique (France)"),
                    ui.p("Carte régionale, camembert par filière, évolution annuelle, typologie bivariée, radar."),
                    ui.tags.button(
                        "Ouvrir l’onglet France",
                        class_="btn btn-success mt-2",
                        onclick="Shiny.setInputValue('page','fr',{priority:'event'})",
                    ),
                ),
            ),
        ),
    ),
)

# DC — Europe (identique visuellement ; Choropleth sous le capot)
europe_panel = ui.panel_conditional(
    "input.page === 'eu'",
    ui.div(
        {"class": "container-app"},
        ui.row(
            ui.column(8, ui.h2("Répartition des data centers en Europe", class_="mb-2")),
            ui.column(
                4,
                ui.div(
                    {"class": "theme-switch"},
                    ui.input_radio_buttons(
                        "theme_mode",
                        "Thème",
                        {"light": "Clair", "dark": "Sombre"},
                        selected="light",
                        inline=True,
                    ),
                ),
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Contexte", class_="section-title"),
            ui.p(
                "Carte choroplèthe (DC / million d'habitants) + bulles proportionnelles au nombre total de DC. "
                "À droite : part du nombre total de DC par pays.",
                class_="section-text",
            ),
        ),
        ui.row(
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Répartition des DC en Europe", class_="section-title"),
                    sw.output_widget("eu_map"),
                    ui.p(
                        "Couleur = DC par million d'habitants ; bulles = intensité absolue (nombre total de DC).",
                        class_="section-text",
                    ),
                ),
            ),
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Part du nombre des DC en Europe", class_="section-title"),
                    sw.output_widget("barPlot_eu"),
                    ui.p("Répartition proportionnelle par pays (ordre croissant).", class_="section-text"),
                ),
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Évolution de la demande énergétique", class_="section-title"),
            sw.output_widget("dc_demand_plot"),
        ),
    ),
)

# Énergie — France
france_panel = ui.panel_conditional(
    "input.page === 'fr'",
    ui.div(
        {"class": "container-app"},
        ui.div({"class": "card"}, ui.h2("Analyse régionale de la production et consommation d’énergie")),
        ui.row(
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Consommation vs Production (carte)"),
                    ui.input_select(
                        "fr_var",
                        "Choisir l’indicateur à afficher :",
                        {"prod": "Production totale (TWh)", "conso": "Consommation totale brute (TWh)"},
                        selected="prod",
                    ),
                    sw.output_widget("map_fr", height="500px"),
                ),
            ),
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Production d’énergie par filière (camembert)"),
                    ui.input_select("region_fr", "Choisir une région :", choices=["France"], selected="France"),
                    sw.output_widget("pie_fr", height="500px"),
                ),
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Évolution de la production par filière + ligne conso"),
            sw.output_widget("area_fr", height="360px"),
        ),
        ui.row(
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Typologie bivariée Production (↑) / Consommation (→)"),
                    sw.output_widget("map_fr_bivar", height="430px"),
                ),
            ),
            ui.column(
                6,
                ui.div(
                    {"class": "card"},
                    ui.h3("Radar Production vs Consommation"),
                    sw.output_widget("radar_fr", height="430px"),
                ),
            ),
        ),
    ),
)

app_ui = ui.page_fluid(head, page_selector, home_panel, europe_panel, france_panel)
