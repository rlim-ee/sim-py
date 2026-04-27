# ui/home_ui.py — Page d'accueil de l'application
#
# Cette page est la première chose que voit l'utilisateur.
# Elle affiche :
#   - un texte d'introduction et des chiffres clés
#   - trois cartes cliquables pour accéder aux modules (Énergie, Données, Extraction)
#
# Les textes viennent de www/texts/home.json.
# Quand l'utilisateur clique sur une carte, le serveur (server/__init__.py)
# détecte l'événement et remplace cette page par la page du module correspondant.
from shiny import ui

from ui._common import app_footer, load_texts, html


def _carte_module(
    *,
    id_bouton:    str,
    icone:        str,
    accent:       str,
    kicker:       str,
    titre:        str,
    accroche:     str,
    contenu:      list,
    appel_action: str,
):
    """Construit une carte de module (bloc cliquable menant à un sous-module).
    Chaque paramètre correspond à un champ du JSON home.json > modules."""
    elements_liste = [ui.tags.li(c) for c in contenu]
    return ui.div(
        {"class": "col"},
        ui.div(
            {"class": f"home-module home-module--{accent}"},
            ui.div(
                {"class": "home-module-head"},
                ui.div(
                    {"class": "home-module-icon"},
                    ui.tags.i({"class": f"fa-solid {icone}"}),
                ),
                ui.div(
                    {"class": "home-module-titleblock"},
                    ui.div(kicker, class_="home-module-kicker"),
                    ui.div(titre, class_="home-module-title"),
                ),
            ),
            ui.p(accroche, class_="home-module-tagline"),
            ui.tags.ul(*elements_liste, class_="home-module-list"),
            # Le bouton déclenche la navigation côté serveur (voir server/__init__.py)
            ui.input_action_button(
                id_bouton,
                html(appel_action),
                class_="btn home-module-btn",
            ),
        ),
    )


def home_ui():
    """Construit et renvoie le HTML complet de la page d'accueil."""
    tx      = load_texts("home")
    s1      = tx.get("section1", {})
    s2      = tx.get("section2", {})
    stats   = tx.get("stats",    {})
    modules = tx.get("modules",  {})
    appel_action = tx.get("appel_action_html", "")

    def _stat(cle: str):
        """Construit un encart de chiffre clé (valeur + libellé)."""
        s = stats.get(cle, {})
        return ui.div(
            {"class": "home-stat"},
            ui.div(s.get("valeur",  ""), class_="home-stat-value"),
            ui.div(s.get("libelle", ""), class_="home-stat-label"),
        )

    def _module(id_bouton: str, cle_module: str):
        """Instancie une carte à partir des données JSON d'un module."""
        m = modules.get(cle_module, {})
        return _carte_module(
            id_bouton=id_bouton,
            icone=m.get("icone",    ""),
            accent=m.get("accent",  ""),
            kicker=m.get("kicker",  ""),
            titre=m.get("titre",    ""),
            accroche=m.get("accroche", ""),
            contenu=m.get("contenu", []),
            appel_action=appel_action,
        )

    return ui.div(
        {"class": "container-app"},

        # =========================================================
        # HERO — titre principal + chiffres clés
        # =========================================================
        ui.div(
            {"class": "home-hero"},
            ui.div(s1.get("titre", ""), class_="home-hero-kicker"),
            ui.h1(tx.get("titre",  ""), class_="home-hero-title"),
            ui.p(html(s1.get("introduction", "")), class_="home-hero-lead"),

            # Quatre chiffres clés mis en avant
            ui.div(
                {"class": "home-stats"},
                _stat("flapd"),
                _stat("pays"),
                _stat("periode"),
                _stat("dataone"),
            ),
        ),

        # =========================================================
        # MODULES — trois cartes d'accès
        # =========================================================
        ui.h2(s2.get("titre", ""), class_="home-section-title"),
        ui.div(
            {"class": "row gap-4 row-eq home-modules-row"},
            # go_energie / go_donnees / go_extraction : IDs Shiny écoutés par le serveur
            _module("go_energie",    "energie"),
            _module("go_donnees",    "donnees"),
            _module("go_extraction", "extraction"),
        ),

        app_footer(),
    )
