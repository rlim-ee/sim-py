# ui.py — UI complète avec sélecteur de thème (Clair/Sombre) et 3 onglets
from pathlib import Path
from shiny import ui
import shinywidgets as sw

# ---- <head> : fonts + FA + CSS + JS de switch de thème
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
            apply(checked ? checked.value : 'dark');
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
    ui.div({"class": "container-app"},

        # ===== Titre + switch de thème
        ui.row(
            ui.column(8, ui.h2("Matérialités du numérique — Simulations", class_="mb-2")),
            ui.column(
                4,
                ui.div(
                    {"class": "theme-switch"},
                    ui.input_radio_buttons(
                        "theme_mode",
                        "Thème",
                        {"light": "Clair", "dark": "Sombre"},
                        selected="light",   # défaut : clair
                        inline=True,
                    ),
                ),
            ),
        ),

        ui.navset_tab(

            # ====================== Onglet 1 : Simulation 1 ======================
            ui.nav_panel(
                "Simulation 1",
                ui.layout_sidebar(
                    # ---- Sidebar
                    ui.sidebar(
                        ui.h4("Paramètres"),
                        ui.input_slider("nb_dc", "Nombre de Data Centers", min=1, max=35, value=1, step=1),
                        ui.input_slider("facteur_charge", "Facteur de charge (%)", min=0, max=100, value=100, step=1),
                        ui.div(
                            {"class": "chip mt-3"},
                            ui.tags.i({"class": "fa-solid fa-gear"}),
                            ui.div(ui.strong("Facteur de charge appliqué : "), ui.output_text("facteur_charge_affiche")),
                        ),
                        class_="sidebar",
                    ),

                    # ---- Contenu principal
                    # Tendances
                    ui.div(
                        {"class": "card"},
                        ui.h3("Tendances 2000–2050 (références)", class_="section-title"),
                        sw.output_widget("energiePlot"),
                    ),

                    # Production vs Consommation
                    ui.div(
                        {"class": "card"},
                        ui.h3("Production vs Consommation (2025–2035)", class_="section-title"),
                        sw.output_widget("energy_plot"),
                        ui.row(
                            ui.column(
                                6,
                                ui.p(
                                    ui.strong("Consommation DC en 2025 : "),
                                    ui.output_text("info_conso_dc")
                                ),
                            ),
                            ui.column(
                                6,
                                ui.p(
                                    ui.strong("Conso actuelle + DC en 2035 : "),
                                    ui.output_text("info_conso_totale")
                                ),
                            ),
                        ),
                    ),

                    # Équivalents / métriques
                    ui.div(
                        {"class": "card"},
                        ui.h3("Équivalents de production pour 2035", class_="section-title"),
                        ui.row(
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-yellow"},
                                    ui.h4("Réacteurs nucléaires"),
                                    ui.div({"class": "value"}, ui.output_text("nuke_value")),
                                    ui.tags.small(ui.output_text("nuke_pct_total")),
                                ),
                            ),
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-blue"},
                                    ui.h4("Grands barrages"),
                                    ui.div({"class": "value"}, ui.output_text("hydro_value")),
                                ),
                            ),
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-orange"},
                                    ui.h4("Centrales à charbon"),
                                    ui.div({"class": "value"}, ui.output_text("coal_value")),
                                ),
                            ),
                        ),
                        ui.row(
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-green"},
                                    ui.h4("Éoliennes terrestres"),
                                    ui.div({"class": "value"}, ui.output_text("wind_value")),
                                    ui.tags.small(ui.output_text("wind_surface")),
                                ),
                            ),
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-cyan"},
                                    ui.h4("Photovoltaïque"),
                                    ui.div({"class": "value"}, ui.output_text("solar_value")),
                                    ui.tags.small(ui.output_text("solar_surface")),
                                ),
                            ),
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-neutral"},
                                    ui.h4("Centrales à Biomasse"),
                                    ui.div({"class": "value"}, ui.output_text("bio_value")),
                                ),
                            ),
                        ),
                        ui.div({"class": "mt-2"}, ui.output_ui("surface_info")),
                    ),
                    fillable=True,
                ),
            ),

            # ====================== Onglet 2 : Simulation 2 ======================
            ui.nav_panel(
                "Simulation 2",
                ui.layout_sidebar(
                    # ---- Sidebar (profils + comparaison personnalisée)
                    ui.sidebar(
                        ui.h4("Profils de consommation"),
                        ui.output_ui("checkbox_group_conso"),
                        ui.hr(),
                        ui.h4("Comparaison personnalisée"),
                        ui.input_text("nom_perso_1", "Entité 1", "Foyer 1"),
                        ui.input_numeric("val_perso_1", "Valeur", 3.4),
                        ui.input_select("unit_perso_1", "Unité", ["kWh/an", "MWh/an", "GWh/an"], selected="MWh/an"),
                        ui.input_text("nom_perso_2", "Entité 2", "Foyer 2"),
                        ui.input_numeric("val_perso_2", "Valeur", 12.1),
                        ui.input_select("unit_perso_2", "Unité", ["kWh/an", "MWh/an", "GWh/an"], selected="MWh/an"),
                        class_="sidebar",
                    ),

                    # ---- Graphique pays
                    ui.div(
                        {"class": "card"},
                        ui.h3("Habitants équivalents par palier (profils sélectionnés)", class_="section-title"),
                        sw.output_widget("barplot"),
                        ui.p(
                            ui.strong("💡 Aide d'interprétation pour l'échelle mondiale :"),
                            " Pour un data center d'une puissance de 1 GW, cela correspond à la consommation énergétique résidentielle annuelle de 3 275 991 personnes, basée sur la moyenne mondiale de 2,674 MWh par personne et par an.",
                            class_="section-text",
                        ),
                    ),

                    # ---- Focus 1 GW (3 cartes)
                    ui.div(
                        {"class": "card"},
                        ui.h3("💡 Focus sur 3 pays : équivalents en population pour un data center de 1 GW", class_="section-title"),
                        ui.p("Ces encarts présentent le nombre d'habitants dont la consommation annuelle équivaut à celle d'un data center de 1 GW, pour trois pays représentatifs : un pays à très forte consommation (Qatar), un pays à très faible consommation (Mali), et la France comme cas d'étude central. Le pourcentage affiché indique la part de la population nationale que cela représenterait.",
                             class_="section-text"),
                        ui.row(
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-orange"},
                                    ui.h4("Qatar"),
                                    ui.div({"class": "value"}, ui.output_text("qatar_1gw")),
                                    ui.tags.small(ui.output_text("qatar_pop")),
                                    ui.tags.small(ui.output_text("qatar_pct")),
                                ),
                            ),
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-blue"},
                                    ui.h4("France"),
                                    ui.div({"class": "value"}, ui.output_text("france_1gw")),
                                    ui.tags.small(ui.output_text("france_pop")),
                                    ui.tags.small(ui.output_text("france_pct")),
                                ),
                            ),
                            ui.column(
                                4,
                                ui.div(
                                    {"class": "metric accent-green"},
                                    ui.h4("Mali"),
                                    ui.div({"class": "value"}, ui.output_text("mali_1gw")),
                                    ui.tags.small(ui.output_text("mali_pop")),
                                    ui.tags.small(ui.output_text("mali_pct")),
                                ),
                            ),
                        ),
                    ),

                    # ---- Comparaison personnalisée (barres)
                    ui.div(
                        {"class": "card"},
                        ui.h3("Comparaison personnalisée", class_="section-title"),
                        sw.output_widget("barplot_personalisee"),
                    ),
                    fillable=True,
                ),
            ),

            # ====================== Onglet 3 : DC en Europe ======================
            ui.nav_panel(
                "DC en Europe",
                ui.div({"class": "card"},
                       ui.h2("Répartition des data centers en Europe", class_="section-title"),
                       ui.p("Visualisation des hubs européens, parts relatives par pays et évolution de la demande énergétique des DC.",
                            class_="section-text"),
                ),
                ui.row(
                    ui.column(
                        6,
                        ui.div(
                            {"class": "card"},
                            ui.h3("Répartition des DC en Europe", class_="section-title"),
                            sw.output_widget("map1"),  # <-- correspond au server
                            ui.p("Distribution géographique des data centers. Couleur = DC par million d’habitants.",
                                 class_="section-text"),
                        ),
                    ),
                    ui.column(
                        6,
                        ui.div(
                            {"class": "card"},
                            ui.h3("Part du nombre des DC en Europe", class_="section-title"),
                            sw.output_widget("barPlot"),  # <-- correspond au server
                            ui.p("Répartition proportionnelle par pays (ordre croissant).",
                                 class_="section-text"),
                        ),
                    ),
                ),
                ui.div(
                    {"class": "card"},
                    ui.h3("Évolution de la demande énergétique", class_="section-title"),
                    sw.output_widget("dc_demand_plot"),
                    ui.p("Selon ICIS, la demande des DC en Europe passerait de 96 TWh en 2024 à 236 TWh en 2035.",
                         class_="section-text"),
                ),
            ),

            id="tabs",
        ),
    ),
)
