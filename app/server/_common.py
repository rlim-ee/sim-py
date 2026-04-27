# server/_common.py — utilitaires partagés par tous les modules serveur
#
# Ce fichier centralise quatre types de ressources :
#
#   1. CACHE GLOBAL — évite de recharger les mêmes fichiers de données
#      à chaque interaction utilisateur. Un CSV chargé une fois reste
#      en mémoire pour toute la durée de vie du processus.
#
#   2. MODE SOMBRE — détecte si l'utilisateur a activé le thème sombre
#      pour adapter les couleurs des graphiques en conséquence.
#
#   3. THÈME PLOTLY — palette cohérente appliquée à tous les graphiques
#      interactifs de l'application (Plotly est la bibliothèque qui
#      produit les graphiques cliquables et survolables).
#
#   4. FILIÈRES ÉNERGÉTIQUES — liste unique des codes, libellés et
#      couleurs par filière, pour que tous les modules utilisent
#      exactement les mêmes valeurs sans copier-coller.
from __future__ import annotations

import hashlib
from typing import Any, Callable


# =====================================================================
# Cache global (niveau module Python, donc partagé entre toutes les sessions)
# =====================================================================

_DATA_CACHE: dict[str, Any] = {}


def cached(key: str, loader: Callable[[], Any]) -> Any:
    """Charge la valeur via loader() une seule fois, puis la garde en mémoire."""
    if key not in _DATA_CACHE:
        _DATA_CACHE[key] = loader()
    return _DATA_CACHE[key]


def cache_clear(prefix: str | None = None) -> None:
    """Vide le cache (entier, ou seulement les clés commençant par prefix)."""
    if prefix is None:
        _DATA_CACHE.clear()
        return
    for k in [k for k in _DATA_CACHE if k.startswith(prefix)]:
        _DATA_CACHE.pop(k, None)


# =====================================================================
# Mode sombre — lu depuis l'input Shiny "darkmode" (une checkbox HTML)
# =====================================================================
def is_dark(input) -> bool:
    """Renvoie True si l'utilisateur a activé le mode sombre."""
    try:
        dm = getattr(input, "darkmode", None)
        return bool(dm()) if callable(dm) else False
    except Exception:
        return False


# =====================================================================
# Thème Plotly — couleurs adaptées clair/sombre
# Retourne un dictionnaire de couleurs prêt à l'emploi dans fig.update_layout()
# =====================================================================
def plotly_theme(is_dark_flag: bool) -> dict:
    """Palette Plotly cohérente entre tous les modules."""
    return {
        "font":          "#e5e7eb"              if is_dark_flag else "#0f172a",
        "grid":          "rgba(203,213,225,.26)" if is_dark_flag else "rgba(15,23,42,.08)",
        "zeroline":      "rgba(148,163,184,.60)" if is_dark_flag else "rgba(100,116,139,.60)",
        "paper":         "rgba(0,0,0,0)",
        "plot":          "rgba(0,0,0,0)",
        "bar":           "#7c8cff"              if is_dark_flag else "#5B7CFF",
        "bar_outline":   "rgba(255,255,255,.18)" if is_dark_flag else "rgba(0,0,0,.08)",
        "legend_bg":     "rgba(15,23,42,.92)"   if is_dark_flag else "rgba(255,255,255,.94)",
        "legend_border": "rgba(148,163,184,.85)" if is_dark_flag else "rgba(15,23,42,.45)",
    }


def text_color(is_dark_flag: bool) -> str:
    return "#F8FAFC" if is_dark_flag else "#0B162C"


def grid_color(is_dark_flag: bool) -> str:
    return "rgba(203,213,225,.28)" if is_dark_flag else "rgba(15,22,44,.08)"


# =====================================================================
# Jitter déterministe — décale légèrement les marqueurs superposés sur la carte
# sans que la position change d'un rechargement à l'autre (même seed = même décalage)
# =====================================================================
def stable_jitter(seed_value, amplitude: float = 0.002) -> float:
    h = hashlib.md5(str(seed_value).encode("utf-8")).hexdigest()
    # 8 caractères hex → entier entre 0 et 16^8−1 → ramené dans [0, 1)
    frac = int(h[:8], 16) / 0xFFFFFFFF
    return (frac * 2.0 - 1.0) * amplitude


# =====================================================================
# Filières énergétiques — source de vérité unique
# Tous les modules qui manipulent des données par filière utilisent ces constantes
# pour garantir la cohérence des couleurs et des libellés.
# =====================================================================
FILIERE_CODES: list[str] = ["nuc", "hyd", "fos", "eol", "sol", "autre"]

FILIERE_LABEL: dict[str, str] = {
    "nuc":   "Nucléaire",
    "hyd":   "Hydraulique",
    "fos":   "Fossile",
    "eol":   "Éolien",
    "sol":   "Solaire",
    "autre": "Autre",
}

# Code → couleur (utilisé pour colorier les barres et segments de graphiques)
FILIERE_COLOR: dict[str, str] = {
    "nuc":   "#FFE18B",
    "hyd":   "#2071B2",
    "fos":   "#313334",
    "eol":   "#8DCDBF",
    "sol":   "#F4902E",
    "autre": "#14682D",
}

# Vues dérivées — pratiques à utiliser directement dans les graphiques
FILIERE_LABELS_FR: list[str] = [FILIERE_LABEL[c] for c in FILIERE_CODES]
FILIERE_COLOR_BY_LABEL: dict[str, str] = {
    FILIERE_LABEL[c]: FILIERE_COLOR[c] for c in FILIERE_CODES
}
