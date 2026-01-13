# ui.py — Dashboard Shiny
from shiny import ui
import shinywidgets as sw
import base64
import pathlib
import mimetypes

# ====== LOGO helpers ======
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

    # 1. on essaye en data URI
    for p in candidates:
        if p.exists():
            uri = _data_uri_for(p)
            if uri:
                return uri

    # 2. sinon, on renvoie le chemin
    for p in candidates:
        if p.exists():
            try:
                return p.relative_to(root).as_posix()
            except Exception:
                return p.name

    return None


def _logo_srcs() -> tuple[str, str | None, str]:
    light = _find_logo(["verit_logo", "logo"])
    dark = _find_logo(["verit_logo_dark", "logo_dark"])
    if light is None and dark is not None:
        light, dark = dark, None
    if light is None:
        light = "images/verit_logo.png"
    logo_class = "logo" + ("" if dark else " no-dark")
    return light, dark, logo_class


LOGO_LIGHT, LOGO_DARK, LOGO_CLASS = _logo_srcs()
PARTNERS_LIGHT = _find_logo(["logos"])
PARTNERS_DARK = _find_logo(["logos_dark"])


# ---------- helper encadré déroulant ----------
def dropcard(title: str, *children, open: bool = False):
    attrs = {"class": "dropcard"}
    if open:
        attrs["open"] = "open"
    return ui.tags.details(
        ui.tags.summary(title),
        ui.div(*children, class_="dropbody"),
        **attrs,
    )


def bloc_hq_flapd():

    def head_title_only(icon_class: str, title_ui):
        """panel-head simple (sans consigne)"""
        return ui.div(
            {"class": "panel-head"},
            ui.tags.i({"class": icon_class}),
            ui.div(title_ui, class_="panel-title"),
        )

    def help_accordion(title: str, content_ui):
        return ui.accordion(
            ui.accordion_panel(
                title,
                ui.div(
                    content_ui,
                    class_="text-muted",
                    style="font-size:13px;line-height:1.45;",
                ),
            )
        )

    # Instruction 
    instruction_map = ui.p(
        "Cliquez sur un ",
        ui.strong("hub"),
        " pour afficher la vue détaillée. ",
        "Re-cliquez sur le ",
        ui.strong("hub actif"),
        " pour revenir à la vue globale.",
        style="margin:0 0 10px 0;",
    )

    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": "fa-solid fa-globe me-2"}),
            "FLAP-D — Pays d’origine (HQ)",
        ),

        ui.div(
            {"class": "section-lead"},
            ui.h2("Europe"),
            ui.p(
                "Ce module explore l’origine géographique des entreprises opérant les data centers "
                "des cinq hubs FLAP-D : Francfort, Londres, Amsterdam, Paris et Dublin."
            ),
        ),

        # LIGNE 1 : CARTE + TREEMAP
        ui.div(
            ui.div(
                # CARTE 
                ui.div(
                    ui.div(
                        {"class": "panel"},

                        head_title_only(
                            "fa-solid fa-layer-group",
                            ui.output_text("titre_carte_hq"),
                        ),

                        ui.div(
                            instruction_map,

                            ui.div(
                                {
                                    "id": "map-responsive-wrapper",
                                    "style": (
                                        "width:100%;"
                                        "height:0;"
                                        "padding-bottom:65%;"
                                        "position:relative;"
                                        "overflow:hidden;"
                                        "border-radius:8px;"
                                    ),
                                },
                                ui.div(
                                    {
                                        "id": "map-inner",
                                        "style": (
                                            "position:absolute;"
                                            "top:0;left:0;"
                                            "width:100%;height:100%;"
                                        ),
                                    },
                                    ui.output_ui("map_hq_flapd"),
                                ),
                            ),

                            class_="panel-body",
                        ),

                        ui.div(
                            ui.div(ui.output_ui("commentaire_carte_hq"), style="color:#111;"),

                            ui.div(
                                {"class": "mt-2"},
                                help_accordion(
                                    "Comment lire cette carte ?",
                                    ui.div(
                                        ui.p(
                                            ui.strong("Coloration des pays : "),
                                            "représente la part (%) des entreprises du hub.",
                                            style="margin:0 0 6px 0;",
                                        ),
                                        ui.p(
                                            ui.strong("Flèches : "),
                                            "indiquent le sens des connexions (pays siège → hub).",
                                            style="margin:0 0 6px 0;",
                                        ),
                                        ui.p(
                                            ui.strong("Points gris : "),
                                            "localisent les pays sièges (HQ).",
                                            style="margin:0;",
                                        ),
                                    ),
                                ),
                            ),

                            class_="panel-foot",
                        ),
                    ),
                    class_="col",
                ),

                # TREEMAP
                ui.div(
                    ui.div(
                        {"class": "panel"},

                        head_title_only(
                            "fa-solid fa-chart-area",
                            ui.div("Répartition des entreprises gestionnaire"), #
                        ),

                        ui.div(
                            ui.output_ui("treemap_hq"),
                            class_="panel-body",
                        ),

                        ui.div(
                            ui.div(ui.output_ui("commentaire_treemap_hq"), style="color:#111;"),

                            ui.div(
                                {"class": "mt-2"},
                                help_accordion(
                                    "Lecture du treemap",
                                    ui.div(
                                        ui.p(
                                            ui.strong("Surface : "),
                                            "plus le rectangle est grand, plus la part du pays est élevée.",
                                            style="margin:0 0 6px 0;",
                                        ),
                                        ui.p(
                                            ui.strong("Navigation : "),
                                            "cliquer sur un rectangle permet de zoomer dans la contribution.",
                                            style="margin:0;",
                                        ),
                                    ),
                                ),
                            ),

                            class_="panel-foot",
                        ),
                    ),
                    class_="col",
                ),

                class_="row gap-4 row-eq",
            ),
            class_="mt-3",
        ),

        ui.tags.hr(class_="section-sep"),


        # LIGNE 2 : TOP 5

        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},

                    head_title_only(
                        "fa-solid fa-ranking-star",
                        ui.output_text("titre_top5"),
                    ),

                    ui.div(
                        ui.output_data_frame("top5_table"),
                        class_="panel-body",
                    ),

                    ui.div(
                        ui.div(ui.output_ui("commentaire_top5_hq"), style="color:#111;"),

                        ui.div(
                            {"class": "mt-2"},
                            help_accordion(
                                "Que dire de ce Top 5 ?",
                                ui.div(
                                    ui.p(
                                        ui.strong("Nombre de DC : "),
                                        "mesure la présence opérationnelle dans le hub.",
                                        style="margin:0 0 6px 0;",
                                    ),
                                    ui.p(
                                        ui.strong("Score share_info : "),
                                        "permet de comparer la transparence entre entreprises.",
                                        style="margin:0;",
                                    ),
                                ),
                            ),
                        ),

                        class_="panel-foot",
                    ),
                ),
                class_="col-12",
            ),
            class_="row",
        ),

        full_screen=True,
        class_="thematique-card",
    )




