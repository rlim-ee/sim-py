# ui/energie/simulateurs/predictif_ui.py — onglet "Analyse prédictive"
#
# Interface du simulateur prédictif : l'utilisateur règle trois paramètres
# (nombre de DC, puissance unitaire, facteur de charge) et voit en temps réel
# comment la consommation électrique projetée se compare aux scénarios RTE 2025-2035.
#
# En bas de page : six encarts KPI montrant combien d'unités de production
# (réacteurs, barrages, parcs éoliens…) seraient nécessaires pour alimenter
# les data centers simulés en 2035.
#
# Toutes les valeurs affichées sont calculées par server/energie/simulateurs/predictif.py.
# Les textes viennent de www/texts/energie/simulateurs/predictif.json.
from shiny import ui
import shinywidgets as sw

from ui._common import (
    dropcard, load_texts, html,
    interp_title, savoir_plus_label,
)


def _curseur(id_shiny: str, spec: dict, **extra):
    """
    Construit un curseur (slider) à partir d'un bloc JSON.
    `id_shiny` est l'identifiant Shiny interne (lu par input.nb_dc(), etc.).
    `spec` contient les paramètres visuels : libelle, min, max, valeur, pas.
    """
    parametres = dict(
        min=spec.get("min",    0),
        max=spec.get("max",    100),
        value=spec.get("valeur", 0),
        step=spec.get("pas",   1),
    )
    parametres.update(extra)
    return ui.input_slider(id_shiny, spec.get("libelle", ""), **parametres)


def _encart_kpi(kpi: dict):
    """
    Encart KPI pour une filière de production.
    Affiche : icone, titre, valeur calculée, pourcentage du parc national, référence.
    Les valeurs (output_value, output_pct, output_extra) sont injectées par le serveur.
    """
    enfants = [
        ui.div(
            {"class": "kpi-icon"},
            ui.tags.i({"class": kpi.get("icone", "")}),
        ),
        ui.div({"class": "kpi-title"}, kpi.get("titre", "")),
        # output_text() = emplacement dont le serveur va remplir la valeur en temps réel
        ui.div({"class": "kpi-value"}, ui.output_text(kpi.get("output_value", ""))),
        ui.tags.small(ui.output_text(kpi.get("output_pct", "")), class_="kpi-sub"),
    ]
    # Surface mobilisée (uniquement pour éolien et solaire)
    if kpi.get("output_extra"):
        enfants.append(
            ui.tags.small(ui.output_text(kpi["output_extra"]), class_="kpi-sub")
        )
    enfants.append(ui.tags.small(kpi.get("reference", ""), class_="kpi-ref"))
    return ui.div(
        {"class": f"kpi-card {kpi.get('accent', '')} {kpi.get('tonalite', '')}"},
        *enfants,
    )


def _bandeau_famille(fam: dict):
    """Bandeau de catégorie séparant les trois familles de filières dans les KPI."""
    return ui.div(
        {"class": fam.get("classe_css", "eq-family-label")},
        html(fam.get("icone_html", "")),
        ui.span(fam.get("libelle", ""), class_="eq-family-text"),
    )


