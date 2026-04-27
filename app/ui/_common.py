# ui/_common.py — boîte à outils partagée par toutes les pages de l'interface
#
# Ce fichier n'affiche rien lui-même. Il fournit des fonctions utilitaires
# que tous les autres fichiers ui/ importent : chargement des textes JSON,
# construction du pied de page, des encadrés déroulants, etc.
from __future__ import annotations

import base64
import json
import mimetypes
import pathlib
from functools import lru_cache

from shiny import ui


# =====================================================================
# Chemins importants
# =====================================================================
# APP_ROOT pointe vers le dossier racine du projet (là où se trouve app.py).
# On remonte d'un cran depuis ce fichier (ui/) pour l'atteindre.
APP_ROOT:  pathlib.Path = pathlib.Path(__file__).resolve().parents[1]
WWW_DIR:   pathlib.Path = APP_ROOT / "www"
TEXTS_DIR: pathlib.Path = WWW_DIR / "texts"


# =====================================================================
# Chargement des textes JSON
# =====================================================================
@lru_cache(maxsize=None)
def load_texts(nom: str) -> dict:
    """
    Charge le fichier JSON de textes correspondant à un sous-module.

    `nom` accepte une notation pointée :
      - "home"             → www/texts/home.json
      - "energie.bilan"    → www/texts/energie/bilan.json
      - "energie.simulateurs.predictif" → www/texts/energie/simulateurs/predictif.json

    Si le fichier est absent, renvoie un dict vide sans faire planter l'appli.
    Le décorateur @lru_cache garantit qu'on ne lit chaque fichier qu'une seule fois.
    """
    chemin_relatif = nom.replace(".", "/")
    chemin = TEXTS_DIR / f"{chemin_relatif}.json"
    if not chemin.exists():
        return {}
    with chemin.open("r", encoding="utf-8") as f:
        return json.load(f)


def t(textes: dict, cle: str, defaut: str = "") -> str:
    """
    Lit une valeur dans un dict imbriqué via une clé pointée.
    Exemple : t(tx, "section1.introduction_html") remonte la valeur sans KeyError.
    Renvoie `defaut` si la clé est absente.
    """
    courant = textes
    for partie in cle.split("."):
        if not isinstance(courant, dict) or partie not in courant:
            return defaut
        courant = courant[partie]
    return courant if isinstance(courant, str) else defaut


def html(s: str):
    """
    Raccourci pour insérer du HTML brut dans l'interface Shiny.
    Shiny traite tout comme du texte par défaut ; cette fonction dit
    explicitement « ce contenu est du HTML, affiche-le tel quel ».
    """
    return ui.HTML(s or "")


# =====================================================================
# Composants réutilisables (titre d'accordéon, label "Savoir plus")
# =====================================================================
def interp_title():
    """Titre HTML standard de l'accordéon 'Aide à l'interprétation'."""
    return ui.HTML(
        load_texts("_common").get("section4", {}).get(
            "interp_accordion_title_html", ""
        )
    )


def savoir_plus_label() -> str:
    """Texte du bouton 'Savoir plus' (récupéré dans _common.json)."""
    return load_texts("_common").get("section4", {}).get("libelle_savoir_plus", "")


# =====================================================================
# Gestion des logos (clair / sombre)
# =====================================================================
_EXTENSIONS = ("png", "svg", "jpg", "jpeg", "webp")


