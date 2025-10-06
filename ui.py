# ui.py — Dashboard Shiny (Cartes + Graphiques + Simulateurs)
from shiny import ui
import shinywidgets as sw
import base64, pathlib, mimetypes

# ====== LOGO helpers (light/dark, base64 + fallback statique) ======
_EXTS = ("png", "svg", "jpg", "jpeg", "webp")

def _data_uri_for(path: pathlib.Path) -> str | None:
    try:
        mime, _ = mimetypes.guess_type(path.name)
        if mime is None:
            mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{data}"
    except Exception:
        return None

def _find_logo(basenames: list[str]) -> str | None:
    """Renvoie une data-URI si possible, sinon le chemin (ex: 'images/verit_logo.png')."""
    root = pathlib.Path(__file__).parent / "www"
    candidates = []
    for base in basenames:
        for ext in _EXTS:
            candidates += [root / "images" / f"{base}.{ext}", root / f"{base}.{ext}"]
    for p in candidates:
        if p.exists():
            uri = _data_uri_for(p)
            if uri:
                return uri
    for p in candidates:
        if p.exists():
            try:
                return p.relative_to(root).as_posix()
            except Exception:
                return p.name
    return None

def _logo_srcs() -> tuple[str, str | None, str]:
    light = _find_logo(["verit_logo", "logo"])
    dark  = _find_logo(["verit_logo_dark", "logo_dark"])
    if light is None and dark is not None:
        light, dark = dark, None
    if light is None:
        light = "images/verit_logo.png"
    logo_class = "logo" + ("" if dark else " no-dark")
    return light, dark, logo_class

LOGO_LIGHT, LOGO_DARK, LOGO_CLASS = _logo_srcs()
# Logos partenaires (clair/sombre)
PARTNERS_LIGHT = _find_logo(["logos"])
PARTNERS_DARK  = _find_logo(["logos_dark"])

# ---------- petit helper pour un encadré déroulant ----------
# helper encadré déroulant
def dropcard(title: str, *children, open: bool = False):
    attrs = {"class": "dropcard"}
    if open:
        attrs["open"] = "open"  # <details open>
    return ui.tags.details(
        ui.tags.summary(title),
        ui.div(*children, class_="dropbody"),   # <- wrapper avec padding
        **attrs,
    )



# ---------- Blocs UI réutilisables ----------
def bloc_repartition():
    """Navset Répartition : Europe (map+barres+KPI) / FLAP-D (placeholder)"""

    # Contenu Europe
    europe_panel = ui.div(
        # Résumé 
        dropcard("Résumé — Répartition", ui.p("À compléter…")),
        ui.div(
            ui.div(
                ui.div({"class": "panel"},
                       ui.div({"class": "panel-head"},
                              ui.tags.i({"class":"fa-solid fa-map-location-dot"}), ui.h4("Répartition des data centers en Europe", class_="panel-title")),
                       ui.div(ui.div(ui.output_ui("repartition_map"), class_="map-wrap"), class_="panel-body")),
                class_="col"),
            ui.div(
                ui.div({"class": "panel"},
                       ui.div({"class": "panel-head"},
                              ui.tags.i({"class":"fa-solid fa-chart-bar"}), ui.h4("Part du nombre des DC en Europe", class_="panel-title")),
                       ui.div(sw.output_widget("dc_share_plot"), class_="panel-body"),
                       ui.div("Répartition proportionnelle par pays, illustrant la dominance de certains marchés.", class_="panel-foot")),
                class_="col"),
            class_="row gap-4 row-eq",
        ),
        ui.div(
            ui.div(
                ui.div({"class":"kpi-card accent-bolt"},
                       ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-bolt"})),
                       ui.div({"class":"kpi-title"}, "Data centers recensés"),
                       ui.div({"class":"kpi-value"}, ui.output_text("kpi_total_dc")),
                       ui.p("Nombre total de data centres recensés", class_="mb-0")),
                class_="col"),
            ui.div(
                ui.div({"class":"kpi-card accent-rank"},
                       ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-ranking-star"})),
                       ui.div({"class":"kpi-title"}, "Pays leader"),
                       ui.div({"class":"kpi-value"}, ui.output_text("kpi_leader_value")),
                       ui.p("Part de l'Allemagne")),
                class_="col"),
            ui.div(
                ui.div({"class":"kpi-card accent-geo"},
                       ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-globe"})),
                       ui.div({"class":"kpi-title"}, "Concentration géographique"),
                       ui.div({"class":"kpi-value"}, ui.output_text("kpi_top10")),
                       ui.p("Part des 10 premiers pays", class_="mb-0")),
                class_="col"),
            class_="row gap-4 mt-3",
        ),
    )

    # FLAP-D
    flapd_panel = ui.div(
        dropcard("Résumé — FLAP-D", ui.p("À compléter…")),
        ui.h4("FLAP-D"),
        ui.p("Espace réservé pour les hubs Francfort, Londres, Amsterdam, Paris, Dublin (à venir)."),
        class_="pt-2"
    )

    return ui.card(
        ui.div({"class": "card-title"},
               ui.tags.i({"class": "fa-solid fa-chart-area me-2"}),
               "Répartition des DC"),
        ui.navset_tab(
            ui.nav_panel("Europe", europe_panel),
            ui.nav_panel("FLAP-D", flapd_panel),
            id="tabs_repartition",
        ),
        full_screen=True,
        class_="thematique-card",
    )

