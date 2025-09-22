# ui.py — Dashboard Shiny (3 cartes empilées + Simulateurs)
# - Logo clair/sombre auto (base64 si possible, sinon chemin statique)
# - Switch "Mode sombre" (ajoute la classe .dark sur <html>)
# - 2 onglets complets dans la carte "Simulateurs"

from shiny import ui
import shinywidgets as sw

# ====== LOGO helpers (light/dark, base64 + fallback statique) ======
import base64, pathlib, mimetypes

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
    # 1) data-uri si possible
    for p in candidates:
        if p.exists():
            uri = _data_uri_for(p)
            if uri:
                return uri
    # 2) sinon chemin statique relatif à www/
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
        light, dark = dark, None  # au pire, on réutilise le sombre comme clair
    if light is None:
        light = "images/verit_logo.png"  # ultime fallback
    logo_class = "logo" + ("" if dark else " no-dark")
    return light, dark, logo_class

LOGO_LIGHT, LOGO_DARK, LOGO_CLASS = _logo_srcs()


# ---------- Blocs UI réutilisables ----------
def bloc_thematique_simple(titre: str, suffix: str):
    """Carte simple avec 2 onglets vides."""
    return ui.card(
        ui.div({"class": "card-title"}, titre),
        ui.navset_tab(
            ui.nav_panel("Onglet 1", ui.markdown("*(vide pour le moment)*")),
            ui.nav_panel("Onglet 2", ui.markdown("*(vide pour le moment)*")),
            id=f"tabs_{suffix}",
        ),
        full_screen=True,
        class_="thematique-card",
    )


def bloc_simulateurs():
    """Carte Simulateurs contenant 2 onglets complets."""
    return ui.card(
        ui.div({"class": "card-title"}, ui.strong("Simulateurs")),
        ui.navset_tab(
            # ================ SIMULATION 1 ================
            ui.nav_panel(
                "Analyse prédictive",
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
                           sw.output_widget("energiePlot")),
                    ui.div({"class": "card"},
                           ui.h3("Production vs Consommation (2025–2035)", class_="section-title"),
                           sw.output_widget("energy_plot"),
                           ui.div({"class": "mt-2"},
                                  ui.row(
                                      ui.column(12, ui.div(ui.strong("Conso actuelle + conso DC en 2035 : "),
                                                           ui.output_text("info_conso_totale"))),
                                  ))),
                    ui.div({"class": "card"},
                           ui.h3("Équivalents de production pour 2035", class_="section-title"),
                           ui.row(
                               ui.column(4, ui.div({"class": "metric accent-orange"},
                                                   ui.h4("Réacteurs nucléaires"),
                                                   ui.div({"class": "value"}, ui.output_text("nuke_value")),
                                                   ui.tags.small(ui.output_text("nuke_pct_total")))),
                               ui.column(4, ui.div({"class": "metric accent-blue"},
                                                   ui.h4("Grands barrages"),
                                                   ui.div({"class": "value"}, ui.output_text("hydro_value")))),
                               ui.column(4, ui.div({"class": "metric accent-neutral"},
                                                   ui.h4("Centrales à charbon"),
                                                   ui.div({"class": "value"}, ui.output_text("coal_value"))))),
                           ui.row(
                               ui.column(4, ui.div({"class": "metric accent-green"},
                                                   ui.h4("Éoliennes terrestres"),
                                                   ui.div({"class": "value"}, ui.output_text("wind_value")),
                                                   ui.tags.small(ui.output_text("wind_surface")))),
                               ui.column(4, ui.div({"class": "metric accent-yellow"},
                                                   ui.h4("Photovoltaïque"),
                                                   ui.div({"class": "value"}, ui.output_text("solar_value")),
                                                   ui.tags.small(ui.output_text("solar_surface")))),
                               ui.column(4, ui.div({"class": "metric accent-cyan"},
                                                   ui.h4("Centrales à Biomasse"),
                                                   ui.div({"class": "value"}, ui.output_text("bio_value"))))),
                           ui.div({"class": "mt-2"}, ui.output_ui("surface_info"))),
                    fillable=True,
                ),
            ),
            # ================ SIMULATION 2 ================
            ui.nav_panel(
                "Analyse comparative",
                ui.layout_sidebar(
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
                    ui.div({"class": "card"},
                           ui.h3("Habitants équivalents par palier (profils sélectionnés)", class_="section-title"),
                           sw.output_widget("barplot"),
                           ui.p(ui.strong("💡 Aide d'interprétation pour l'échelle mondiale :"),
                                " Pour un data center d'une puissance de 1 GW, cela correspond à la consommation",
                                " énergétique résidentielle annuelle de 3 275 991 personnes, basée sur la moyenne",
                                " mondiale de 2,674 MWh par personne et par an.")),
                    ui.div({"class": "card"},
                           ui.h3("💡 Focus sur 3 pays : équivalents en population pour un data center de 1 GW", class_="section-title"),
                           ui.p("Ces encarts présentent le nombre d'habitants dont la consommation annuelle",
                                " équivaut à celle d'un data center de 1 GW, pour trois pays représentatifs :",
                                " un pays à très forte consommation (Qatar), un pays à très faible consommation (Mali),",
                                " et la France comme cas d'étude central."),
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
                ),
            ),
            id="sim_tabs",
        ),
        full_screen=True,
        class_="thematique-card",
    )


# ---------- UI principale ----------
app_ui = ui.page_fluid(
    # --- HEAD : polices + CSS + JS (positionnel en premier) ---
    ui.head_content(
        ui.tags.meta(charset="utf-8"),
        ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),
        # Polices + Font Awesome (CDN)
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

        # JS : toggle .dark + swap du logo clair/sombre
        ui.tags.script(f"""
document.addEventListener('DOMContentLoaded', () => {{
  const sw = document.getElementById('darkmode');
  const logo = document.getElementById('logo');
  const lightSrc = {LOGO_LIGHT!r};
  const darkSrc  = {LOGO_DARK!r}; // peut être 'None'

  const apply = () => {{
    const isDark = !!(sw && sw.checked);
    document.documentElement.classList.toggle('dark', isDark);
    if (logo) {{
      if (darkSrc && darkSrc !== 'None') {{
        logo.src = isDark ? darkSrc : lightSrc;
      }} else {{
        logo.src = lightSrc; // pas de version sombre -> même source
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

    # --- Topbar avec logo + switch sombre ---
    ui.div(
        ui.div(
            ui.tags.img(id="logo", src=LOGO_LIGHT, alt="VERIT", class_=LOGO_CLASS),
            ui.div("Matérialités du numérique • Projet VerIT", class_="brand"),
            class_="brandbox",
        ),
        ui.input_switch("darkmode", "Mode sombre", value=True),
        class_="topbar",
    ),

    # --- 3 cartes empilées ---
    bloc_thematique_simple("Répartition des data centers", "a"),
    bloc_thematique_simple("Bilan énergétique", "b"),
    bloc_simulateurs(),
)