# ---------- Blocs UI réutilisables ----------
def bloc_repartition():
    """Navset Répartition : Europe (map+barres+KPI) / FLAP-D (placeholder)"""

    # Contenu Europe
    europe_panel = ui.div(
        ui.div(
            {"class": "section-lead"},
            ui.h2("Europe"),
            ui.p(
                    "Ce module présente la distribution spatiale des data centers en Europe et met en évidence "
                    "les logiques de concentration géographique du secteur numérique. "
                    "La carte met en relation", ui.strong(" le nombre total de data centers par pays avec la population, "),
                    "afin de mesurer l’intensité relative de l’équipement numérique."
                ),
        ),
        dropcard(
            "Savoir plus",
            ui.div(
                ui.p(
                    ui.strong("📍 Facteurs explicatifs : "),
                    "la localisation des data centers résulte de la combinaison de plusieurs déterminants : "
                    "(1) la proximité des marchés de la donnée et des utilisateurs, "
                    "(2) la connectivité internationale (câbles sous-marins, points de peering), "
                    "(3) la disponibilité foncière et la stabilité réglementaire, "
                    "et surtout (4) la ",
                    ui.strong("sécurité et compétitivité de l’approvisionnement électrique."),
                ),
                ui.p(
                    ui.strong("⚡ Vers une recomposition spatiale : "),
                    "l’émergence des usages liés à l’intelligence artificielle (IA) "
                    "modifie les logiques traditionnelles d’implantation. "
                    "Les centres de calcul dédiés aux modèles d’IA sont fortement ",
                    ui.strong("électro-intensifs"),
                    " et nécessitent des sites capables de fournir une énergie abondante, stable et décarbonée. "
                ),
                ui.p(
                    ui.strong("🔮 Perspective : "),
                    "à moyen terme, la carte européenne des data centers pourrait connaître une transformation profonde. "
                    "La géographie du numérique, historiquement centrée sur les grands hubs métropolitains, "
                    "pourrait se redéfinir autour de la ",
                    ui.strong("géographie énergétique"),
                    " — c’est-à-dire des territoires capables de garantir un accès durable à l’électricité bas carbone. "
                    "Cette évolution souligne le lien croissant entre transition numérique et transition énergétique au sein du continent européen."
                ),
            ),
        ),
        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-map-location-dot"}),
                        ui.h4("Répartition des data centers en Europe", class_="panel-title"),
                    ),
                    ui.div(
                        ui.div(ui.output_ui("repartition_map"), class_="map-wrap"),
                        class_="panel-body",
                    ),
                    ui.div(
                        ui.p(
                            ui.strong("🗺️ Lecture de la carte : "),
                            "les teintes de couleur représentent le ratio de data centers par million d’habitants, "
                            "tandis que la taille des cercles indique le volume total d’infrastructures implantées. "
                            "Les pays affichant des cercles importants et des teintes soutenues combinent à la fois un parc volumineux "
                            "et une densité d’équipement élevée."),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-chart-bar"}),
                        ui.h4("Part du nombre des DC en Europe", class_="panel-title"),
                    ),
                    ui.div(sw.output_widget("dc_share_plot"), class_="panel-body"),
                    ui.div(
                        ui.p(
                            ui.strong("📊 Interprétation du graphique associé : "),
                            "le diagramme en barres classe les pays selon leur part dans le total européen de data centers. "
                            "L’analyse révèle une forte concentration : quelques États membres, "
                            "notamment l’Allemagne, les Pays-Bas, la France, le Royaume-Uni et l’Irlande, "
                            "regroupent la majorité du parc. Cette configuration traduit l’existence de pôles structurants "
                            "— souvent désignés sous l’acronyme ‘FLAP-D’ — qui concentrent les ressources en connectivité et en capacités de traitement."),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            class_="row gap-4 row-eq",
        ),
        ui.div(
            ui.div(
                ui.div(
                    {"class": "kpi-card accent-bolt"},
                    ui.div({"class": "kpi-icon"}, ui.tags.i({"class": "fa-solid fa-bolt"})),
                    ui.div({"class": "kpi-title"}, "Data centers recensés"),
                    ui.div({"class": "kpi-value"}, ui.output_text("kpi_total_dc")),
                    ui.p("Nombre total de data centres recensés", class_="mb-0"),
                ),
                class_="col",
            ),
            ui.div(
                ui.div(
                    {"class": "kpi-card accent-rank"},
                    ui.div({"class": "kpi-icon"}, ui.tags.i({"class": "fa-solid fa-ranking-star"})),
                    ui.div({"class": "kpi-title"}, "Pays leader"),
                    ui.div({"class": "kpi-value"}, ui.output_text("kpi_leader_value")),
                    ui.p("Part de l'Allemagne"),
                ),
                class_="col",
            ),
            ui.div(
                ui.div(
                    {"class": "kpi-card accent-geo"},
                    ui.div({"class": "kpi-icon"}, ui.tags.i({"class": "fa-solid fa-globe"})),
                    ui.div({"class": "kpi-title"}, "Concentration géographique"),
                    ui.div({"class": "kpi-value"}, ui.output_text("kpi_top10")),
                    ui.p("Part des 10 premiers pays", class_="mb-0"),
                ),
                class_="col",
            ),
            class_="row gap-4 mt-3",
        ),
    )

    # --- FLAP-D ---
    flapd_panel = ui.div(

        # --- Titre + intro ---
        ui.div(
            {"class": "section-lead"},
            ui.h2("FLAP-D"),
            ui.p(
                "Ce module présente une analyse détaillée des Data Centers situés dans les cinq grands hubs européens "
                "regroupés sous l’acronyme FLAP-D : ",
                ui.strong("Francfort, Londres, Amsterdam, Paris et Dublin."),
                " Ces pôles concentrent une part importante des capacités d’hébergement et de connectivité en Europe."
            ),
        ),

        # --- Dropcard (Savoir plus) ---
        dropcard(
            "Résumé — FLAP-D",
            ui.div(
                ui.p(
                    ui.strong("📍 Hubs étudiés : "),
                    "les data centers sont automatiquement rattachés au hub le plus proche via un algorithme géographique "
                    "tenant compte de la position exacte (latitude/longitude)."
                ),
                ui.p(
                    ui.strong("⚡ Lectures croisées : "),
                    "la carte permet de visualiser les sites selon leur puissance installée et leur surface au sol, "
                    "tandis que le tableau synthétise les caractéristiques moyennes par hub."
                ),
                ui.p(
                    ui.strong("🔍 Méthodologie : "),
                    "les données proviennent d’une harmonisation de sources ouvertes (DataCenterMap – avril 2025). "
                    "Les valeurs manquantes sont mesurées via des indicateurs de complétude (pastilles colorées)."
                ),
                style="font-size: 15px; line-height: 1.55;",
            ),
        ),

        # --- Carte FLAP-D ---
        ui.div(
            {"class": "panel"},
            ui.div(
                {"class": "panel-head"},
                ui.tags.i({"class": "fa-solid fa-map-location-dot"}),
                ui.h4("Carte des Data Centers FLAP-D", class_="panel-title"),
            ),

            ui.div(
                {"class": "panel-body"},
                ui.div(
                    {"style": "padding: 16px; border-radius: 8px;"},

                    # Boutons FLAPD
                    ui.div(
                        {"class": "row gap-2 mb-3"},
                        ui.div(ui.input_action_button("go_frankfurt", "🇩🇪 Frankfurt am Main", class_="btn btn-outline-primary w-100"), class_="col"),
                        ui.div(ui.input_action_button("go_london", "🇬🇧 London", class_="btn btn-outline-primary w-100"), class_="col"),
                        ui.div(ui.input_action_button("go_amsterdam", "🇳🇱 Amsterdam", class_="btn btn-outline-primary w-100"), class_="col"),
                        ui.div(ui.input_action_button("go_paris", "🇫🇷 Paris", class_="btn btn-outline-primary w-100"), class_="col"),
                        ui.div(ui.input_action_button("go_dublin", "🇮🇪 Dublin", class_="btn btn-outline-primary w-100"), class_="col"),
                        ui.div(ui.input_action_button("reset_vue", "🌍 Vue globale", class_="btn reset-btn w-100"), class_="col"),
                    ),

                    ui.output_ui("map_flapd_sites", class_="mt-3"),
                ),
            ),

            # --- Texte explicatif juste après la carte ---
            ui.div(
                {"class": "panel-foot"},

                ui.p(
                    ui.strong("🗺️ Lecture de la carte : "),
                    "les cercles représentent les data centers du hub sélectionné. Leur taille dépend de la surface (m²) "
                    "et leur couleur de la puissance électrique (MW). Les communes limitrophes sont automatiquement incluses "
                    "pour mieux représenter chaque pôle géographique."
                ),

                dropcard(
                    "Interprétation — Carte FLAP-D",
                    ui.div(
                        ui.p(
                            "Chaque hub FLAP-D présente une organisation spatiale distincte, combinant cœur urbain et périphéries spécialisées :"
                        ),
                        ui.tags.ul(
                            ui.tags.li(
                                "🇳🇱 ", ui.strong("Amsterdam : "),
                                "hub compact et dense, centré sur le Science Park. Forte concentration de sites de taille "
                                "moyenne, complétés par quelques grands campus vers Schiphol."
                            ),
                            ui.tags.li(
                                "🇮🇪 ", ui.strong("Dublin : "),
                                "pôle structuré autour des parcs d’activités à l’ouest de la ville. Capacités homogènes, "
                                "moins dispersées spatialement que dans les autres hubs."
                            ),
                            ui.tags.li(
                                "🇩🇪 ", ui.strong("Francfort : "),
                                "l’un des hubs les plus denses et puissants. Mélange de grands sites et d’extensions "
                                "périphériques (Offenbach, Wiesbaden). Forte intensité électrique."
                            ),
                            ui.tags.li(
                                "🇬🇧 ", ui.strong("Londres : "),
                                "hub le plus diversifié et le plus étendu. Importante dispersion géographique, des "
                                "sites anciens du centre aux grands pôles spécialisés comme Slough."
                            ),
                            ui.tags.li(
                                "🇫🇷 ", ui.strong("Paris : "),
                                "forte périphérisation au nord et à l’ouest (Saint-Denis, Aubervilliers). Répartition "
                                "entre nombreux sites intermédiaires et quelques très grands campus."
                            ),
                        ),
                        style="font-size: 15px; line-height: 1.55;",
                    ),
                ),
            ),
        ),

        # --- Tableau FLAP-D ---
        ui.div(
            {"class": "panel mt-4"},
            ui.div(
                {"class": "panel-head"},
                ui.tags.i({"class": "fa-solid fa-table"}),
                ui.h4("Tableau synthétique – FLAP-D", class_="panel-title"),
            ),

            ui.div(
                {"class": "panel-body"},
                ui.output_ui("encarts_villes"),
            ),

            ui.div(
                {"class": "panel-foot"},

                ui.p(
                    ui.strong("📊 Lecture du tableau : "),
                    "chaque hub présente des indicateurs moyens et totaux. Les pastilles colorées indiquent "
                    "la complétude de l’information pour chaque variable (surface, puissance, PUE)."
                ),

                dropcard(
                    "Interprétation — Tableau FLAP-D",
                    ui.div(
                        ui.p(
                            "Le tableau met en évidence les différences de capacité, de surface et de complétude entre les hubs :"),
                        ui.tags.ul(
                            ui.tags.li(
                                "🇳🇱 ", ui.strong("Amsterdam : "),
                                "surfaces et puissances moyennes modérées ; tissu homogène de sites intermédiaires."),
                            ui.tags.li(
                                "🇮🇪 ", ui.strong("Dublin : "),
                                "capacités élevées malgré un nombre plus restreint de sites ; données souvent incomplètes."),
                            ui.tags.li(
                                "🇩🇪 ", ui.strong("Francfort : "),
                                "parmi les puissances moyennes les plus hautes ; forte présence de grands sites."),
                            ui.tags.li(
                                "🇬🇧 ", ui.strong("Londres : "),
                                "forte dispersion des capacités ; cohabitation de très grands campus et de sites plus anciens."),
                            ui.tags.li(
                                "🇫🇷 ", ui.strong("Paris : "),
                                "surfaces moyennes élevées tirées par quelques méga-sites ; nombreux sites intermédiaires."),
                            ui.tags.li(
                                "📉 ", ui.strong("Qualité des données : "),
                                "PUE, année et tier souvent manquants, surtout à Dublin et Francfort : "
                                "à lire comme des ordres de grandeur."),
                        ),
                        style="font-size: 15px; line-height: 1.55;",
                    ),
                ),
            ),
        ),

        class_="pt-2",
    )



    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": "fa-solid fa-chart-area me-2"}),
            "Répartition des DC",
        ),
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

    # France
    france = ui.div(
        ui.div(
            {"class": "section-lead"},
            ui.h2("Europe"),
            ui.p(
                    "Ce module propose une lecture territorialisée de la", ui.strong(" production et de la consommation d’électricité"), " en France entre 2014 et 2024. "
                    "L’enjeu est de montrer que le système électrique français n’est pas homogène : certaines régions sont structurellement "
                    "productrices, d’autres structurellement consommatrices."
                ),
        ),
        dropcard(
            "Savoir plus",
            ui.div(
                ui.p(
                    ui.strong("📍 Le cas d’Auvergne–Rhône-Alpes (AURA) : "),
                    "dans la série retenue, AURA apparaît comme l’une des régions les plus productrices de France. "
                    "Ce résultat tient à la combinaison d’un parc ",
                    ui.strong("hydroélectrique"),
                    " ancien et important (vallées alpines, aménagements du Rhône) et de raccordements structurants au réseau national.",
                ),
            ),
        ),
        ui.div(
            # Colonne GAUCHE : carte FR
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-layer-group"}),
                        ui.div(ui.output_text("map_title"), class_="panel-title"),
                    ),
                    ui.div(ui.output_ui("fr_map"), class_="panel-body"),
                    ui.div(
                        ui.p(
                            ui.strong("La carte du solde "),
                        "(production – consommation) montre, pour l’année sélectionnée, quelles régions dégagent un excédent énergétique "
                        "et lesquelles doivent être alimentées depuis d’autres territoires. Les teintes positives traduisent une capacité de "
                        "production locale supérieure aux usages, les teintes négatives l’inverse.",),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            # Colonne DROITE : camembert
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-chart-area"}),
                        ui.div(ui.output_text("pie_title"), class_="panel-title"),
                    ),
                    ui.div(
                        ui.div({"class": "mb-2"}, ui.output_ui("region_selector")),
                        sw.output_widget("prod_pie"),
                        ui.div(
                        ui.p(
                            ui.strong("Le diagramme circulaire (mix énergétique) "),
                        "détaille la composition de la production : nucléaire, hydraulique, fossile, éolien, solaire, autres. "
                        "C’est utile pour distinguer les régions disposant d’un ",
                        ui.strong("socle pilotable"),
                        " (nucléaire, hydro) de celles davantage dépendantes des filières variables.",),
                        class_="panel-foot",),
                        class_="panel-body",
                    ),
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
                    ui.div(
                        {"class": "mb-2"},
                        ui.input_slider(
                            "year",
                            "Choisir une année :",
                            min=2014,
                            max=2024,
                            value=2024,
                            step=1,
                            width="100%",
                            sep="",
                        ),
                    ),
                    ui.div(sw.output_widget("area_chart"), style="width:100%"),
                    ui.div(
                        ui.p(
                            ui.strong("Le graphique d’évolution 2014–2024 "),
                        "permet d’observer les dynamiques de long terme : montée des renouvelables, repli ponctuel du nucléaire, "
                        "stagnation ou hausse de la consommation. La superposition de la consommation est volontaire : elle permet de voir "
                        "si la demande progresse plus vite que l’offre sur un territoire donné.",),
                        class_="panel-foot",
                    ),
                    class_="panel-body",
                    style="width:100%",
                ),
            ),
            class_="col-12",
        ),
    )

    # Échanges France - voisins européens (onglet avancé)
    echanges = ui.div(
        ui.div(
            {"class": "section-lead"},
            ui.h2("Echanges France-Europe"),
            ui.p(
                "Ce module a pour objectif de montrer ", ui.strong("les flux réels d'échanges d'électricité"), " entre la France et ses voisins, et le rôle qu'ils jouent dans ", 
                ui.strong("l’équilibre énergétique régional"),
                 ". Lorsque l’on étudie le ", ui.strong("bilan énergétique français"), ", il est important de faire le point sur ces échanges avec les pays voisins : ",
                 "même si la France reste le pays qui ", ui.strong("exportent le plus d’électricité en Europe"),
                 ", elle importe aussi à certaines périodes, notamment lorsque l'électricité est moins chère chez ses voisins, ou  lorsque les barrages hydrauliques ",
                 "produisent moins, par exemple en hiver. Cela pose des questions sur la part d'", ui.strong("énergie réellement décarbonée"),
                 " consommée pendant certaines périodes."
            ),
        ),
        dropcard(
            "Savoir plus",
            ui.div(
                ui.p(
                    ui.strong("⚡ Pourquoi la France exporte autant ? "),
                    "Parce qu’elle produit généralement un peu plus d’électricité qu’elle n’en consomme, ",
                    "grâce à un parc de production très pilotable (nucléaire et hydraulique). ",
                    "Ces ",
                    ui.strong("surplus français"),
                    " sont exportés vers ses voisins européens, ",
                    "dont la production nationale couvre souvent un peu moins que leur consommation. ",
                    "Même si cet écart n’est pas énorme, il est essentiel pour l’équilibre énergétique de la région. ",
                    "Par exemple, l’Italie dépend régulièrement des importations françaises pour garantir sa stabilité électrique.",
                ),
                ui.tags.hr(),
                ui.p(
                    ui.strong("🌦️ Une production qui varie selon les saisons : "),
                    "la production d’électricité en France n’est pas constante tout au long de l’année. ",
                    "En hiver, la demande augmente fortement, et en été, certains réacteurs ou barrages ",
                    "sont moins disponibles. Dans ces périodes, la France ",
                    ui.strong("importe temporairement"),
                    " de l’électricité depuis ses voisins. ",
                    "Ainsi, même si la France reste exportatrice sur l’année, ",
                    "elle peut être importatrice sur certaines semaines ou journées. ",
                    "C’est ce que montre le graphique des échanges France ↔ voisins : ",
                    "les courbes positives traduisent des exportations, les négatives des importations.",
                ),
                ui.tags.hr(),
                ui.p(
                    ui.strong("📊 Comment lire la carte ? "),
                    "La carte te montre la situation énergétique des pays voisins à une année donnée : ",
                    "la ",
                    ui.strong("taille des cercles"),
                    " correspond à la consommation ou à la production totale (selon le filtre choisi), ",
                    "et la ",
                    ui.strong("couleur"),
                    " indique la filière dominante dans le mix (nucléaire, hydraulique, fossile, éolien, solaire...). ",
                    "Cela permet de visualiser rapidement quels pays ont une production importante ",
                    "et lesquels reposent davantage sur leurs importations.",
                ),
                ui.tags.hr(),
                ui.p(
                    ui.strong("🎯 Ce qu’il faut retenir : "),
                    "les échanges d’électricité en Europe ne sont pas un signe de fragilité, mais de ",
                    ui.strong("solidarité énergétique"),
                    ". ",
                    "La France joue un rôle de ",
                    ui.strong("stabilisateur"),
                    " : elle exporte quand ses voisins ont besoin d’énergie, ",
                    "et importe quand sa propre production est plus faible. ",
                    "Cette complémentarité renforce la ",
                    ui.strong("sécurité énergétique collective"),
                    " et montre que la France reste ",
                    "un acteur central de l’équilibre du réseau électrique européen.",
                ),
            ),
        ),
        
        # ====== Comparaison (RTE) ======
        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-arrows-left-right"}),
                        ui.h4("Echanges France - Europe", class_="panel-title"),
                    ),
                    ui.div(
                        ui.row(
                            ui.column(
                                8,
                                ui.input_checkbox_group(
                                    "ech_countries",
                                    "Pays à comparer",
                                    choices=[],
                                    selected=[],
                                    inline=True,
                                ),
                            ),
                            ui.column(
                                2,
                                ui.input_slider(
                                    "ech_roll",
                                    "Lissage (rolling, mois)",
                                    min=1,
                                    max=6,
                                    value=1,
                                    step=1,
                                ),
                            ),
                            ui.column(
                                2,
                                ui.input_action_button(
                                    "ech_compare_go",
                                    "Valider",
                                    class_="btn btn-primary",
                                ),
                            ),
                        ),
                        class_="mb-2",
                    ),
                    ui.div(
                        ui.row(
                            ui.column(
                                4,
                                ui.input_date_range(
                                    "ech_cmp_period",
                                    "Période (comparaison)",
                                    start="2019-01-01",
                                    end="2025-12-31",
                                    min="2005-01-01",
                                    max="2025-12-31",
                                    weekstart=1,
                                ),
                            ),
                            ui.column(
                                4,
                                ui.input_radio_buttons(
                                    "ech_cmp_metric",
                                    "Flux à comparer",
                                    choices=["Exportations", "Importations", "Solde"],
                                    selected="Solde",
                                    inline=True,
                                ),
                            ),
                            ui.column(
                                4,
                                ui.input_radio_buttons(
                                    "ech_cmp_agg",
                                    "Temporalité",
                                    choices=["Mensuel", "Annuel"],
                                    selected="Mensuel",
                                    inline=True,
                                ),
                            ),
                        ),
                        class_="mb-2",
                    ),
                    ui.div(sw.output_widget("comp_plot"), class_="panel-body"),
                    ui.div(
                        ui.p(
                            ui.strong("Le graphique des échanges entre la France et ses voisins : "),
                            "Le graphique présente l’évolution du solde énergétique entre la France et ses principaux voisins européens sur la période sélectionnée. Les valeurs ",
                            ui.strong("au-dessus de 0"), " indiquent que la France", ui.strong(" exporte davantage qu’elle n’importe"), " depuis le pays concerné. Pour ce qui est Les valeurs",
                            ui.strong(" en dessous de 0"), " signifient que la France", ui.strong(" importe plus qu’elle n’exporte"),
                            ". Les courbes mettent ainsi en évidence la variabilité des échanges selon les saisons, les conditions de production des différents pays et les tensions sur le marché européen de l’énergie. ",
                            "Chaque pays affiche une dynamique propre, permettant de comparer la dépendance ou la capacité d’exportation de la France vis-à-vis de ses voisins."
                            ),
                        class_="panel-foot",
                        ),
                    ),
                class_="col-12",
            ),
            class_="row gap-4",
        ),
        
        ui.hr(),
        
        ui.h3(
    "💡 ",
    ui.strong("Aide à l'interprétation"),
    " : exemple pour le mois de décembre en 2022 (2022-12-01) sur la frontière France - Belgique/Allemagne (ligne noire)",
    class_="section-title",
),
ui.row(
    {"class": "metrics-row"},
    ui.column(
        4,
        ui.div(
            {"class": "metric"},
            ui.h4("Exportations"),
            ui.div({"class": "value"}, ui.p("0,3 TWh")),
            ui.p("La France a exporté 0,3 TWh d'électricité vers Belgique/Allemagne en décembre 2022"),
        ),
    ),
    ui.column(
        4,
        ui.div(
            {"class": "metric"},
            ui.h4("Importations"),
            ui.div({"class": "value"}, ui.p("-3,3 TWh")),
            ui.p("La France a importé 3,3 TWh d'électricité depuis Belgique/Allemagne en décembre 2022"),
        ),
    ),
    ui.column(
        4,
        ui.div(
            {"class": "metric"},
            ui.h4("Solde"),
            ui.div({"class": "value"}, ui.p("-3 TWh")),
            ui.p(
                "Le solde entre exportations et importations en décembre 2022 est de : ",
                ui.em("0,3 - 3,3 = -3 (TWh)."),
                " Cela signifie qu'en décembre 2022 la France a importé (depuis Belgique/Allemagne) plus qu'elle n'a exporté (vers Belgique/Allemagne).",
            ),
        ),
    ),
),
    
        ui.hr(),
        
        # ====== Filtres (COMMUN) ======
        ui.div(
            ui.div(
                {"class": "panel"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": "fa-solid fa-sliders"}),
                    ui.h4("Filtres", class_="panel-title"),
                ),
                ui.div(
                    ui.row(
                        # 1) année OWID
                        ui.column(
                            3,
                            ui.input_select(
                                "ech_mix_year",
                                "Année (mix OWID)",
                                choices=[str(y) for y in range(2014, 2025)],
                                selected="2024",
                            ),
                        ),
                        # 2) filière de production (nouveau)
                        ui.column(
                            3,
                            ui.input_select(
                                "ech_mix_filiere",
                                "Filière de production",
                                choices={
                                    "all": "Toutes filières",
                                    "nuc": "Nucléaire",
                                    "hyd": "Hydraulique",
                                    "fos": "Fossile (incl. gaz)",
                                    "eol": "Éolien",
                                    "sol": "Solaire",
                                    "autre": "Autre",
                                },
                                selected="all",
                            ),
                        ),
                        # 3) affichage du barplot
                        ui.column(
                            3,
                            ui.input_switch(
                                "ech_plot_mode",
                                "Graphique en % (sinon TWh)",
                                value=True,
                            ),
                            ui.div(
                                "Basculer le switch pour passer de la répartition (%) au volume (TWh).",
                                class_="form-text",
                                ),
                        ),
                        # 4) bouton
                        ui.column(
                            3,
                            ui.input_action_button(
                                "ech_apply",
                                "Valider",
                                class_="btn btn-primary",
                            ),
                        ),
                    ),
                    class_="panel-body",
                ),
            ),
            class_="mb-3",
        ),
        
        # ====== Carte + Mix ======
        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-map-location-dot"}),
                        ui.h4("Mix énergétique — carte", class_="panel-title"),
                    ),
                    ui.div(ui.output_ui("map_elec"), class_="panel-body"),
                ),
                class_="col",
            ),
            ui.div(
                ui.div(
                    {"class": "panel"},
                    ui.div(
                        {"class": "panel-head"},
                        ui.tags.i({"class": "fa-solid fa-chart-bar"}),
                        ui.h4("Mix énergétique — graphique", class_="panel-title"),
                    ),
                    ui.div(sw.output_widget("bar_exports"), class_="panel-body"),
                    ui.div(
                        ui.p(
                            "NB : dans ce jeu de données, la filière ",
                            ui.strong("fossile"),
                            " regroupe le charbon, le pétrole et ",
                            ui.strong("le gaz naturel"),
                            ", ce qui explique son poids plus élevé que dans certaines statistiques nationales.",
                            class_="mt-2 mb-0",
                        ),
                        class_="panel-foot",
                    ),
                ),
                class_="col",
            ),
            class_="row gap-4 row-eq",
        ),
        ui.hr(),
    )
    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": "fa-solid fa-bolt me-2"}),
            "Bilan énergétique",
        ),
        ui.navset_tab(
            ui.nav_panel("France", france),
            ui.nav_panel("Échanges France-Europe", echanges),
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
            ui.tags.div(
                {
                    "id": "predictive-sticky",
                    "style": (
                        "position: -webkit-sticky; position: sticky;"
                        "top: 72px;"
                        "height: max-content; align-self: flex-start;"
                        "z-index: 10;"
                    ),
                },
                ui.tags.div(
                    {
                        "style": (
                            "background: var(--card);"
                            "border-radius: 12px;"
                            "padding: 16px;"
                            "box-shadow: 0 8px 24px rgba(18,38,63,.07);"
                            "border: 1px solid var(--border);"
                            "color: var(--text);"
                        ),
                    },
                    ui.tags.h4(
                        "Paramètres",
                        style=(
                            "font-weight:700;"
                            "font-size:20px;"
                            "margin:0 0 10px 0;"
                            "margin-bottom:40px"
                        ),
                    ),
                    ui.tags.hr(),
                    ui.p(
                        ui.tags.small(
                            "Déplacez les curseurs pour effectuer une estimation de la consommation d'énergie "
                            "en fonction du nombre de dc et de leur % de charge."
                        )
                    ),
                    ui.input_slider("nb_dc", ui.strong("Nombre de DC"), min=1, max=35, value=1, step=1),
                    ui.input_slider("facteur_charge", ui.strong("Facteur de charge (%)"), min=0, max=100, value=100, step=1),
                ),
            ),
            style="overflow: visible",
        ),
        # --- Résumé détaillé ---
        ui.div(
            {"class": "section-lead"},
            ui.h2("Analyse prédictive"),
            ui.p(
                "Cette simulation a pour objectif de comparer la consommation électrique projetée d'un ou plusieurs data centers (DC) avec la production totale d'énergie "
                "en France selon le rapport de RTE, sur la période 2025–2035. Les projections de consommation sont établies à partir des estimations de puissance du data center "
                "actuellement en construction à Eybens."
            ),
            ui.p(
                    ui.strong("🎯 Objectif :"),
                    " Cette simulation vise à éclairer les enjeux d'articulation entre les besoins énergétiques croissants des infrastructures numériques et les capacités de production énergétique du pays dans une perspective de planification énergétique à long terme.",
                ),
        ),
        dropcard(
            "Savoir plus",
            ui.div(
                ui.p(
                    ui.strong("📈 Hypothèses d'évolution :"),
                    " Les prévisions suivent les étapes de développement du projet Data One :",
                ),
                ui.tags.ul(
                    ui.tags.li("2025 : 15 MW"),
                    ui.tags.li("2026 : 200 MW"),
                    ui.tags.li("2028 : 400 MW"),
                    ui.tags.li("2035 : 1 000 MW"),
                ),
                ui.p(
                    "🏗️ La simulation permet d'extrapoler jusqu'à 35 data centers, en cohérence avec les ambitions exprimées par les pouvoirs publics en matière d'infrastructures numériques, notamment dans le cadre du développement de l'intelligence artificielle."
                ),
                ui.tags.hr(),
                ui.p(
                    ui.strong("⚡ Équivalent en unités de production :"),
                    " La simulation permet de comparer la consommation projetée des data centers en 2035 avec la production nécessaire par filière :",
                ),
                ui.tags.ul(
                    ui.tags.li("Réacteurs nucléaires"),
                    ui.tags.li("Grands barrages hydrauliques"),
                    ui.tags.li("Centrales à charbon"),
                    ui.tags.li("Éoliennes"),
                    ui.tags.li("Panneaux solaires"),
                    ui.tags.li("Centrales à biomasse"),
                ),
                ui.tags.hr(),
                ui.p(
                    ui.strong("💡 Conversion des unités :"),
                    " Pour comparer les consommations projetées, il est nécessaire de convertir les unités de GW en TWh/an selon la formule :",
                ),
                ui.p(ui.em("Énergie annuelle (GWh/an) = Puissance (GW) × 24 heures × 365 jours")),
                ui.p(
                    "Exemple pour un data center d'une puissance d'1 GW et un facteur de charge de 60 % : 1 × 24 × 365 × 0,6 = 5 256 GWh/an = 5,26 TWh/an"
                ),
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Tendances 2000–2050 (références)", class_="section-title"),
            sw.output_widget("energiePlot"),
            ui.div(
                        ui.p(
                            ui.strong("Le graphique d'évolution de la production et consommation énergétique en France depuis 2000 et la projection jusqu'à 2035 : "),
                        "Le graphique présente, d’une part,", ui.strong(" l’historique de la consommation et de la production d’électricité en France entre 2000 et 2025,"), 
                        " marqué par des fluctuations plus ou moins importantes en lien avec de grands événements mondiaux (crise financière de 2008, pandémie "
                        "de Covid-19 en 2020, crise énergétique et guerre en Ukraine à partir de 2022), et, d’autre part,", ui.strong(" une projection jusqu’en 2050 basée sur "
                        "les scénarios du rapport RTE, représentés par des plages d’incertitude autour des courbes de référence."), " La simulation de la consommation "
                        "énergétique des data centers se concentre sur la période comprise entre les deux lignes pointillées (2024–2035) et est détaillée dans le "
                        "graphique situé en dessous.",),
                        class_="panel-foot",),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Production vs Consommation (2025–2035)", class_="section-title"),
            sw.output_widget("energy_plot"),
            ui.div(
                {"class": "mt-2"},
                ui.row(
                    ui.column(
                        12,
                        ui.div(
                            ui.strong("Conso actuelle + conso DC en 2035 : "),
                            ui.output_text("info_conso_totale"),
                        ),
                    ),
                ),
                ui.div(
                        ui.p(ui.strong("📊 Représentation graphique :")),
                ui.tags.ul(
                    ui.tags.li(
                        "Les points rouges indiquent la consommation cumulée des data centers ajoutée à la consommation énergétique 2024 (Consommation simulée)."
                    ),
                    ui.tags.li(
                        "La courbe verte représente la trajectoire de référence de la production énergétique nationale."
                    ),
                    ui.tags.li(
                        "La courbe bleue représente la trajectoire de référence de la consommation énergétique nationale."
                    ),
                    ui.tags.li(
                        "Les pointillés verts/bleus indiquent les variations min/max des différents scénarios RTE."
                    ),
                ),
                        class_="panel-foot",),
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Équivalents de production pour 2035", class_="section-title"),
            ui.div(
                {"class": "kpi-eq"},
                ui.div(
                    ui.div(
                        {
                            "class": "kpi-card neutral",
                            "style": "border-left:6px solid #FFE18B;",
                        },
                        ui.div(
                            {"class": "kpi-icon", "style": "background:#FFE18B;color:#1f2937;"},
                            ui.tags.i({"class": "fa-solid fa-atom"}),
                        ),
                        ui.div({"class": "kpi-title"}, "Réacteurs nucléaires"),
                        ui.div(
                            {
                                "class": "kpi-value",
                                "style": "font-size:clamp(28px,2.8vw,38px);font-weight:900;",
                            },
                            ui.output_text("nuke_value"),
                        ),
                        ui.tags.small(ui.output_text("nuke_pct_total"), class_="kpi-sub"),
                    )
                ),
                ui.div(
                    ui.div(
                        {
                            "class": "kpi-card neutral",
                            "style": "border-left:6px solid #2071B2;",
                        },
                        ui.div(
                            {"class": "kpi-icon", "style": "background:#2071B2;color:#ffffff;"},
                            ui.tags.i({"class": "fa-solid fa-water"}),
                        ),
                        ui.div({"class": "kpi-title"}, "Grands barrages"),
                        ui.div(
                            {
                                "class": "kpi-value",
                                "style": "font-size:clamp(28px,2.8vw,38px);font-weight:900;",
                            },
                            ui.output_text("hydro_value"),
                        ),
                        ui.tags.small("", class_="kpi-sub"),
                    )
                ),
                ui.div(
                    ui.div(
                        {
                            "class": "kpi-card neutral",
                            "style": "border-left:6px solid #313334;",
                        },
                        ui.div(
                            {"class": "kpi-icon", "style": "background:#313334;color:#ffffff;"},
                            ui.tags.i({"class": "fa-solid fa-industry"}),
                        ),
                        ui.div({"class": "kpi-title"}, "Centrales à charbon"),
                        ui.div(
                            {
                                "class": "kpi-value",
                                "style": "font-size:clamp(28px,2.8vw,38px);font-weight:900;",
                            },
                            ui.output_text("coal_value"),
                        ),
                        ui.tags.small("", class_="kpi-sub"),
                    )
                ),
                ui.div(
                    ui.div(
                        {
                            "class": "kpi-card neutral",
                            "style": "border-left:6px solid #8DCDBF;",
                        },
                        ui.div(
                            {"class": "kpi-icon", "style": "background:#8DCDBF;color:#1f2937;"},
                            ui.tags.i({"class": "fa-solid fa-wind"}),
                        ),
                        ui.div({"class": "kpi-title"}, "Éoliennes terrestres"),
                        ui.div(
                            {
                                "class": "kpi-value",
                                "style": "font-size:clamp(28px,2.8vw,38px);font-weight:900;",
                            },
                            ui.output_text("wind_value"),
                        ),
                        ui.tags.small(ui.output_text("wind_surface"), class_="kpi-sub"),
                    )
                ),
                ui.div(
                    ui.div(
                        {
                            "class": "kpi-card neutral",
                            "style": "border-left:6px solid #F4902E;",
                        },
                        ui.div(
                            {"class": "kpi-icon", "style": "background:#F4902E;color:#1f2937;"},
                            ui.tags.i({"class": "fa-solid fa-solar-panel"}),
                        ),
                        ui.div({"class": "kpi-title"}, "Photovoltaïque"),
                        ui.div(
                            {
                                "class": "kpi-value",
                                "style": "font-size:clamp(28px,2.8vw,38px);font-weight:900;",
                            },
                            ui.output_text("solar_value"),
                        ),
                        ui.tags.small(ui.output_text("solar_surface"), class_="kpi-sub"),
                    )
                ),
                ui.div(
                    ui.div(
                        {
                            "class": "kpi-card neutral",
                            "style": "border-left:6px solid #14682D;",
                        },
                        ui.div(
                            {"class": "kpi-icon", "style": "background:#14682D;color:#ffffff;"},
                            ui.tags.i({"class": "fa-solid fa-leaf"}),
                        ),
                        ui.div({"class": "kpi-title"}, "Centrales à biomasse"),
                        ui.div(
                            {
                                "class": "kpi-value",
                                "style": "font-size:clamp(28px,2.8vw,38px);font-weight:900;",
                            },
                            ui.output_text("bio_value"),
                        ),
                        ui.tags.small("", class_="kpi-sub"),
                    )
                ),
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
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.hr(),
            ui.h4("Comparaison personnalisée"),
            ui.output_ui("entites_dyn"),
            ui.output_ui("entite_controls"),
            class_="sidebar",
        ),
        # --- Résumé détaillé ---
        ui.div(
            {"class": "section-lead"},
            ui.h2("Analyse comparative"),
            ui.p(
                "Ce graphique permet de représenter et de comparer le nombre d'habitants équivalents pour chaque palier de consommation du data center d'Eybens entre "
                "2025 et 2035. Et ce, en prenant des exemples de profils de consommation du secteur résidentiel uniquement et ceux par personne à travers le monde et en France. "
                "Les barres représentent le nombre d'habitants équivalents selon la consommation moyenne."
            ),
        ),
        dropcard(
            "Savoir plus",
            ui.div(
                ui.p(
                    ui.strong("🔍 Estimation initiale :"),
                    " La consommation du DC est basée sur le data center actuellement en construction à Éybens.",
                ),
                ui.p(
                    ui.strong("📈 Évolution prévue :"),
                    " Les projections suivent les plans de développement de Data One :",
                ),
                ui.tags.ul(
                    ui.tags.li("2025 : 15 MW"),
                    ui.tags.li("2026 : 200 MW"),
                    ui.tags.li("2028 : 400 MW"),
                    ui.tags.li("2035 : 1 000 MW"),
                ),
                ui.tags.hr(),
                ui.p(
                    ui.strong("💡 Conversion des unités :"),
                    " Pour comparer les consommations projetées de Data One aux consommations annuelles moyennes d'individus, il est nécessaire de convertir l'unité des projections de Data One (exprimées en GW) afin d'obtenir des valeurs en GWh/an. Pour ce faire, on applique la formule suivante :",
                ),
                ui.p(
                    ui.em(
                        "Énergie annuelle (en GWh/an) = Puissance (GW) × nombre d'heures d'utilisation par jour × nombre de jours d'utilisation par an"
                    )
                ),
                ui.p("Par exemple, calculons la conversion de la projection de 2035 pour 1 GW :"),
                ui.p(ui.em("Énergie annuelle (GWh) = 1 × 24 × 365 = 8 760 GWh/an")),
                ui.tags.ul(
                    ui.tags.li("Ou encore 8 760 000 000 kWh/an"),
                    ui.tags.li("Soit 8 760 000 MWh/an"),
                    ui.tags.li("Ou l'équivalent de 8,76 TWh/an"),
                ),
                ui.p(
                    "On peut donc diviser les différentes consommations annuelles projetées par la consommation moyenne souhaitée pour obtenir le nombre d'individus équivalents."
                ),
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("Habitants équivalents par palier (profils sélectionnés)", class_="section-title"),
            sw.output_widget("barplot"),
            ui.p(
                ui.strong("💡 Aide d'interprétation pour l'échelle mondiale :"),
                " Pour un data center d'une puissance de 1 GW, cela correspond à la consommation",
                " énergétique résidentielle annuelle de 3 275 991 personnes, basée sur la moyenne",
                " mondiale de 2,674 MWh par personne et par an.",
            ),
        ),
        ui.div(
            {"class": "card"},
            ui.h3("💡 Focus sur 3 pays : équivalents en population pour un data center de 1 GW", class_="section-title"),
            ui.row(
                ui.column(
                    4,
                    ui.div(
                        {"class": "metric"},
                        ui.h4("Qatar"),
                        ui.div({"class": "value"}, ui.output_text("qatar_1gw")),
                        ui.tags.small(ui.output_text("qatar_pop")),
                        ui.tags.small(ui.output_text("qatar_pct")),
                    ),
                ),
                ui.column(
                    4,
                    ui.div(
                        {"class": "metric"},
                        ui.h4("France"),
                        ui.div({"class": "value"}, ui.output_text("france_1gw")),
                        ui.tags.small(ui.output_text("france_pop")),
                        ui.tags.small(ui.output_text("france_pct")),
                    ),
                ),
                ui.column(
                    4,
                    ui.div(
                        {"class": "metric"},
                        ui.h4("Mali"),
                        ui.div({"class": "value"}, ui.output_text("mali_1gw")),
                        ui.tags.small(ui.output_text("mali_pop")),
                        ui.tags.small(ui.output_text("mali_pct")),
                    ),
                ),
            ),
        ),
        ui.div(
            {"class": "card", "id": "personalized-card"},
            ui.h3("Comparaison personnalisée", class_="section-title"),
            sw.output_widget("barplot_personalisee"),
        ),
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
                ui.tags.img(
                    src=PARTNERS_LIGHT or "images/logos.png",
                    alt="Partenaires",
                    class_="partners partners--light",
                    loading="lazy",
                ),
                ui.tags.img(
                    src=PARTNERS_DARK or "images/logos_dark.png",
                    alt="Partenaires (mode sombre)",
                    class_="partners partners--dark",
                    loading="lazy",
                ),
                class_="footer-logos",
            ),
            ui.div(
                ui.span("Conception & développement : "),
                ui.strong("Zoé CARGNELLI"),
                ui.span(" & "),
                ui.strong("Robert LIM"),
                ui.br(),
                ui.span("© 2025 — Matérialité du numérique • Projet VerIT"),
                class_="footer-credits",
            ),
            class_="footer-inner",
        ),
        ui.p(
            "Opération soutenue par l’État dans le cadre de l’AMI « Compétences et Métiers d’Avenir »  du programme France 2030, opéré par la Caisse des Dépôts (La Banque des Territoires).",
            class_="footer-text",
        ),
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
            href=(
                "https://fonts.googleapis.com/css2?"
                "family=Poppins:wght@400;600;700;800;900&display=swap"
            ),
        ),
        ui.tags.link(
            rel="stylesheet",
            href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
        ),
        ui.include_css("www/styles.css"),
        ui.tags.script(
            f"""
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
"""
        ),
        ui.tags.script(
            """
document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('predictive-sticky');   // ton bloc paramètres
  if (!el) return;

  const rail  = el.closest('[data-testid="sidebar"]') || el.parentElement; // la colonne sidebar
  const topbar = document.querySelector('.topbar');

  // règle ici la marge sous la topbar pour être bien sous les onglets
  const GAP = 160; // essaie 120–200 selon la hauteur de tes onglets
  const topbarH = () => (topbar?.offsetHeight || 56);
  const fixedTop = () => topbarH() + GAP;

  // le rail doit être positionné pour ancrer l'"absolute" éventuel
  if (getComputedStyle(rail).position === 'static') rail.style.position = 'relative';

  // ghost pour garder la place quand on passe en fixed
  const ghost = document.createElement('div');
  ghost.style.width = '100%'; ghost.style.height = '0px'; ghost.style.pointerEvents = 'none';

  // helper
  const addGhost = () => { if (!ghost.parentNode) el.parentNode.insertBefore(ghost, el); };
  const rmGhost  = () => { if (ghost.parentNode) ghost.parentNode.removeChild(ghost); };

  function place() {
    const rRect = rail.getBoundingClientRect();
    const railTop = rRect.top + window.scrollY;
    const railBot = railTop + rail.offsetHeight;
    const elH = el.offsetHeight;

    // seuil d'activation du mode fixed (quand le haut du bloc atteindrait la topbar)
    const startFix = railTop - fixedTop();

    // largeur/gauche quand on est en fixed
    const left  = rRect.left + window.scrollX;
    const width = rRect.width;

    if (window.scrollY < startFix) {
      // 1) avant le seuil: sticky natif, pas d'overlay
      rmGhost();
      el.style.position = 'sticky';
      el.style.top = fixedTop() + 'px';
      el.style.left = '';
      el.style.width = '';
      el.style.zIndex = '1';   // z-index bas -> ne recouvre pas les onglets
      return;
    }

    // 2) mode fixed sous la topbar, avec bride en bas du rail
    addGhost();                                // garde la place dans le flux
    ghost.style.height = elH + 'px';

    // top bridé pour ne pas dépasser le bas du rail
    const maxTop = Math.max(0, railBot - window.scrollY - elH);
    const clampedTop = Math.min(fixedTop(), maxTop);

    el.style.position = 'fixed';
    el.style.top = clampedTop + 'px';
    el.style.left = left + 'px';
    el.style.width = width + 'px';
    el.style.zIndex = '1';     // bas pour éviter de passer au-dessus des onglets
  }

  // init après layout
  requestAnimationFrame(() => requestAnimationFrame(() => { place(); }));

  window.addEventListener('scroll', place, { passive: true });
  window.addEventListener('resize', place);
  new ResizeObserver(place).observe(rail);

  // optionnel: cacher le handle "Drag to resize sidebar" en JS (pas de CSS global)
  const handle = document.querySelector('[title="Drag to resize sidebar"]');
  if (handle) handle.style.display = 'none';
});
"""
        ),
        ui.tags.style("#personalized-card{scroll-margin-top:160px;}"),
        ui.tags.style(
            """
button[disabled] { opacity: .45 !important; cursor: not-allowed !important; }
.btn-round i { pointer-events: none; }
"""
        ),
        ui.tags.script(
            """
  // Scroll doux vers une ancre envoyée par le serveur
  Shiny.addCustomMessageHandler('scrollto', (msg) => {
    const el = document.querySelector(msg.selector);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
"""
        ),
        ui.tags.title("Matérialité du numérique"),
        ui.tags.link(rel="icon", href=LOGO_LIGHT, type="image/png"),
    ),
    ui.div(
        ui.div(
            ui.tags.a(
                ui.tags.img(
                    id="logo",
                    src=LOGO_LIGHT,
                    alt="VERIT",
                    class_=LOGO_CLASS,
                ),
                href="https://ensimag.grenoble-inp.fr/fr/l-ecole/projet-verit",
                target="_blank", 
                rel="noopener noreferrer",
            ),
            ui.div("Matérialité du numérique • Projet VerIT", class_="brand"),
            class_="brandbox",
        ),
        ui.input_switch("darkmode", "Mode sombre", value=False),
        class_="topbar",
    ),
    
    ui.tags.script("""
    (function () {
    function hook() {
        // Shiny peut ne pas être prêt immédiatement
        if (!window.Shiny || !window.Shiny.setInputValue) {
        setTimeout(hook, 100);
        return;
        }
        window.addEventListener("message", function (event) {
        if (!event || !event.data) return;
        if (event.data.type === "hub_click" && event.data.hub) {
            window.Shiny.setInputValue("hub_click", event.data.hub, { priority: "event" });
        }
        }, false);
    }
    hook();
    })();
    """),

    # Présentation générale en haut de page (plein large)
    dropcard(
        "Présentation générale",
        ui.p("Présentation globale du dashboard, contexte et mode d’emploi. (À compléter…)"),
    ),
    bloc_hq_flapd(),
    bloc_repartition(),
    bloc_bilan(),
    bloc_simulateurs(),
    app_footer(),
)