def bloc_bilan():
    """Bilan énergétique — France (carte + camembert) / AURA (placeholder)"""

    # France : Carte + Pie
    france= ui.div(
        dropcard("Résumé — Bilan énergétique", ui.p("À compléter…")),
        ui.div(
            # Colonne GAUCHE : carte FR
            ui.div(
                ui.div({"class": "panel"},
                       ui.div(
                           {"class": "panel-head"},
                           ui.tags.i({"class": "fa-solid fa-layer-group"}),
                           ui.div(ui.output_text("map_title"), class_="panel-title"),
                           ),
                       ui.div(
                           ui.output_ui("fr_map"),
                           class_="panel-body"),
                       ),
                class_="col",
            ),
            # Colonne DROITE : camembert
            ui.div(
                ui.div({"class": "panel"},
                       ui.div(
                           {"class": "panel-head"},
                           ui.tags.i({"class": "fa-solid fa-chart-area"}),
                           ui.div(ui.output_text("pie_title"), class_="panel-title"),
                           ),
                       ui.div(
                           ui.div({"class":"mb-2"}, ui.output_ui("region_selector")),
                           sw.output_widget("prod_pie"),
                           class_="panel-body"),
                       ),
                class_="col",
            ),
            class_="row gap-4 row-eq",
        ),
        ui.tags.hr(class_="section-sep"),
        ui.div(
            ui.div(
                {"class": "panel panel-compact"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": "fa-solid fa-chart-area"}),
                    ui.div(ui.output_text("area_title"), class_="panel-title"),
                    ),
                ui.div(
                    ui.div({"class":"mb-2"},
                           ui.input_slider("year", "Année :", min=2014, max=2024, value=2024, step=1, width="100%")),
                    ui.div(sw.output_widget("area_chart"), style="width:100%"), class_="panel-body", style="width:100%"),
            ),
            class_="col-12",
        ),
    )

    # AURA
    aura   = ui.div(
        dropcard("Résumé — AURA", ui.p("À compléter…")),
        ui.markdown("*(à venir — indicateurs Auvergne-Rhône-Alpes : zoom régional, comparaisons, parts)*")
    )

    return ui.card(
        ui.div({"class":"card-title"}, ui.tags.i({"class":"fa-solid fa-bolt me-2"}), "Bilan énergétique"),
        ui.navset_tab(
            ui.nav_panel("France", france),
            ui.nav_panel("AURA", aura),
            id="tabs_bilan",
        ),
        full_screen=True,
        class_="thematique-card",
    )

