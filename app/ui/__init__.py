from shiny import ui
from ui.energie_ui import LOGO_LIGHT, LOGO_DARK, LOGO_CLASS


def app_ui(request):
    return ui.page_fluid(

        # ======================= HEAD GLOBAL =======================
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

            # ===== Dark mode + logo =====
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

            # ===== Resize Plotly (UNIQUE) =====
            ui.tags.script(
                """
(function () {
  function resizeAll() {
    const plots = document.querySelectorAll('.js-plotly-plot');
    plots.forEach(p => { try { Plotly.Plots.resize(p); } catch(e){} });
  }
  document.addEventListener('shiny:value', () => requestAnimationFrame(resizeAll));
  document.addEventListener('shown.bs.tab', () => setTimeout(resizeAll, 60));
  window.addEventListener('resize', () => requestAnimationFrame(resizeAll));
})();
"""
            ),

            # ===== Scroll depuis le serveur =====
            ui.tags.script(
                """
Shiny.addCustomMessageHandler('scrollto', (msg) => {
  const el = document.querySelector(msg.selector);
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
});
"""
            ),

            ui.tags.style("#personalized-card{scroll-margin-top:160px;}"),
            ui.tags.style(
                "button[disabled]{opacity:.45!important;cursor:not-allowed!important}"
            ),

            ui.tags.title("Matérialité du numérique"),
            ui.tags.link(rel="icon", href=LOGO_LIGHT, type="/image/png"),
        ),

        # ======================= TOPBAR =======================
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

        # ======================= CONTENU DYNAMIQUE =======================
        ui.output_ui("page"),
    )
