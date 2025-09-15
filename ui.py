# ui.py — UI avec sélecteur de thème manuel (Clair/Sombre)
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
    # CSS
    ui.include_css(str(Path(__file__).parent / "www" / "custom.css")),
    # JS: handler pour changer la classe du <html>
    ui.tags.script("""
      (function(){
        const root = document.documentElement;

        function apply(theme){
          root.classList.remove('theme-light','theme-dark');
          root.classList.add(theme === 'light' ? 'theme-light' : 'theme-dark');
        }

        // Thème initial aligné au radio (défaut = 'dark' côté UI)
        document.addEventListener('DOMContentLoaded', function(){
          const checked = document.querySelector("input[name='theme_mode']:checked");
          apply(checked ? checked.value : 'dark');
        });

        // Écoute côté user (immédiat, sans round-trip)
        document.addEventListener('change', function(e){
          if (e.target && e.target.name === 'theme_mode') apply(e.target.value);
        });

        // Écoute aussi les messages du serveur (optionnel)
        if (window.Shiny && Shiny.addCustomMessageHandler){
          Shiny.addCustomMessageHandler('set-theme', function(theme){ apply(theme); });
        }
      })();
    """),
)

app_ui = ui.page_fluid(
    head,
    ui.div({"class": "container-app"},
        # Ligne titre + switch de thème
        ui.row(
            ui.column(8, ui.h2("Matérialités du numérique — Simulations", class_="mb-2")),
            ui.column(4,
                ui.div({"class": "theme-switch"},
                    ui.input_radio_buttons(
                        "theme_mode",
                        "Thème",
                        {"light": "Clair", "dark": "Sombre"},
                        selected="dark",
                        inline=True,
                    ),
                ),
            ),
        ),

        ui.navset_tab(
            # ================ SIMULATION 1 ================
            ui.nav_panel(
                "Simulation 1",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("Paramètres"),
                        ui.input_slider("nb_dc", "Nombre de Data Centers", min=1, max=35, value=1, step=1),
                        ui.input_slider("facteur_charge", "Facteur de charge (%)", min=0, max=100, value=100, step=1),
                        ui.div({"class": "chip mt-2"},
                               ui.tags.i({"class": "fa-solid fa-gear"}),
                               ui.output_text("facteur_charge_affiche")),
                        class_="sidebar",
                    ),
                    ui.div({"class": "card"},
                           ui.h3("Tendances 2000–2050 (références)", class_="section-title"),
                           sw.output_widget("energiePlot"),
                    ),
                    ui.div({"class": "card"},
                           ui.h3("Production vs Consommation (2025–2035)", class_="section-title"),
                           sw.output_widget("energy_plot"),
                           ui.div({"class": "mt-2"},
                                  ui.row(
                                      ui.column(12, ui.div(ui.strong("Conso actuelle + conso DC en 2035 : "), ui.output_text("info_conso_totale"))),
                                  ),
                           ),
                    ),
                    ui.div({"class": "card"},
                           ui.h3("Équivalents de production pour 2035", class_="section-title"),
                           ui.row(
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Réacteurs nucléaires"),
                                                   ui.div({"class": "value"}, ui.output_text("nuke_value")))),
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Grands barrages"),
                                                   ui.div({"class": "value"}, ui.output_text("hydro_value")))),
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Centrales à charbon"),
                                                   ui.div({"class": "value"}, ui.output_text("coal_value")))),
                           ),
                           ui.row(
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Éoliennes terrestres"),
                                                   ui.div({"class": "value"}, ui.output_text("wind_value")),
                                                   ui.tags.small(ui.output_text("wind_surface")))),
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Photovoltaïque"),
                                                   ui.div({"class": "value"}, ui.output_text("solar_value")),
                                                   ui.tags.small(ui.output_text("solar_surface")))),
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Biomasse"),
                                                   ui.div({"class": "value"}, ui.output_text("bio_value")))),
                           ),
                           ui.div({"class": "mt-2"}, ui.output_ui("surface_info")),
                    ),
                    fillable=True,
                ),
            ),

            # ================ SIMULATION 2 ================
            ui.nav_panel(
                "Simulation 2",
                ui.layout_sidebar(
                    ui.sidebar(
                        ui.h4("Profils de consommation"),
                        ui.output_ui("checkbox_group_conso"),
                        ui.hr(),
                        ui.h4("Comparaison personnalisée"),
                        ui.input_text("nom_perso_1", "Entité 1", "Perso 1"),
                        ui.input_numeric("val_perso_1", "Valeur", 100.0),
                        ui.input_select("unit_perso_1", "Unité", ["kWh/an", "MWh/an", "GWh/an"], selected="MWh/an"),
                        ui.input_text("nom_perso_2", "Entité 2", "Perso 2"),
                        ui.input_numeric("val_perso_2", "Valeur", None),
                        ui.input_select("unit_perso_2", "Unité", ["kWh/an", "MWh/an", "GWh/an"], selected="MWh/an"),
                        class_="sidebar",
                    ),
                    ui.div({"class": "card"},
                           ui.h3("Habitants équivalents par palier (profils sélectionnés)", class_="section-title"),
                           sw.output_widget("barplot"),
                    ),
                    ui.div({"class": "card"},
                           ui.h3("Focus 1 GW — 2035", class_="section-title"),
                           ui.row(
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Qatar"),
                                                   ui.div({"class": "value"}, ui.output_text("qatar_1gw")),
                                                   ui.tags.small(ui.output_text("qatar_pop")),
                                                   ui.tags.small(ui.output_text("qatar_pct")))),
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("France"),
                                                   ui.div({"class": "value"}, ui.output_text("france_1gw")),
                                                   ui.tags.small(ui.output_text("france_pop")),
                                                   ui.tags.small(ui.output_text("france_pct")))),
                               ui.column(4, ui.div({"class": "metric"},
                                                   ui.h4("Mali"),
                                                   ui.div({"class": "value"}, ui.output_text("mali_1gw")),
                                                   ui.tags.small(ui.output_text("mali_pop")),
                                                   ui.tags.small(ui.output_text("mali_pct")))),
                           ),
                    ),
                    ui.div({"class": "card"},
                           ui.h3("Comparaison personnalisée", class_="section-title"),
                           sw.output_widget("barplot_personalisee"),
                    ),
                    fillable=True,
                ),
            ),
            id="tabs",
        ),
    ),
)