def bloc_simulateurs():
    """2 onglets : Analyse prédictive / Analyse comparative (+ KPI neutres)"""

    # --- Analyse prédictive ---
    predictive_panel = ui.layout_sidebar(
        ui.sidebar(
            ui.h4("Paramètres"),
            ui.input_slider("nb_dc", "Nombre de Data Centers", min=1, max=35, value=1, step=1),
            ui.input_slider("facteur_charge", "Facteur de charge (%)", min=0, max=100, value=100, step=1),
            ui.div({"class": "chip mt-2"},
                   ui.tags.i({"class": "fa-solid fa-gear"}),
                   ui.output_text("facteur_charge_affiche")),
            class_="sidebar",
        ),

        # --- Résumé détaillé (ton texte) ---
        dropcard(
            "Résumé — Analyse prédictive",
            ui.div(
                ui.p("Cette simulation a pour objectif de comparer la consommation électrique projetée d'un ou plusieurs data centers (DC) avec la production totale d'énergie en France selon le rapport de RTE, sur la période 2025–2035."),
                ui.p("Les projections de consommation sont établies à partir des estimations de puissance du data center actuellement en construction à Éybens."),

                ui.tags.hr(),

                ui.p(ui.strong("📈 Hypothèses d'évolution :"),
                    " Les prévisions suivent les étapes de développement du projet Data One :"),
                ui.tags.ul(
                    ui.tags.li("2025 : 15 MW"),
                    ui.tags.li("2026 : 200 MW"),
                    ui.tags.li("2028 : 400 MW"),
                    ui.tags.li("2035 : 1 000 MW"),
                ),

                ui.p("🏗️ La simulation permet d'extrapoler jusqu'à 35 data centers, en cohérence avec les ambitions exprimées par les pouvoirs publics en matière d'infrastructures numériques, notamment dans le cadre du développement de l'intelligence artificielle."),

                ui.tags.hr(),

                ui.p(ui.strong("📊 Représentation graphique :")),
                ui.tags.ul(
                    ui.tags.li("Les points rouges indiquent la consommation cumulée des data centers ajoutée à la consommation énergétique 2024 (Consommation simulée)."),
                    ui.tags.li("La courbe verte représente la trajectoire de référence de la production énergétique nationale."),
                    ui.tags.li("La courbe bleue représente la trajectoire de référence de la consommation énergétique nationale."),
                    ui.tags.li("Les pointillés verts/bleus indiquent les variations min/max des différents scénarios RTE."),
                ),

                ui.tags.hr(),

                ui.p(ui.strong("⚡ Équivalent en unités de production :"),
                    " La simulation permet de comparer la consommation projetée des data centers en 2035 avec la production nécessaire par filière :"),
                ui.tags.ul(
                    ui.tags.li("Réacteurs nucléaires"),
                    ui.tags.li("Grands barrages hydrauliques"),
                    ui.tags.li("Centrales à charbon"),
                    ui.tags.li("Éoliennes"),
                    ui.tags.li("Panneaux solaires"),
                    ui.tags.li("Centrales à biomasse"),
                ),

                ui.tags.hr(),

                ui.p(ui.strong("💡 Conversion des unités :"),
                    " Pour comparer les consommations projetées, il est nécessaire de convertir les unités de GW en TWh/an selon la formule :"),
                ui.p(ui.em("Énergie annuelle (GWh/an) = Puissance (GW) × 24 heures × 365 jours")),
                ui.p("Exemple pour un data center d'une puissance d'1 GW et un facteur de charge de 60 % : 1 × 24 × 365 × 0,6 = 5 256 GWh/an = 5,26 TWh/an"),

                ui.tags.hr(),

                ui.p(ui.strong("🎯 Objectif :"),
                    " Cette simulation vise à éclairer les enjeux d'articulation entre les besoins énergétiques croissants des infrastructures numériques et les capacités de production énergétique du pays dans une perspective de planification énergétique à long terme.")
            ),
        ),

        ui.div({"class": "card"},
               ui.h3("Tendances 2000–2050 (références)", class_="section-title"),
               sw.output_widget("energiePlot")),
        ui.div({"class": "card"},
               ui.h3("Production vs Consommation (2025–2035)", class_="section-title"),
               sw.output_widget("energy_plot"),
               ui.div({"class": "mt-2"},
                      ui.row(
                          ui.column(12, ui.div(ui.strong("Conso actuelle + conso DC en 2035 : "),
                                               ui.output_text("info_conso_totale"))),
                      ))),

        ui.div({"class":"card"},
               ui.h3("Équivalents de production pour 2035", class_="section-title"),
               ui.div({"class": "kpi-eq"},
                      ui.div(ui.div({"class":"kpi-card neutral"},
                                    ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-atom"})),
                                    ui.div({"class":"kpi-title"}, "Réacteurs nucléaires"),
                                    ui.div({"class":"kpi-value"}, ui.output_text("nuke_value")),
                                    ui.tags.small(ui.output_text("nuke_pct_total"), class_="kpi-sub"))),
                      ui.div(ui.div({"class":"kpi-card neutral"},
                                    ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-water"})),
                                    ui.div({"class":"kpi-title"}, "Grands barrages"),
                                    ui.div({"class":"kpi-value"}, ui.output_text("hydro_value")),
                                    ui.tags.small("", class_="kpi-sub"))),
                      ui.div(ui.div({"class":"kpi-card neutral"},
                                    ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-industry"})),
                                    ui.div({"class":"kpi-title"}, "Centrales à charbon"),
                                    ui.div({"class":"kpi-value"}, ui.output_text("coal_value")),
                                    ui.tags.small("", class_="kpi-sub"))),
                      ui.div(ui.div({"class":"kpi-card neutral"},
                                    ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-wind"})),
                                    ui.div({"class":"kpi-title"}, "Éoliennes terrestres"),
                                    ui.div({"class":"kpi-value"}, ui.output_text("wind_value")),
                                    ui.tags.small(ui.output_text("wind_surface"), class_="kpi-sub"))),
                      ui.div(ui.div({"class":"kpi-card neutral"},
                                    ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-solar-panel"})),
                                    ui.div({"class":"kpi-title"}, "Photovoltaïque"),
                                    ui.div({"class":"kpi-value"}, ui.output_text("solar_value")),
                                    ui.tags.small(ui.output_text("solar_surface"), class_="kpi-sub"))),
                      ui.div(ui.div({"class":"kpi-card neutral"},
                                    ui.div({"class":"kpi-icon"}, ui.tags.i({"class":"fa-solid fa-leaf"})),
                                    ui.div({"class":"kpi-title"}, "Centrales à biomasse"),
                                    ui.div({"class":"kpi-value"}, ui.output_text("bio_value")),
                                    ui.tags.small("", class_="kpi-sub"))),
               ),
        ),
        ui.output_ui("surface_info"),
        fillable=True,
    )

    # --- Analyse comparative ---
    comparative_panel = ui.layout_sidebar(
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

        # --- Résumé détaillé (ton 2e texte) ---
        dropcard(
            "Résumé — Analyse comparative",
            ui.div(
                ui.p("Ce graphique permet de représenter et de comparer le nombre d'habitants équivalents pour chaque palier de consommation du data center d'Eybens entre 2025 et 2035. Et ce, en prenant des exemples de profils de consommation du secteur résidentiel uniquement et ceux par personne à travers le monde et en France."),
                ui.p("Les barres représentent le nombre d'habitants équivalents selon la consommation moyenne."),
                ui.p("Cochez les profils pour adapter la simulation."),

                ui.tags.hr(),

                ui.p(ui.strong("🔍 Estimation initiale :"),
                     " La consommation du DC est basée sur le data center actuellement en construction à Éybens."),
                ui.p(ui.strong("📈 Évolution prévue :"),
                     " Les projections suivent les plans de développement de Data One :"),
                ui.tags.ul(
                    ui.tags.li("2025 : 15 MW"),
                    ui.tags.li("2026 : 200 MW"),
                    ui.tags.li("2028 : 400 MW"),
                    ui.tags.li("2035 : 1 000 MW"),
                ),

                ui.tags.hr(),

                ui.p(ui.strong("💡 Conversion des unités :"),
                     " Pour comparer les consommations projetées de Data One aux consommations annuelles moyennes d'individus, il est nécessaire de convertir l'unité des projections de Data One (exprimées en GW) afin d'obtenir des valeurs en GWh/an. Pour ce faire, on applique la formule suivante :"),
                ui.p(ui.em("Énergie annuelle (en GWh/an) = Puissance (GW) × nombre d'heures d'utilisation par jour × nombre de jours d'utilisation par an")),
                ui.p("Par exemple, calculons la conversion de la projection de 2035 pour 1 GW :"),
                ui.p(ui.em("Énergie annuelle (GWh) = 1 × 24 × 365 = 8 760 GWh/an")),
                ui.tags.ul(
                    ui.tags.li("Ou encore 8 760 000 000 kWh/an"),
                    ui.tags.li("Soit 8 760 000 MWh/an"),
                    ui.tags.li("Ou l'équivalent de 8,76 TWh/an"),
                ),
                ui.p("On peut donc diviser les différentes consommations annuelles projetées par la consommation moyenne souhaitée pour obtenir le nombre d'individus équivalents.")
            ),
        ),

        ui.div({"class": "card"},
               ui.h3("Habitants équivalents par palier (profils sélectionnés)", class_="section-title"),
               sw.output_widget("barplot"),
               ui.p(ui.strong("💡 Aide d'interprétation pour l'échelle mondiale :"),
                    " Pour un data center d'une puissance de 1 GW, cela correspond à la consommation",
                    " énergétique résidentielle annuelle de 3 275 991 personnes, basée sur la moyenne",
                    " mondiale de 2,674 MWh par personne et par an.")),
        ui.div({"class": "card"},
               ui.h3("💡 Focus sur 3 pays : équivalents en population pour un data center de 1 GW", class_="section-title"),
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
               )),
        ui.div({"class": "card"},
               ui.h3("Comparaison personnalisée", class_="section-title"),
               sw.output_widget("barplot_personalisee")),
        fillable=True,
    )

    return ui.card(
        ui.div({"class": "card-title"}, ui.strong("Simulateurs")),
        ui.navset_tab(
            ui.nav_panel("Analyse prédictive", predictive_panel),
            ui.nav_panel("Analyse comparative", comparative_panel),
            id="sim_tabs",
        ),
        full_screen=True,
        class_="thematique-card",
    )
    
