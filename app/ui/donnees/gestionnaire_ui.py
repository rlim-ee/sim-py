# ui/donnees/gestionnaire_ui.py — interface du module Données
#
# Ce module répond à la question : "qui opère les data centers FLAP-D, et depuis où ?"
# Il présente trois visualisations :
#
#   1. Carte choroplèthe + flèches (pays d'origine des sièges sociaux → hub)
#   2. Treemap (répartition des entreprises par hub et par pays d'origine)
#   3. Tableau Top 5 des opérateurs les plus présents
#
# Les visualisations sont calculées par server/donnees/gestionnaire.py.
# Les textes viennent de www/texts/donnees/gestionnaire.json.
from shiny import ui

from ui._common import load_texts, html


def bloc_hq_flapd():
    """Construit la carte complète 'FLAP-D — Pays d'origine (HQ)'."""
    tx = load_texts("donnees.gestionnaire")
    s1, s2, s3, s4 = (tx.get(f"section{i}", {}) for i in range(1, 5))

    def _entete_panneau(classe_icone: str, contenu_titre):
        """Construit l'en-tête d'un panneau (icône + titre)."""
        return ui.div(
            {"class": "panel-head"},
            ui.tags.i({"class": classe_icone}),
            ui.div(contenu_titre, class_="panel-title"),
        )

    def _accordeon_aide(titre: str, elements: list):
        """Accordéon d'aide contextuelle pour chaque panneau."""
        return ui.accordion(
            ui.accordion_panel(
                titre,
                ui.div(
                    *[ui.p(item) for item in elements],
                    class_="text-muted",
                    style="font-size:13px;line-height:1.45;",
                ),
            )
        )

    return ui.card(

        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": tx.get("icone_carte", "")}),
            tx.get("titre_carte", ""),
        ),

        ui.div(
            {"class": "section-lead"},
            ui.h2(s1.get("titre",        "")),
            ui.p(s1.get("introduction", "")),
        ),

        # ===============================
        # LIGNE 1 — CARTE + TREEMAP
        # ===============================
        ui.div(
            ui.div(

                # ---- Carte choroplèthe (rendue par server → map_hq_flapd) ----
                ui.div(
                    ui.div(
                        {"class": "panel"},

                        _entete_panneau(
                            s2.get("icone", ""),
                            # id_titre est le nom de l'output Shiny qui fournit le titre dynamique
                            ui.output_text(s2.get("id_titre", "titre_carte_hq")),
                        ),

                        ui.div(
                            ui.p(
                                html(s1.get("instruction_carte_html", "")),
                                style="margin:0 0 10px 0;",
                            ),
                            # Conteneur à ratio fixe pour la carte Folium
                            ui.div(
                                {"style": (
                                    "width:100%;height:0;padding-bottom:65%;"
                                    "position:relative;overflow:hidden;border-radius:8px;"
                                )},
                                ui.div(
                                    {"style": (
                                        "position:absolute;top:0;left:0;"
                                        "width:100%;height:100%;"
                                    )},
                                    ui.output_ui("map_hq_flapd"),
                                ),
                            ),
                            class_="panel-body",
                        ),

                        ui.div(
                            ui.div(ui.output_ui("commentaire_carte_hq"), style="color:#111;"),
                            ui.div(
                                {"class": "mt-2"},
                                _accordeon_aide(
                                    s2.get("titre_aide",    ""),
                                    s2.get("elements_aide", []),
                                ),
                            ),
                            class_="panel-foot",
                        ),
                    ),
                    class_="col",
                ),

                # ---- Treemap (rendu par server → treemap_hq) ----
                ui.div(
                    ui.div(
                        {"class": "panel"},

                        _entete_panneau(
                            s3.get("icone", ""),
                            ui.div(s3.get("titre", "")),
                        ),

                        ui.div(
                            ui.div(
                                ui.output_ui("treemap_hq"),
                                style="width:100%;height:420px;",
                            ),
                            class_="panel-body",
                        ),

                        ui.div(
                            ui.div(ui.output_ui("commentaire_treemap_hq"), style="color:#111;"),
                            ui.div(
                                {"class": "mt-2"},
                                _accordeon_aide(
                                    s3.get("titre_aide",    ""),
                                    s3.get("elements_aide", []),
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

        # ===============================
        # LIGNE 2 — TABLEAU TOP 5
        # ===============================
        ui.div(
            ui.div(
                ui.div(
                    {"class": "panel"},

                    _entete_panneau(
                        s4.get("icone", ""),
                        ui.output_text(s4.get("id_titre", "titre_top5")),
                    ),

                    ui.div(
                        # Tableau de données interactif (rendu par server → top5_table)
                        ui.output_data_frame("top5_table"),
                        class_="panel-body",
                    ),

                    ui.div(
                        ui.div(ui.output_ui("commentaire_top5_hq"), style="color:#111;"),
                        ui.div(
                            {"class": "mt-2"},
                            _accordeon_aide(
                                s4.get("titre_aide",    ""),
                                s4.get("elements_aide", []),
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
