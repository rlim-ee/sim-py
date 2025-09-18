# ui.py — DC en Europe (style “simulations”) + switch Clair/Sombre
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
            root.classList.add(theme === 'light' ? 'theme-light' : 'theme-dark');
          }
          document.addEventListener('DOMContentLoaded', function(){
            const checked = document.querySelector("input[name='theme_mode']:checked");
            apply(checked ? checked.value : 'light');
          });
          document.addEventListener('change', function(e){
            if (e.target && e.target.name === 'theme_mode') apply(e.target.value);
          });
          if (window.Shiny && Shiny.addCustomMessageHandler){
            Shiny.addCustomMessageHandler('set-theme', function(theme){ apply(theme); });
          }
        })();
        """
    ),
)

app_ui = ui.page_fluid(
    head,
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
                    ui.p(
                        "Répartition proportionnelle par pays (ordre croissant).",
                        class_="section-text",
                    ),
                ),
            ),
        ),

        ui.div(
            {"class": "card"},
            ui.h3("Chiffres clés", class_="section-title"),
            ui.row(
                ui.column(
                    4,
                    ui.div(
                        {"class": "metric accent-yellow"},
                        ui.h4("Demande énergétique 2035"),
                        ui.div({"class": "value"}, "236 TWh"),
                        ui.tags.small("Projection : ~5,7 % de la demande électrique européenne."),
                    ),
                ),
                ui.column(
                    4,
                    ui.div(
                        {"class": "metric accent-orange"},
                        ui.h4("Croissance 2024 → 2035"),
                        ui.div({"class": "value"}, "+146 %"),
                        ui.tags.small("Croissance projetée de la demande des DC."),
                    ),
                ),
                ui.column(
                    4,
                    ui.div(
                        {"class": "metric accent-cyan"},
                        ui.h4("Concentration géographique"),
                        ui.div({"class": "value"}, "79 %"),
                        ui.tags.small("10 pays concentrent la majorité de la demande."),
                    ),
                ),
            ),
        ),

        ui.div(
            {"class": "card"},
            ui.h3("Évolution de la demande énergétique", class_="section-title"),
            sw.output_widget("dc_demand_plot"),
            ui.p(
                "Selon ICIS, la demande des DC en Europe passerait de 96 TWh en 2024 à 236 TWh en 2035.",
                class_="section-text",
            ),
        ),
    ),
)