def app_footer():
    return ui.tags.footer(
        ui.div(
            ui.div(
                ui.tags.img(src=PARTNERS_LIGHT or "images/logos.png", alt="Partenaires", class_="partners partners--light", loading="lazy"),
                ui.tags.img(src=PARTNERS_DARK or "images/logos_dark.png", alt="Partenaires (mode sombre)", class_="partners partners--dark", loading="lazy"),
                class_="footer-logos",
            ),
            ui.div(
                ui.span("Conception & développement : "),
                ui.strong("Zoé CARGNELLI"),
                ui.span(" & "),
                ui.strong("Robert LIM"),
                ui.br(),
                ui.span("© 2025 — Matérialités du numérique • Projet VerIT"),
                class_="footer-credits",
                ),
            class_="footer-inner",
        ),
        ui.p("Opération soutenue par l’État dans le cadre de l’AMI « Compétences et Métiers d’Avenir »  du programme France 2030, opéré par la Caisse des Dépôts (La Banque des Territoires).", class_="footer-text"),
        class_="app-footer",
    )

# ---------- UI principale ----------
app_ui = ui.page_fluid(
    ui.head_content(
        ui.tags.meta(charset="utf-8"),
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),
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
        ui.include_css("www/styles.css"),
        ui.tags.script(f"""
document.addEventListener('DOMContentLoaded', () => {{
  const sw = document.getElementById('darkmode');
  const logo = document.getElementById('logo');
  const lightSrc = {LOGO_LIGHT!r};
  const darkSrc  = {LOGO_DARK!r};

  const apply = () => {{
    const isDark = !!(sw && sw.checked);
    document.documentElement.classList.toggle('dark', isDark);
    if (logo) {{
      if (darkSrc && darkSrc !== 'None') {{
        logo.src = isDark ? darkSrc : lightSrc;
      }} else {{
        logo.src = lightSrc;
      }}
    }}
  }};
  apply();
  if (sw) sw.addEventListener('change', apply);
}});
        """),
        ui.tags.title("Matérialités du numérique"),
        ui.tags.link(rel="icon", href=LOGO_LIGHT, type="image/png"),
    ),

    ui.div(
        ui.div(
            ui.tags.img(id="logo", src=LOGO_LIGHT, alt="VERIT", class_=LOGO_CLASS),
            ui.div("Matérialités du numérique • Projet VerIT", class_="brand"),
            class_="brandbox",
        ),
        ui.input_switch("darkmode", "Mode sombre", value=True),
        class_="topbar",
    ),
    
    ui.tags.script("""
(function () {
  function resizeAll() {
    const plots = document.querySelectorAll('.js-plotly-plot');
    plots.forEach(p => { try { Plotly.Plots.resize(p); } catch(e){} });
  }

  // À chaque valeur Shiny livrée, redimensionner juste après le paint
  document.addEventListener('shiny:value', () => {
    requestAnimationFrame(resizeAll);
  });

  // Quand on change d’onglet (Bootstrap navset), redimensionner
  document.addEventListener('shown.bs.tab', () => {
    setTimeout(resizeAll, 60);
  });

  // Et sur resize fenêtre
  window.addEventListener('resize', () => {
    requestAnimationFrame(resizeAll);
  });
})();
"""),


    # Présentation générale en haut de page (plein large)
    dropcard(
        "Présentation générale",
        ui.p("Présentation globale du dashboard, contexte et mode d’emploi. (À compléter…)"),
    ),

    bloc_repartition(),
    bloc_bilan(),
    bloc_simulateurs(),
    app_footer(),
)
