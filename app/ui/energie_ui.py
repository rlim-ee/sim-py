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
    root = pathlib.Path(__file__).parents[1] / "www"
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


# ---------- Blocs UI réutilisables ----------
def bloc_repartition():
    """Navset Répartition : Europe (map+barres+KPI) / FLAP-D (placeholder)"""

    # Contenu Europe
    europe_panel = ui.div(
        ui.div(
            {"class": "section-lead text-narrow"},
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
                            "Les teintes de couleur représentent le ratio de data centers par million d’habitants, "
                            "tandis que la taille des cercles indique le volume total d’infrastructures implantées. "),
                        ui.accordion(
                            ui.accordion_panel(
                                "Détails d’interprétation",
                                ui.p(
                                    "Les pays affichant des cercles importants et des teintes soutenues combinent à la fois un parc volumineux "
                                    "et une densité d’équipement élevée. "
                                    "On observe que les pays du Nord de l’Europe présentent les ratios de data centers par habitant les plus élevés. "
                                    "Ce phénomène s’explique en partie par leur très faible densité de population : quelques implantations "
                                    "supplémentaires suffisent à faire fortement augmenter le nombre de data centers rapporté au million d’habitants. ",
                                    ui.br(),
                                    "🇮🇪 L’Irlande constitue toutefois le cas le plus spectaculaire : c’est le pays qui concentre le plus grand "
                                    "nombre de data centers par rapport à sa population, avec plus de ", ui.strong("20"),
                                    " installations par million d’habitants, alors que la moyenne européenne se situe autour de ", ui.strong("6"),
                                    " data centers par million d’habitants.",),
                                ),
                            open=False
                            ),
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
                            "le diagramme en barres classe les pays selon leur part dans le total européen de data centers. "),
                        ui.accordion(
                            ui.accordion_panel(
                                "Détails d’interprétation",
                                ui.p(
                                    "On observe que les quatre premiers pays en nombre de data centers sont l’Allemagne, le Royaume-Uni, "
                                    "la France et les Pays-Bas. À ce noyau s’ajoute très souvent l’Irlande, en raison de sa situation "
                                    "particulière avec un nombre de data centers très élevé rapporté à la population. "
                                    "À eux cinq, ces pays concentrent ", ui.strong("plus de la moitié"),
                                    " des data centers recensés en Europe, ce qui révèle une forte concentration des infrastructures. "
                                    "Cette configuration correspond aux pôles structurants souvent désignés sous l’acronyme ", ui.strong("« FLAP-D »"),
                                    " (Francfort, Londres, Amsterdam, Paris, Dublin), qui concentrent les ressources en connectivité "
                                    "et en capacités de traitement.",),
                                ),
                            open=False,  
                            ),
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
        {"class": "section-lead text-narrow"},
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
        "Savoir plus",
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

        # --- Texte explicatif juste après la carte (comme Europe) ---
        ui.div(
            {"class": "panel-foot"},
            ui.p(
                ui.strong("🗺️ Lecture de la carte : "),
                "les cercles représentent les data centers du hub sélectionné. Leur taille dépend de la surface (m²) "
                "et leur couleur de la puissance électrique (MW). Les communes limitrophes sont automatiquement incluses "
                "pour mieux représenter chaque pôle géographique."
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

        # --- Texte explicatif sous le tableau ---
        ui.div(
            {"class": "panel-foot"},
            ui.p(
                ui.strong("📊 Lecture du tableau : "),
                "chaque hub présente des indicateurs moyens et totaux. Les pastilles colorées indiquent "
                "la complétude de l’information pour chaque variable (surface, puissance, PUE). Le tableau est", ui.strong(" triable"), " dans par ordre", ui.strong(" croissant/décroissant"), " en cliquant l'en-tête de la colonne"
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
        class_="thematique-card",
    )


def bloc_bilan():
    """Bilan énergétique — France (carte + camembert) / AURA (placeholder)"""

    # France
    france = ui.div(
        ui.div(
            {"class": "section-lead text-narrow"},
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
                    "Pour plus d'informations sur la production et la consommation énergétique en France, veuillez consulter le site de ",
                    ui.a(
                        "RTE",
                        href="https://www.rte-france.com/#",
                        target="_blank",
                        rel="noopener noreferrer",
                        ),
                    "." )
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
            {"class": "section-lead text-narrow"},
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
                                ui.tags.span(
                                    "Année (mix ",
                                    ui.tags.a(
                                        "OWID",
                                        href="https://ourworldindata.org/energy-production-consumption",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        ),
                                    ")",
                                    ),
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
        class_="thematique-card",
    )


def bloc_simulateurs():
    """2 onglets : Analyse prédictive / Analyse comparative (+ KPI neutres)"""

    # --- Analyse prédictive ---
    predictive_panel = ui.div(

    ui.div(
        {"class": "row g-4"},

        # =====================================================
        # SIDEBAR GAUCHE — STICKY
        # =====================================================
        ui.div(
            {"class": "col-12 col-lg-3", "id": "predictive-col"},

            ui.div(
                {
                    "id": "predictive-sticky",
                    "class": "sidebar",
                },

                ui.h4(
                    "Paramètres",
                    style="font-weight:700;font-size:20px;margin-bottom:16px;",
                ),

                ui.hr(),

                ui.p(
                    ui.tags.small(
                        "Déplacez les curseurs pour effectuer une estimation de la consommation d'énergie "
                        "en fonction du nombre de ", ui.strong("data centers"), ", de leur ", ui.strong("facteur de charge"),
                        " et de leur ", ui.strong("puissance"), "."
                    )
                ),

                ui.input_slider(
                    "nb_dc",
                    "Nombre de DC",
                    min=1,
                    max=35,
                    value=1,
                    step=1,
                ),

                ui.input_slider(
                    "facteur_charge",
                    "Facteur de charge (%)",
                    min=0,
                    max=100,
                    value=100,
                    step=1,
                ),
                ui.input_slider(
                    "puissance_mw",
                    "Puissance par DC (MW)",
                    min=0,
                    max=1000,
                    value=200,
                    step=10,
                    sep="",
                ),
            ),
        ),

        # =====================================================
        # CONTENU DROIT
        # =====================================================
        ui.div(
            {"class": "col-12 col-lg-9"},

            # --- Intro ---
            ui.div(
                {"class": "section-lead text-narrow"},
                ui.h2("Analyse prédictive"),
                ui.p(
                    "Cette simulation a pour objectif de comparer la consommation "
                    "électrique projetée d'un ou plusieurs data centers (DC) avec "
                    "la production totale d'énergie en France selon le ",
                    ui.a(
                        "rapport RTE",
                        href=(
                            "https://www.rte-france.com/"
                            "donnees-publications/etudes-prospectives/"
                            "futurs-energetique-2050#Lesresultatsdeletude"
                        ),
                        target="_blank",
                        rel="noopener noreferrer",
                    ),
                    " sur la période 2025–2035."
                ),
                ui.p(
                    ui.strong("🎯 Objectif : "),
                    "évaluer l’impact énergétique potentiel du développement "
                    "des data centers dans une perspective de planification "
                    "énergétique nationale."
                ),
            ),

            # --- Savoir plus ---
            dropcard(
                "Savoir plus",
                ui.p(
                    ui.strong("📈 Hypothèses d'évolution :"),
                    " Les prévisions suivent les étapes de développement du projet Data One."
                ),
                ui.tags.ul(
                    ui.tags.li("2025 : 15 MW"),
                    ui.tags.li("2026 : 200 MW"),
                    ui.tags.li("2028 : 400 MW"),
                    ui.tags.li("2035 : 1 000 MW"),
                ),
                ui.p(
                    "La simulation permet d’extrapoler jusqu’à ",
                    ui.strong("35 data centers"),
                    " afin d’explorer des scénarios de montée en charge."
                ),
                ui.hr(),
                ui.p(
                    ui.strong("💡 Conversion des unités :"),
                    " Énergie annuelle (GWh/an) = Puissance (GW) × 24 × 365 × facteur de charge"
                ),
                ui.p(
                    ui.em(
                        "Exemple : 1 GW avec 60 % de facteur de charge → "
                        "5,26 TWh/an"
                    )
                ),
            ),

            # --- Graphique historique ---
            ui.div(
                {"class": "card"},
                ui.h3("Tendances 2000–2050 (références)", class_="section-title"),
                sw.output_widget("energiePlot"),
                ui.div(
                    ui.p(
                        ui.strong("Lecture : "),
                        "historique de la production et de la consommation "
                        "électrique en France et projection selon les scénarios RTE."
                    ),
                    class_="panel-foot",
                ),
            ),

            # =====================================================
            # KPI — Équivalents de production pour 2035
            # =====================================================
ui.div(
    {"class": "card"},
    ui.h3(
        "Équivalents de production pour 2035",
        class_="section-title",
    ),

    ui.div(
        {"class": "kpi-eq"},

        # ================== NUCLEAIRE ==================
        ui.div(
            {"class": "kpi-card accent-nuke"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": "fa-solid fa-atom"}),
            ),
            ui.div({"class": "kpi-title"}, "Réacteurs nucléaires"),
            ui.div(
                {"class": "kpi-value"},
                ui.output_text("nuke_value"),
            ),
            ui.tags.small(
                ui.output_text("nuke_pct_total"),
                class_="kpi-sub",
            ),
        ),

        # ================== HYDRAULIQUE ==================
        ui.div(
            {"class": "kpi-card accent-hydro"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": "fa-solid fa-water"}),
            ),
            ui.div({"class": "kpi-title"}, "Grands barrages"),
            ui.div(
                {"class": "kpi-value"},
                ui.output_text("hydro_value"),
            ),
        ),

        # ================== CHARBON ==================
        ui.div(
            {"class": "kpi-card accent-coal"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": "fa-solid fa-industry"}),
            ),
            ui.div({"class": "kpi-title"}, "Centrales à charbon"),
            ui.div(
                {"class": "kpi-value"},
                ui.output_text("coal_value"),
            ),
        ),

        # ================== ÉOLIEN ==================
        ui.div(
            {"class": "kpi-card accent-wind"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": "fa-solid fa-wind"}),
            ),
            ui.div({"class": "kpi-title"}, "Éoliennes terrestres"),
            ui.div(
                {"class": "kpi-value"},
                ui.output_text("wind_value"),
            ),
            ui.tags.small(
                ui.output_text("wind_surface"),
                class_="kpi-sub",
            ),
        ),

        # ================== SOLAIRE ==================
        ui.div(
            {"class": "kpi-card accent-solar"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": "fa-solid fa-solar-panel"}),
            ),
            ui.div({"class": "kpi-title"}, "Photovoltaïque"),
            ui.div(
                {"class": "kpi-value"},
                ui.output_text("solar_value"),
            ),
            ui.tags.small(
                ui.output_text("solar_surface"),
                class_="kpi-sub",
            ),
        ),

        # ================== BIOMASSE ==================
        ui.div(
            {"class": "kpi-card accent-bio"},
            ui.div(
                {"class": "kpi-icon"},
                ui.tags.i({"class": "fa-solid fa-leaf"}),
            ),
            ui.div({"class": "kpi-title"}, "Centrales à biomasse"),
            ui.div(
                {"class": "kpi-value"},
                ui.output_text("bio_value"),
            ),
        ),
    ),
),


            ui.output_ui("surface_info"),
        ),
    ),
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
            {"class": "section-lead text-narrow"},
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
def energie_ui():
    return ui.div(

        # =========================================================
        # CONTENEUR GLOBAL RESPONSIVE
        # =========================================================
        ui.div(

            # =====================================================
            # NAVIGATION
            # =====================================================
            ui.div(
                ui.input_action_button(
                    "back_home",
                    "← Retour à l’accueil",
                    class_="btn btn-outline-secondary mb-3",
                ),
                class_="container-fluid px-3 px-lg-4",
            ),

            # =====================================================
            # INTRO GÉNÉRALE
            # =====================================================
            ui.div(
                dropcard(
                    "Présentation générale",
                    ui.p(
                        "Ce module est consacré à l’analyse des liens entre infrastructures numériques "
                        "(data centers) et systèmes énergétiques. Il combine une approche spatiale, "
                        "statistique et prospective afin d’évaluer les enjeux énergétiques associés "
                        "au développement du numérique."
                    ),
                    ui.p(
                        "Les analyses portent à la fois sur la répartition géographique des data centers, "
                        "le bilan énergétique français, les échanges d’électricité à l’échelle européenne "
                        "et des scénarios de consommation futurs."
                    ),
                    open=False,
                ),
                class_="container-fluid mb-5",
            ),

            # =====================================================
            # MODULE 1 — RÉPARTITION DES DATA CENTERS
            # =====================================================
            ui.div(
                bloc_repartition(),
                class_="container-fluid mb-5",
            ),

            # =====================================================
            # MODULE 2 — BILAN ÉNERGÉTIQUE
            # =====================================================
            ui.div(
                bloc_bilan(),
                class_="container-fluid mb-5",
            ),

            # =====================================================
            # MODULE 3 — SIMULATEURS
            # =====================================================
            ui.div(
                bloc_simulateurs(),
                class_="container-fluid mb-5",
            ),

            # =====================================================
            # FOOTER
            # =====================================================
            ui.div(
                app_footer(),
                class_="container-fluid mb-5",
            ),

            class_="container-fluid px-0",
        ),
    )
