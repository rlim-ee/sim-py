# ui/extraction/matieres_premieres_ui.py — interface du module Extraction
#
# Ce module montre où dans le monde sont extraits les métaux
# nécessaires aux infrastructures numériques (lithium, cobalt, nickel, cuivre, terres rares).
#
# Un menu déroulant permet de sélectionner le métal.
# La carte choroplèthe se met à jour automatiquement.
#
# La carte est calculée par server/extraction/matieres_premieres.py.
# Les textes viennent de www/texts/extraction/matieres_premieres.json.
from shiny import ui

from ui._common import dropcard, load_texts, html


def card():
    """Construit la carte complète 'Extraction des matières premières'."""
    tx = load_texts("extraction.matieres_premieres")
    s1 = tx.get("section1", {})
    s2 = tx.get("section2", {})
    s3 = tx.get("section3", {})
    s4 = tx.get("section4", {})

    contenu = ui.div(

        # Titre + introduction générale
        ui.div(
            {"class": "section-lead text-narrow"},
            ui.h2(s1.get("titre",            "")),
            ui.p(html(s1.get("introduction_html", ""))),
        ),

        # Encadré "Savoir plus" — enjeux géopolitiques des métaux critiques
        dropcard(
            s2.get("titre", ""),
            ui.div(html(s2.get("contenu_html", ""))),
        ),

        # Sélecteur de métal — change la carte en temps réel
        ui.div(
            ui.div(
                {"class": "panel"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": s3.get("icone", "")}),
                    ui.h4(s3.get("titre", ""), class_="panel-title"),
                ),
                ui.div(
                    ui.row(
                        ui.column(
                            4,
                            # "metal_selected" est l'ID Shiny, lu par le serveur
                            ui.input_select(
                                "metal_selected",
                                s3.get("libelle_selection", ""),
                                choices=s3.get("choix", {}),
                                selected="lithium",
                            ),
                        ),
                        ui.column(
                            8,
                            ui.p(
                                s3.get("aide_selection", ""),
                                class_="form-text mt-4",
                            ),
                        ),
                    ),
                    class_="panel-body",
                ),
            ),
            class_="mb-4",
        ),

        # Carte mondiale (rendue par server/extraction/matieres_premieres.py → extraction_map)
        ui.div(
            ui.div(
                {"class": "panel"},
                ui.div(
                    {"class": "panel-head"},
                    ui.tags.i({"class": s4.get("icone", "")}),
                    ui.h4(s4.get("titre", ""), class_="panel-title"),
                ),
                ui.div(
                    ui.output_ui("extraction_map"),
                    class_="panel-body",
                ),
                ui.div(
                    ui.p(html(s4.get("note_html", ""))),
                    class_="panel-foot",
                ),
            ),
            class_="mb-4",
        ),
    )

    return ui.card(
        ui.div(
            {"class": "card-title"},
            ui.tags.i({"class": tx.get("icone_carte", "")}),
            tx.get("titre_carte", ""),
        ),
        contenu,
        class_="thematique-card",
    )