def _data_uri_pour(chemin: pathlib.Path) -> str | None:
    """Encode une image en base64 pour l'intégrer directement dans le HTML.
    Évite une requête HTTP séparée et fonctionne même sans serveur de fichiers statiques."""
    try:
        mime, _ = mimetypes.guess_type(chemin.name)
        if mime is None:
            mime = "image/svg+xml" if chemin.suffix.lower() == ".svg" else "image/png"
        donnees = base64.b64encode(chemin.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{donnees}"
    except Exception:
        return None


def _trouver_logo(noms: list[str]) -> str | None:
    """Cherche un logo parmi plusieurs noms possibles dans www/images/.
    Renvoie une data-URI si possible (prioritaire), sinon un chemin relatif."""
    racine = WWW_DIR
    candidats: list[pathlib.Path] = []
    for nom in noms:
        for ext in _EXTENSIONS:
            candidats += [racine / "images" / f"{nom}.{ext}", racine / f"{nom}.{ext}"]

    # 1er essai : data URI (intègre l'image dans le HTML)
    for p in candidats:
        if p.exists():
            uri = _data_uri_pour(p)
            if uri:
                return uri

    # 2e essai : chemin relatif simple
    for p in candidats:
        if p.exists():
            try:
                return p.relative_to(racine).as_posix()
            except Exception:
                return p.name

    return None


def _sources_logos() -> tuple[str, str | None, str]:
    """Détermine les URLs (ou data-URIs) du logo clair et du logo sombre.
    Retourne (logo_clair, logo_sombre, classe_css)."""
    clair = _trouver_logo(["verit_logo", "logo"])
    sombre = _trouver_logo(["verit_logo_dark", "logo_dark"])
    if clair is None and sombre is not None:
        clair, sombre = sombre, None
    if clair is None:
        clair = "images/verit_logo.png"
    classe = "logo" + ("" if sombre else " no-dark")
    return clair, sombre, classe


# Ces constantes sont calculées une seule fois au démarrage
LOGO_CLAIR, LOGO_SOMBRE, LOGO_CLASSE = _sources_logos()
PARTENAIRES_CLAIR = _trouver_logo(["logos"])
PARTENAIRES_SOMBRE = _trouver_logo(["logos_dark"])

# Alias pour les anciens noms (compatibilité avec ui/__init__.py)
LOGO_LIGHT  = LOGO_CLAIR
LOGO_DARK   = LOGO_SOMBRE
LOGO_CLASS  = LOGO_CLASSE


# =====================================================================
# Encadré déroulant (balise HTML <details>/<summary>)
# =====================================================================
def dropcard(titre, *enfants, ouvert: bool = False):
    """
    Crée un encadré qui se déplie au clic — c'est un <details>/<summary> HTML standard.
    Utilisé partout pour les sections 'Savoir plus' et les blocs d'intro rétractables.
    `titre` : le texte ou le HTML affiché sur la ligne cliquable.
    `*enfants` : le contenu caché jusqu'au clic.
    `ouvert` : si True, l'encadré est déplié par défaut.
    """
    attrs = {"class": "dropcard"}
    if ouvert:
        attrs["open"] = "open"
    return ui.tags.details(
        ui.tags.summary(titre),
        ui.div(*enfants, class_="dropbody"),
        **attrs,
    )


# =====================================================================
# Bouton de retour à l'accueil
# =====================================================================
def back_home_button():
    """Bouton 'Retour à l'accueil'. Le label et l'icône viennent de _common.json."""
    tx = load_texts("_common")
    sec3 = tx.get("section3", {})
    return ui.input_action_button(
        "back_home",
        html(sec3.get("bouton_accueil_html", "Retour")),
        class_="btn-back-home",
    )


# =====================================================================
# Pied de page
# =====================================================================
def app_footer():
    """Pied de page commun à toutes les pages : logos partenaires + crédits + financement."""
    tx = load_texts("_common")
    sec1 = tx.get("section1", {})
    sec2 = tx.get("section2", {})
    return ui.tags.footer(
        ui.div(
            ui.div(
                # Logo clair (visible en mode jour)
                ui.tags.img(
                    src=PARTENAIRES_CLAIR or "images/logos.png",
                    alt=sec2.get("alt_logo_partenaires", ""),
                    class_="partners partners--light",
                    loading="lazy",
                ),
                # Logo sombre (visible en mode nuit, géré par CSS)
                ui.tags.img(
                    src=PARTENAIRES_SOMBRE or "images/logos_dark.png",
                    alt=sec2.get("alt_logo_partenaires_sombre", ""),
                    class_="partners partners--dark",
                    loading="lazy",
                ),
                class_="footer-logos",
            ),
            ui.div(
                html(sec1.get("credits_html", "")),
                class_="footer-credits",
            ),
            class_="footer-inner",
        ),
        ui.p(
            sec1.get("funding_text", ""),
            class_="footer-text",
        ),
        class_="app-footer",
    )
