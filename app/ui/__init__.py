# ui/__init__.py — Coquille globale de l'interface
#
# Ce fichier construit uniquement la structure commune à toutes les pages :
# barre de navigation, polices, scripts JavaScript globaux, bouton "Remonter".
# Le contenu réel de chaque page est injecté dynamiquement par le serveur
# via ui.output_ui("page"), qui appelle l'une des fonctions suivantes :
#
#   ui/home_ui.py          → page d'accueil
#   ui/energie/            → module Énergie (plusieurs sous-modules)
#   ui/donnees/            → module Données
#   ui/extraction/         → module Extraction
#
# Les textes de la barre de navigation viennent de www/texts/_common.json.
from shiny import ui

from ui._common import LOGO_LIGHT, LOGO_DARK, LOGO_CLASS, load_texts


def app_ui(request):
    """Point d'entrée UI : Shiny appelle cette fonction à chaque nouvelle connexion."""
    tx = load_texts("_common").get("section3", {})

    return ui.page_fluid(

        # ======================= HEAD — ressources globales =======================
        # Tout ce qui va dans le <head> HTML : polices, icônes, CSS, scripts
        ui.head_content(
            ui.tags.meta(charset="utf-8"),
            ui.tags.meta(name="viewport", content="width=device-width, initial-scale=1"),

            # Police Poppins chargée depuis Google Fonts
            ui.tags.link(rel="preconnect", href="https://fonts.googleapis.com"),
            ui.tags.link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
            ui.tags.link(
                rel="stylesheet",
                href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800;900&display=swap",
            ),
            # Icônes Font Awesome (fa-bolt, fa-map-location-dot, etc.)
            ui.tags.link(
                rel="stylesheet",
                href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css",
            ),
            # Feuille de style principale du projet
            ui.include_css("www/styles.css"),

            # ===== Mode sombre : bascule logo + classe CSS sur <html> =====
            # Quand l'utilisateur active l'interrupteur "Mode sombre",
            # ce script met à jour la classe CSS et change le logo.
            ui.tags.script(
                f"""
document.addEventListener('DOMContentLoaded', () => {{
  const interrupteur = document.getElementById('darkmode');
  const logo         = document.getElementById('logo');
  const srcClair  = {LOGO_LIGHT!r};
  const srcSombre = {LOGO_DARK!r};

  const appliquer = () => {{
    const estSombre = !!(interrupteur && interrupteur.checked);
    document.documentElement.classList.toggle('dark', estSombre);
    if (logo) {{
      if (srcSombre && srcSombre !== 'None') {{
        logo.src = estSombre ? srcSombre : srcClair;
      }} else {{
        logo.src = srcClair;
      }}
    }}
  }};
  appliquer();
  if (interrupteur) interrupteur.addEventListener('change', appliquer);
}});
"""
            ),

            # ===== Redimensionnement des graphiques Plotly =====
            # Plotly ne se redimensionne pas automatiquement quand on change d'onglet.
            # Ce script force le recalcul à chaque fois qu'un nouvel élément apparaît.
            ui.tags.script(
                """
(function () {
  function redimensionnerTout() {
    const graphiques = document.querySelectorAll('.js-plotly-plot');
    graphiques.forEach(g => { try { Plotly.Plots.resize(g); } catch(e){} });
  }
  document.addEventListener('shiny:value',   () => requestAnimationFrame(redimensionnerTout));
  document.addEventListener('shown.bs.tab',  () => setTimeout(redimensionnerTout, 60));
  window.addEventListener('resize',          () => requestAnimationFrame(redimensionnerTout));
})();
"""
            ),

            # ===== Défilement vers un élément (déclenché par le serveur) =====
            # Le serveur peut envoyer le message "scrollto" avec un sélecteur CSS
            # pour faire défiler la page automatiquement vers un élément précis.
            ui.tags.script(
                """
Shiny.addCustomMessageHandler('scrollto', (msg) => {
  const el = document.querySelector(msg.selector);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
"""
            ),

            # ===== Bouton flottant "Remonter en haut" =====
            # Apparaît après 320px de défilement, remonte en douceur au clic.
            ui.tags.script(
                """
(function () {
  function init() {
    const btn = document.getElementById('scroll-top-fab');
    if (!btn) return;
    const surDefilement = () => {
      if (window.scrollY > 320) btn.classList.add('visible');
      else                       btn.classList.remove('visible');
    };
    window.addEventListener('scroll', surDefilement, { passive: true });
    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    surDefilement();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
"""
            ),

            ui.tags.style("#personalized-card{scroll-margin-top:160px;}"),
            ui.tags.style(
                "button[disabled]{opacity:.45!important;cursor:not-allowed!important}"
            ),

            ui.tags.title(tx.get("titre_page", "")),
            ui.tags.link(rel="icon", href=LOGO_LIGHT, type="image/png"),
        ),

        # ======================= BARRE DE NAVIGATION (haut de page) =======================
        ui.div(
            ui.div(
                # Logo cliquable → site VerIT
                ui.tags.a(
                    ui.tags.img(
                        id="logo",
                        src=LOGO_LIGHT,
                        alt=tx.get("alt_logo", ""),
                        class_=LOGO_CLASS,
                    ),
                    href=tx.get("url_logo", "#"),
                    target="_blank",
                    rel="noopener noreferrer",
                ),
                ui.div(tx.get("marque_html", ""), class_="brand"),
                class_="brandbox",
            ),
            # Interrupteur mode sombre — son état est lu par le serveur via input.darkmode()
            ui.input_switch("darkmode", tx.get("libelle_mode_sombre", ""), value=False),
            class_="topbar",
        ),

        # ======================= CONTENU PRINCIPAL (injection dynamique) =======================
        # C'est ici que le serveur insère la page active (accueil, énergie, données…)
        ui.output_ui("page"),

        # ======================= BOUTON FLOTTANT "REMONTER" =======================
        ui.tags.button(
            ui.HTML("<i class='fa-solid fa-arrow-up'></i>"),
            id="scroll-top-fab",
            type="button",
            **{
                "aria-label": tx.get("aria_remonter", ""),
                "title":      tx.get("titre_remonter", ""),
            },
        ),
    )
