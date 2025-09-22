from __future__ import annotations

from shiny import reactive, render, ui
import shinywidgets as sw

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# --------- Couleurs ---------
COLORS = {
    "consumption": "#1F6FEB",    # clair
    "consumption_dark": "#58A6FF",
    "production":  "#2EA043",
    "accent":      "#F97316",
}

# ============================
# Données (identiques)
# ============================
consommation_actuelle = 442  # TWh (2025)

dc_data = pd.DataFrame({
    "Annee": [2025, 2026, 2028, 2035],
    "Conso": [0.131400, 1.752000, 3.504000, 8.760000],  # TWh/DC
})

production_data = pd.DataFrame({
    "Annee": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    "Min":   [538, 550, 560, 565, 568, 570, 572, 575, 578, 580, 585],
    "Max":   [538, 570, 580, 590, 595, 600, 610, 615, 620, 628, 636],
    "Ref":   [538, 560, 570, 577.5, 581.5, 585, 591, 595, 599, 604, 610.5],
})

consommation_data = pd.DataFrame({
    "Annee": [2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035],
    "Ref":   [442, 455, 468, 481, 494, 508, 514, 520, 526, 532, 538],
})

conso_hist = pd.DataFrame({
    "Annee": [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
    "Conso": [425,434,434,449,460,464,468,467,481,472,499,472,487,495,463,474,482,481,477,472,449,472,454,439,442],
})
conso_p = pd.DataFrame({
    "Annee": list(range(2025, 2051)),
    "Ref":   [442,455,468,481,494,508,514,520,526,532,538,544,550,556,562,568,574,580,586,592,598,604,610,616,622,628],
})
n = len(conso_p)
delta = np.linspace(0, 50, n)
conso_p["Min"] = (conso_p["Ref"] - delta).round(1)
conso_p["Max"] = (conso_p["Ref"] + delta).round(1)

prod_hist = pd.DataFrame({
    "Annee": [2000,2001,2002,2003,2004,2005,2006,2007,2008,2009,2010,2011,2012,2013,2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024],
    "Prod":  [517,522,533,539,546,547,546,541,545,515,550,543,542,550,538,545,531,528,548,536,500,522,446,495,539],
})
prod_p = pd.DataFrame({
    "Annee": [2025,2026,2027,2028,2029,2030,2031,2032,2033,2034,2035,2036,2037,2038,2039,2040,2041,2042,2043,2044,2045,2046,2047,2048,2049,2050],
    "Min":   [538,550,560,565,568,570,572,575,578,580,585,590,595,600,610,620,630,640,650,660,665,670,675,680,685,690],
    "Max":   [538,570,580,590,595,600,610,615,620,628,636,645,655,665,675,685,695,705,715,725,735,740,745,750,755,760],
    "Ref":   [538,560,570,577.5,581.5,585,591,595,599,604,610.5,617.5,625,632.5,642.5,652.5,662.5,672.5,682.5,692.5,700,705,710,715,720,725],
})

# ============================
# SERVER
# ============================
def server(input, output, session):

    # -- helpers thème : basé sur le switch `darkmode` (True/False)
    def _is_dark() -> bool:
        try:
            return bool(input.darkmode())
        except Exception:
            return True

    def _theme_text_color():
        return "#0B162C" if not _is_dark() else "#F8FAFC"

    def _grid_color():
        return "rgba(15,22,44,.08)" if not _is_dark() else "rgba(203,213,225,.28)"

    def _consumption_color():
        return COLORS["consumption"] if not _is_dark() else COLORS["consumption_dark"]

    def _style_fig(fig, *, height=460):
        fig.update_layout(
            template="plotly_white",
            font=dict(family="Poppins, Arial, sans-serif", size=13, color=_theme_text_color()),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            hoverlabel=dict(font_size=12, font_family="Poppins, Arial, sans-serif"),
            margin=dict(t=40, r=20, b=40, l=40),
            title_font=dict(color=_theme_text_color()),
            legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center",
                        bgcolor="rgba(0,0,0,0)", bordercolor="rgba(0,0,0,0)",
                        font=dict(color=_theme_text_color())),
            height=height,
        )
        gc = _grid_color()
        fig.update_xaxes(showgrid=True, gridcolor=gc,
                         tickfont=dict(color=_theme_text_color()),
                         title_font=dict(color=_theme_text_color()))
        fig.update_yaxes(showgrid=True, gridcolor=gc,
                         tickfont=dict(color=_theme_text_color()),
                         title_font=dict(color=_theme_text_color()))
        return fig

    # ---- Conso totale aux paliers
    @reactive.calc
    def consommation_totale():
        nb_dc = input.nb_dc()
        facteur = input.facteur_charge() / 100.0
        df = dc_data.copy()
        df["Conso_Totale"] = consommation_actuelle + (df["Conso"] * nb_dc * facteur)
        return df

    @render.text
    def facteur_charge_affiche():
        return f"⚙️ Facteur de charge appliqué : {input.facteur_charge()} %"

    # ---- Graphique tendances 2000–2050
    @output
    @sw.render_widget
    def energiePlot():
        conso_hist2 = conso_hist.assign(Type="Consommation").rename(columns={"Conso": "Value"})
        prod_hist2  = prod_hist.assign(Type="Production").rename(columns={"Prod": "Value"})
        conso_proj  = conso_p.assign(Type="Consommation").rename(columns={"Ref": "Value"})
        prod_proj   = prod_p.assign(Type="Production").rename(columns={"Ref": "Value"})

        data_lines = pd.concat([
            conso_hist2[["Annee","Value","Type"]],
            prod_hist2 [["Annee","Value","Type"]],
            conso_proj [["Annee","Value","Type"]],
            prod_proj  [["Annee","Value","Type"]],
        ])
        data_ribbons = pd.concat([
            conso_p[["Annee"]].assign(ymin=conso_p["Min"], ymax=conso_p["Max"], Type="Consommation"),
            prod_p [["Annee"]].assign(ymin=prod_p ["Min"], ymax=prod_p ["Max"], Type="Production"),
        ])

        fig = go.Figure()
        # Rubans
        for typ in ("Consommation", "Production"):
            d = data_ribbons[data_ribbons["Type"] == typ]
            fill = "rgba(31,111,235,0.14)" if typ == "Consommation" else "rgba(46,160,67,0.16)"
            fig.add_trace(go.Scatter(
                x=list(d["Annee"]) + list(d["Annee"][::-1]),
                y=list(d["ymax"]) + list(d["ymin"][::-1]),
                fill="toself", mode="none", fillcolor=fill, hoverinfo="skip", name=f"Zone {typ}"
            ))
        # Lignes
        fig.add_trace(go.Scatter(
            x=data_lines.query("Type=='Consommation'")["Annee"],
            y=data_lines.query("Type=='Consommation'")["Value"],
            mode="lines", name="Consommation",
            line=dict(color=_consumption_color(), width=2.8)))
        fig.add_trace(go.Scatter(
            x=data_lines.query("Type=='Production'")["Annee"],
            y=data_lines.query("Type=='Production'")["Value"],
            mode="lines", name="Production",
            line=dict(color=COLORS["production"], width=2.8)))

        fig.add_vline(x=2025, line_dash="dash", line_color="rgba(148,163,184,.6)")
        fig.add_vline(x=2035, line_dash="dash", line_color="rgba(148,163,184,.6)")
        fig.update_layout(legend_title_text="", xaxis_title=None, yaxis_title="TWh")
        return _style_fig(fig, height=420)

    # ---- Graphique principal (2025–2035)
    @output
    @sw.render_widget
    def energy_plot():
        conso_tot = consommation_totale()
        nb_dc = input.nb_dc()
        conso_sub = conso_p[(conso_p["Annee"] >= 2025) & (conso_p["Annee"] <= 2035)]

        p = go.Figure()
        # Bandes production
        p.add_trace(go.Scatter(
            x=list(production_data["Annee"]) + list(production_data["Annee"][::-1]),
            y=list(production_data["Max"])   + list(production_data["Min"][::-1]),
            fill="toself", mode="none", fillcolor="rgba(46,160,67,0.16)",
            line=dict(color="rgba(0,0,0,0)"), name="Zone de production", hoverinfo="skip"
        ))
        # Production
        p.add_trace(go.Scatter(x=production_data["Annee"], y=production_data["Ref"], mode="lines",
                               line=dict(color=COLORS["production"], width=4),
                               name="Projection de production de référence"))
        p.add_trace(go.Scatter(x=production_data["Annee"], y=production_data["Min"], mode="lines",
                               line=dict(color=COLORS["production"], width=2, dash="dash"),
                               name="Projection de production minimum de référence"))
        p.add_trace(go.Scatter(x=production_data["Annee"], y=production_data["Max"], mode="lines",
                               line=dict(color=COLORS["production"], width=2, dash="dash"),
                               name="Projection de production maximum de référence"))

        # Consommation + bande
        p.add_trace(go.Scatter(x=consommation_data["Annee"], y=consommation_data["Ref"], mode="lines",
                               line=dict(color=_consumption_color(), width=4),
                               name="Projection de consommation de référence"))
        p.add_trace(go.Scatter(
            x=list(conso_sub["Annee"]) + list(conso_sub["Annee"][::-1]),
            y=list(conso_sub["Max"])   + list(conso_sub["Min"][::-1]),
            fill="toself", mode="none", fillcolor="rgba(31,111,235,0.14)",
            line=dict(color="rgba(0,0,0,0)"), name="Zone de consommation", hoverinfo="skip"
        ))

        # Points conso simulée
        p.add_trace(go.Scatter(
            x=conso_tot["Annee"], y=conso_tot["Conso_Totale"], mode="markers+text",
            text=conso_tot["Annee"], textposition="top center",
            marker=dict(color=COLORS["accent"], size=13, symbol="diamond-open",
                        line=dict(color="#ffffff", width=2)),
            name=f"Consommation simulée : Consommation 2024 + consommation de {nb_dc} DC par palier",
            hovertemplate="<b>Consommation simulée</b><br>Année: %{x}<br>Consommation: %{y:.1f} TWh/an<extra></extra>",
        ))

        # Annotations
        p.add_annotation(x=production_data["Annee"].max(),
                         y=float(production_data["Ref"].iloc[-1]) + 3,
                         text="<b>Production de référence</b>", showarrow=False,
                         font=dict(color=COLORS["production"], size=13))
        p.add_annotation(x=consommation_data["Annee"].max(),
                         y=float(consommation_data["Ref"].iloc[-1]) + 3,
                         text="<b>Consommation de référence</b>", showarrow=False,
                         font=dict(color=_consumption_color(), size=13))

        p.update_layout(xaxis_title="Année", yaxis_title="Énergie (TWh/an)")
        return _style_fig(p)

    # ---- Infos & équivalents
    @render.text
    def info_conso_totale():
        nb_dc = input.nb_dc()
        facteur = input.facteur_charge() / 100.0
        conso_dc_2035 = dc_data.loc[dc_data["Annee"] == 2035, "Conso"].iloc[0] * nb_dc * facteur
        conso_totale_2035 = consommation_actuelle + conso_dc_2035
        return f"{conso_totale_2035:.0f} TWh"

    energy_per_dc_gwh = 8700  # GWh par DC
    NUC_REACTORS_TOTAL = 56
    AURA_KM2 = 69_711

    capacities = {
        "nuke": 8.2, "hydro": 1.5, "wind": 0.004, "solar": 0.00004, "coal": 3.0, "bio": 0.1
    }

    def calculate_equivalent(source: str) -> int:
        nb_dc = input.nb_dc() or 1
        facteur = input.facteur_charge() / 100.0
        conso_2035_twh = float(dc_data.loc[dc_data["Annee"] == 2035, "Conso"].iloc[0] * nb_dc * facteur)
        return int(round(conso_2035_twh / capacities[source]))

    @render.text
    def nuke_value():  return f"{calculate_equivalent('nuke'):,}".replace(",", " ")
    @render.text
    def hydro_value(): return f"{calculate_equivalent('hydro'):,}".replace(",", " ")
    @render.text
    def coal_value():  return f"{calculate_equivalent('coal'):,}".replace(",", " ")
    @render.text
    def wind_value():  return f"{calculate_equivalent('wind'):,}".replace(",", " ")
    @render.text
    def solar_value(): return f"{calculate_equivalent('solar'):,}".replace(",", " ")
    @render.text
    def bio_value():   return f"{calculate_equivalent('bio'):,}".replace(",", " ")

    @render.text
    def nuke_pct_total():
        eq = calculate_equivalent("nuke")
        pct = (eq / NUC_REACTORS_TOTAL) * 100.0
        return f"{NUC_REACTORS_TOTAL} au total — soit {pct:.2f} % du nombre total"

    @render.text
    def wind_surface():
        production_par_eolienne_gwh = 6.8
        surface_par_eolienne_km2 = 0.78
        total_gwh = input.nb_dc() * energy_per_dc_gwh
        nb_eoliennes = total_gwh / production_par_eolienne_gwh
        surface_km2 = nb_eoliennes * surface_par_eolienne_km2
        pct_fr = (surface_km2 / AURA_KM2) * 100
        return f"≈ {surface_km2:,.2f} km² occupés — soit {pct_fr:,.2f} % de l'Auvergne-Rhône-Alpes".replace(",", " ")

    @render.text
    def solar_surface():
        taille_m2 = 140
        production_totale_twh_fr = 25
        nb_installations_fr = 600_000
        prod_par_install_twh = production_totale_twh_fr / nb_installations_fr
        total_twh = (input.nb_dc() * energy_per_dc_gwh) / 1000.0  # GWh → TWh
        nb_inst = total_twh / prod_par_install_twh
        surface_km2 = (nb_inst * taille_m2) / 1e6
        pct_fr = (surface_km2 / AURA_KM2) * 100
        return f"≈ {surface_km2:,.2f} km² occupés — soit {pct_fr:,.2f} % de l'Auvergne-Rhône-Alpes".replace(",", " ")

    @output
    @render.ui
    def surface_info():
        return ui.HTML(
            """
            <p><em><strong>Note :</strong> La surface indiquée pour l’éolien correspond à la surface totale mobilisée
            (espacement, sécurité), qui n’est pas entièrement artificialisée.</em></p>
            <p><em>Pour le solaire, la surface correspond à une estimation plus proche de la surface réellement
            artificialisée au sol.</em></p>
            <p style="opacity:.8"><em>Le pourcentage affiché est calculé par rapport à une surface de référence de
            <strong>69 711 km²</strong> (Région Auvergne-Rhône-Alpes).</em></p>
            """
        )

    # ============================
    # Simulation 2
    # ============================
    consommation_habitants = pd.DataFrame({
        "Pays": [
            "Mondial", "France (68,29 M)", "Qatar (2,66 M)", "Mali (28,24 M)",
            "Etats-Unis (340,1 M)", "Chine (1 411,41 M)", "Inde (1438,60 M)", "Russie (143,8 M)"
        ],
        "Conso_MWh": [2.674, 2.223, 226.848, 0.173, 12.705, 6.113, 1.395, 6.961],
    })
    autres_pays = consommation_habitants[consommation_habitants["Pays"] != "Mondial"].copy().sort_values("Pays")
    consommation_habitants = pd.concat(
        [consommation_habitants[consommation_habitants["Pays"] == "Mondial"], autres_pays],
        ignore_index=True
    )

    dc_paliers = pd.DataFrame({
        "Nom": ["15 MW", "200 MW", "400 MW", "1 GW"],
        "Puissance_MW": [15, 200, 400, 1000],
    })
    dc_paliers["Conso_MWh_An"] = dc_paliers["Puissance_MW"] * 24 * 365

    palette_colors = ["#3B82F6", "#22C55E", "#F59E0B", "#EF4444", "#8B5CF6", "#06B6D4", "#84CC16", "#F97316"]
    dc_1gw_conso = 8_760_000  # MWh/an

    @render.text
    def france_1gw():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("France"), "Conso_MWh"].values
        return f"{int(round(dc_1gw_conso / v[0])):,}".replace(",", " ") if len(v) else ""

    @render.text
    def qatar_1gw():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Qatar"), "Conso_MWh"].values
        return f"{int(round(dc_1gw_conso / v[0])):,}".replace(",", " ") if len(v) else ""

    @render.text
    def mali_1gw():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Mali"), "Conso_MWh"].values
        return f"{int(round(dc_1gw_conso / v[0])):,}".replace(",", " ") if len(v) else ""

    @render.text
    def france_pop(): return "Population totale : 68 290 000"
    @render.text
    def qatar_pop():  return "Population totale : 2 660 000"
    @render.text
    def mali_pop():   return "Population totale : 28 243 609"

    @render.text
    def france_pct():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("France"), "Conso_MWh"].values
        pct = round((dc_1gw_conso / v[0]) / 68_290_000 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @render.text
    def qatar_pct():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Qatar"), "Conso_MWh"].values
        pct = round((dc_1gw_conso / v[0]) / 2_660_000 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @render.text
    def mali_pct():
        v = consommation_habitants.loc[consommation_habitants["Pays"].str.contains("Mali"), "Conso_MWh"].values
        pct = round((dc_1gw_conso / v[0]) / 28_243_609 * 100, 2)
        return f"Soit {pct} % de la population totale du pays"

    @output
    @render.ui
    def checkbox_group_conso():
        return ui.input_checkbox_group(
            "pays_selection",
            "Choisissez les pays (Population totale en Million) à afficher :",
            choices=list(consommation_habitants["Pays"].values),
            selected=["Mondial"],
        )

    @output
    @sw.render_widget
    def barplot():
        sel = input.pays_selection() or ["Mondial"]
        selected_data = consommation_habitants[consommation_habitants["Pays"].isin(sel)].copy()
        if selected_data.empty:
            return px.bar(title="Sélectionnez au moins un profil")

        comparison = (
            selected_data.assign(key=1)
            .merge(dc_paliers.assign(key=1), on="key")
            .drop(columns=["key"])
        )
        comparison["Habitants_equivalents"] = comparison["Conso_MWh_An"] / comparison["Conso_MWh"]
        comparison["DC"] = pd.Categorical(comparison["Nom"], categories=dc_paliers["Nom"], ordered=True)
        comparison["NomPays"] = (
            comparison["Pays"].str.replace(r" \((.*)\)", "", regex=True)
            + " (" + comparison["Conso_MWh"].astype(str) + " MWh/an)"
        )

        max_val = float(comparison["Habitants_equivalents"].max())
        if max_val >= 1e6:
            scale_factor, y_title, hover_suffix = 1e6, "Nombre d'habitants équivalents (en millions)", " millions"
        elif max_val >= 1e3:
            scale_factor, y_title, hover_suffix = 1e3, "Nombre d'habitants équivalents (en milliers)", " milliers"
        else:
            scale_factor, y_title, hover_suffix = 1, "Nombre d'habitants équivalents", ""
        comparison["Habitants_equivalents_scaled"] = comparison["Habitants_equivalents"] / scale_factor

        unique_pays = list(dict.fromkeys(comparison["NomPays"]))
        colors = {p: palette_colors[i % len(palette_colors)] for i, p in enumerate(unique_pays)}

        fig = px.bar(
            comparison, x="DC", y="Habitants_equivalents_scaled", color="NomPays",
            color_discrete_map=colors, title="Nombre d'habitants équivalents par palier"
        )
        fig.update_layout(legend_title_text="",
                          xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group")
        fig.update_traces(
            hovertemplate="Profil : %{fullData.name}<br>"
                          "Palier : %{x}<br>"
                          "Habitants équivalents : %{y:,.2f}" + hover_suffix + "<extra></extra>"
        )
        return _style_fig(fig, height=460)

    @output
    @sw.render_widget
    def barplot_personalisee():
        # récupère les deux entrées perso
        def _collect():
            rows = []
            for i in (1, 2):
                nom = getattr(input, f"nom_perso_{i}")()
                val = getattr(input, f"val_perso_{i}")()
                unit = getattr(input, f"unit_perso_{i}")()
                if not nom or val is None:
                    continue
                if unit == "kWh/an": mwh = val / 1000.0
                elif unit == "MWh/an": mwh = val
                else: mwh = val * 1000.0
                rows.append({"Pays": nom, "Conso_MWh": mwh})
            return pd.DataFrame(rows)

        custom_data = _collect()
        if custom_data.empty:
            return px.bar(title="Ajoutez des entrées dans la sidebar")

        comparison = (
            custom_data.assign(key=1)
            .merge(dc_paliers.assign(key=1), on="key")
            .drop(columns=["key"])
        )
        comparison["Habitants_equivalents"] = comparison["Conso_MWh_An"] / comparison["Conso_MWh"]
        comparison["DC"] = pd.Categorical(comparison["Nom"], categories=dc_paliers["Nom"], ordered=True)

        max_val = float(comparison["Habitants_equivalents"].max())
        if max_val >= 1e6:
            scale_factor, y_title, hover_suffix = 1e6, "Nombre d'individus équivalents (en millions)", " millions"
        elif max_val >= 1e3:
            scale_factor, y_title, hover_suffix = 1e3, "Nombre d'individus équivalents (en milliers)", " milliers"
        else:
            scale_factor, y_title, hover_suffix = 1, "Nombre d'individus équivalents", ""
        comparison["Habitants_equivalents_scaled"] = comparison["Habitants_equivalents"] / scale_factor

        fig = px.bar(
            comparison, x="DC", y="Habitants_equivalents_scaled", color="Pays",
            title="Nombre d'individus équivalents — projections Data One",
            color_discrete_sequence=["#3B82F6", "#22C55E", "#F59E0B", "#EF4444",
                                    "#8B5CF6", "#06B6D4", "#84CC16", "#F97316"]
        )
        fig.update_layout(legend_title_text="",
                          xaxis_title="Paliers de puissance du Data Center de Eybens",
                          yaxis_title=y_title, barmode="group")
        fig.update_traces(
            hovertemplate="Nom : %{fullData.name}<br>"
                          "Palier : %{x}<br>"
                          "Habitants équivalents : %{y:,.2f}" + hover_suffix + "<extra></extra>"
        )
        return _style_fig(fig, height=420)