def panel():
    """Construit le panneau complet de l'onglet Analyse prédictive."""
    tx           = load_texts("energie.simulateurs.predictif")
    barre_lat    = tx.get("barre_laterale", {})
    s1           = tx.get("section1", {})
    s2           = tx.get("section2", {})
    s3           = tx.get("section3", {})
    s4           = tx.get("section4", {})

    curseurs = barre_lat.get("curseurs",  {})
    familles = s4.get("familles",         {})
    kpis     = s4.get("kpis",            {})

    return ui.div(
        ui.div(
            {"class": "row g-4"},

            # =====================================================
            # BARRE LATÉRALE GAUCHE — curseurs de paramétrage
            # Ces trois curseurs contrôlent tous les graphiques et KPI en temps réel.
            # =====================================================
            ui.div(
                {"class": "col-12 col-lg-3", "id": "predictive-col"},
                ui.div(
                    {"id": "predictive-sticky", "class": "sidebar"},

                    ui.h4(
                        barre_lat.get("titre", ""),
                        style="font-weight:700;font-size:20px;margin-bottom:16px;",
                    ),
                    ui.hr(),

                    ui.p(ui.tags.small(html(barre_lat.get("introduction_html", "")))),

                    # "nb_dc", "facteur_charge", "puissance_mw" sont les IDs Shiny
                    # lus par le serveur via input.nb_dc(), input.facteur_charge(), etc.
                    _curseur("nb_dc",          curseurs.get("nombre_dc",       {})),
                    _curseur("facteur_charge", curseurs.get("facteur_charge",  {})),
                    _curseur("puissance_mw",   curseurs.get("puissance_mw",    {}), sep=""),
                ),
            ),

            # =====================================================
            # CONTENU PRINCIPAL DROIT
            # =====================================================
            ui.div(
                {"class": "col-12 col-lg-9"},

                # Introduction + lien RTE
                ui.div(
                    {"class": "section-lead text-narrow"},
                    ui.h2(s1.get("titre",            "")),
                    ui.p(html(s1.get("introduction_html", ""))),
                    ui.p(html(s1.get("objectif_html",     ""))),
                ),

                # Encadré "Savoir plus" — jalons Data One + formule de conversion
                dropcard(
                    s2.get("titre", savoir_plus_label()),
                    html(s2.get("contenu_html", "")),
                ),

                # Graphique historique + projection (rendu par server → energiePlot)
                ui.div(
                    {"class": "card"},
                    ui.h3(s3.get("titre", ""), class_="section-title"),
                    sw.output_widget("energiePlot"),
                    ui.div(
                        ui.p(html(s3.get("lecture_html", ""))),
                        class_="panel-foot",
                    ),
                ),

                # =====================================================
                # KPI — Équivalents de production pour l'horizon 2035
                # Trois familles de filières, chacune précédée d'un bandeau.
                # =====================================================
                ui.div(
                    {"class": "card"},
                    ui.h3(html(s4.get("titre_html",       "")), class_="section-title"),
                    ui.p(html(s4.get("introduction_html", "")), class_="eq-intro"),

                    # Famille 1 — Bas-carbone pilotable (nucléaire, hydraulique, biomasse)
                    _bandeau_famille(familles.get("bas_carbone", {})),
                    ui.div(
                        {"class": "kpi-eq kpi-eq-3"},
                        _encart_kpi(kpis.get("nucleaire",   {})),
                        _encart_kpi(kpis.get("hydraulique", {})),
                        _encart_kpi(kpis.get("biomasse",    {})),
                    ),

                    # Famille 2 — Renouvelables variables (éolien, solaire)
                    _bandeau_famille(familles.get("renouvelables_variables", {})),
                    ui.div(
                        {"class": "kpi-eq kpi-eq-2"},
                        _encart_kpi(kpis.get("eolien",  {})),
                        _encart_kpi(kpis.get("solaire", {})),
                    ),

                    # Famille 3 — Fossile, affiché comme référence historique seulement
                    _bandeau_famille(familles.get("fossile_ref", {})),
                    ui.div(
                        {"class": "kpi-eq kpi-eq-1"},
                        _encart_kpi(kpis.get("charbon", {})),
                    ),

                    # Accordéon d'aide à la lecture des KPI
                    ui.div(
                        ui.accordion(
                            ui.accordion_panel(
                                interp_title(),
                                html(s4.get("aide_html", "")),
                                value=s4.get("id_accordeon", "interp-equivalents-2035"),
                            ),
                            open=False,
                            class_="interp-accordion",
                        ),
                        class_="mt-3",
                    ),
                ),

                # Note de bas de page sur les sources et hypothèses (rendue par le serveur)
                ui.output_ui("surface_info"),
            ),
        ),
    )
