# ====================================================================
# MODULE FLAP-D : Sièges sociaux → Investissements dans les hubs FLAP-D
# ====================================================================

from shiny import reactive, render, ui
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString
import folium
from branca.colormap import linear
import plotly.express as px
import os

# server/donnees/gestionnaire.py
from pathlib import Path


def server(input, output, session, app_dir: Path):

    # =========================================================
    # 1) Chemins et chargement des données (MODULAIRE via app_dir)
    # =========================================================
    data_dir = app_dir / "www" / "data"
    PATH_DC = data_dir / "DC_FLAP_D.geojson"
    PATH_WORLD = data_dir / "world-administrative-boundaries.geojson"

    print("=== DÉMARRAGE MODULE FLAPD ===")
    print("Chargement GeoJSON :", PATH_DC)
    print("Chargement Monde :", PATH_WORLD)

    if not PATH_DC.exists():
        raise FileNotFoundError(f"Fichier manquant : {PATH_DC}")

    if not PATH_WORLD.exists():
        raise FileNotFoundError(f"Fichier manquant : {PATH_WORLD}")

    dc_flapd = gpd.read_file(PATH_DC).to_crs("EPSG:4326")
    world = gpd.read_file(PATH_WORLD).to_crs("EPSG:4326")

    # ==============================================================
    # 1B) CALCUL DU SCORE share_info (0 à 100)
    # ==============================================================

    cols_score = ["area_m2", "capacity_e", "PUE"]
    present = dc_flapd[cols_score].notna().sum(axis=1)
    dc_flapd["share_info"] = (present / len(cols_score)) * 100

    # ==============================================================
    # 2) Harmonisation des noms de pays (pour la jointure)
    # ==============================================================

    COUNTRY_FIX = {
        "USA": "United States of America",
        "UK": "U.K. of Great Britain and Northern Ireland",
    }
    dc_flapd["country_hq"] = dc_flapd["country_hq"].replace(COUNTRY_FIX)

    # ==============================================================
    # 3A) Agrégats : nb et % d'entreprises par hub / pays
    # ==============================================================

    hq_by_hub = (
        dc_flapd.groupby(["city_hub", "country_hq"])
        .agg(
            n_dc=("company", "size"),
            companies=("company", lambda x: ", ".join(sorted(set(x)))),
            share_info_mean=("share_info", "mean"),
        )
        .reset_index()
    )

    # Totaux par hub
    totals = hq_by_hub.groupby("city_hub")["n_dc"].sum().rename("total_dc")
    hq_by_hub = hq_by_hub.merge(totals, on="city_hub", how="left")
    hq_by_hub["pct"] = hq_by_hub["n_dc"] / hq_by_hub["total_dc"] * 100

    hq_by_hub["share_info_mean"] = hq_by_hub["share_info_mean"].round(1)

    # ==============================================================
    # 3B) Statistiques par entreprise
    # ==============================================================

    entreprise_stats = (
        dc_flapd.groupby(["city_hub", "company", "country_hq"])
        .agg(
            n_dc=("name", "count"),
            share_info_mean=("share_info", "mean"),
        )
        .reset_index()
    )

    entreprise_stats["share_info_mean"] = entreprise_stats["share_info_mean"].round(1)

    # ==============================================================
    # 4) Géométries
    # ==============================================================

    hubs_geom = (
        dc_flapd[["city_hub", "geometry"]]
        .dissolve(by="city_hub", as_index=False)
    )
    hubs_geom["hub_centroid"] = hubs_geom.geometry.centroid

    world_centroids = world.copy()
    world_centroids["country_hq"] = world_centroids["name"]
    world_centroids["hq_centroid"] = world_centroids.geometry.centroid

    # Correction Norvège (Oslo)
    mask = world_centroids["country_hq"] == "Norway"
    if mask.any():
        world_centroids.loc[mask, "hq_centroid"] = gpd.points_from_xy(
            [10.75], [59.91], crs="EPSG:4326"
        )

    # ==============================================================
    # 5) Flux
    # ==============================================================

    flows_records = []
    for _, row in hq_by_hub.iterrows():

        city = row["city_hub"]
        country = row["country_hq"]

        hq_row = world_centroids[world_centroids["country_hq"] == country]
        hub_row = hubs_geom[hubs_geom["city_hub"] == city]

        if hq_row.empty or hub_row.empty:
            continue

        hq_pt = hq_row["hq_centroid"].iloc[0]
        hub_pt = hub_row["hub_centroid"].iloc[0]

        flows_records.append(
            {
                "city_hub": city,
                "country_hq": country,
                "n_dc": row["n_dc"],
                "geometry": LineString([(hq_pt.x, hq_pt.y), (hub_pt.x, hub_pt.y)]),
            }
        )

    flows_gdf = gpd.GeoDataFrame(flows_records, crs="EPSG:4326")

    # ==============================================================
    # 6) Vues par hub
    # ==============================================================

    HUB_VIEWS = {
        row["city_hub"]: {
            "location": [row["hub_centroid"].y, row["hub_centroid"].x],
            "zoom": 4,
        }
        for _, row in hubs_geom.iterrows()
    }

    # ==============================================================
    # 7) Colormap (%)
    # ==============================================================

    COLORMAP = linear.Blues_09.scale(0, 100)
    COLORMAP.caption = "Part (%) des entreprises du hub"

    # ==============================================================
    # 8) Génération de la carte
    # ==============================================================

    def make_map(hub: str | None) -> ui.HTML:
        """
        - hub=None  -> vue globale : tous les hubs, cliquables
        - hub=str   -> vue hub : choropleth + flux + HQ + hubs toujours visibles
        NOTE:
        - Rendu via m._repr_html_() (folium embed en iframe) => affichage garanti.
        - Clic hub: window.parent.postMessage(...) depuis l'iframe,
          puis un script global côté UI transforme ça en input Shiny hub_click.
        - Les hubs sont dessinés EN DERNIER => toujours au-dessus des polygones.
        """

        # --- Carte de base (centrée sur les hubs) ---
        hubs_lat = hubs_geom["hub_centroid"].y
        hubs_lon = hubs_geom["hub_centroid"].x

        m = folium.Map(
            location=[float(hubs_lat.mean()), float(hubs_lon.mean())],
            zoom_start=3,
            tiles="CartoDB positron",
        )

        # --- JS: bind click marker -> postMessage au parent ---
        def _bind_click(marker_name: str, hub_name: str) -> str:
            hub_name_js = hub_name.replace("\\", "\\\\").replace("'", "\\'")
            return f"""
            <script>
            (function() {{
                function bind() {{
                    try {{
                        var mk = {marker_name};
                        if (!mk || !mk.on) {{
                            setTimeout(bind, 50);
                            return;
                        }}
                        mk.on('click', function() {{
                            if (window.parent && window.parent.postMessage) {{
                                window.parent.postMessage({{ type: 'hub_click', hub: '{hub_name_js}' }}, '*');
                            }}
                        }});
                    }} catch(e) {{
                        setTimeout(bind, 50);
                    }}
                }}
                bind();
            }})();
            </script>
            """

        # --- Légende ---
        def add_legend(map_obj: folium.Map, mode: str, hub_name: str | None = None):
            """
            mode:
              - "global" : seulement hubs
              - "hub"    : hubs + HQ
            """
            if mode == "global":
                legend_html = """
                <div style="
                    position: fixed;
                    bottom: 18px;
                    left: 18px;
                    z-index: 9999;
                    background: rgba(255,255,255,0.50);
                    border: 1px solid rgba(0,0,0,0.15);
                    border-radius: 10px;
                    padding: 10px 12px;
                    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
                    font-size: 13px;
                    line-height: 1.35;
                    ">
                  <div style="font-weight:700; margin-bottom:6px;">Légende</div>

                  <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                    <span style="width:10px;height:10px;border-radius:50%;
                      display:inline-block;background:rgba(220,0,0,0.35);
                      border:2px solid rgba(220,0,0,0.9);"></span>
                    Hubs FLAP-D
                  </div>
                </div>
                """
            else:
                hub_label = f" ({hub_name})" if hub_name else ""
                legend_html = f"""
                <div style="
                    position: fixed;
                    bottom: 18px;
                    left: 18px;
                    z-index: 9999;
                    background: rgba(255,255,255,0.50);
                    border: 1px solid rgba(0,0,0,0.15);
                    border-radius: 10px;
                    padding: 10px 12px;
                    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
                    font-size: 13px;
                    line-height: 1.35;
                    ">
                  <div style="font-weight:700; margin-bottom:6px;">Légende</div>

                  <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                    <span style="width:12px;height:12px;border-radius:50%;
                      display:inline-block;background:rgba(220,0,0,0.95);
                      border:2px solid rgba(220,0,0,1);"></span>
                    Hub sélectionné{hub_label}
                  </div>

                  <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                    <span style="width:10px;height:10px;border-radius:50%;
                      display:inline-block;background:rgba(220,0,0,0.35);
                      border:2px solid rgba(220,0,0,0.9);"></span>
                    Autres hubs
                  </div>

                  <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                    <span style="width:10px;height:10px;border-radius:50%;
                      display:inline-block;background:rgba(102,102,102,0.9);
                      border:2px solid rgba(102,102,102,1);"></span>
                    Pays sièges
                  </div>
                </div>
                """

            map_obj.get_root().html.add_child(folium.Element(legend_html))

        # --- Hubs au-dessus ---
        def add_hubs_on_top(map_obj: folium.Map, selected_hub: str | None):
            for _, r in hubs_geom.iterrows():
                hub_name = r["city_hub"]
                pt = r["hub_centroid"]

                is_selected = (selected_hub is not None and hub_name == selected_hub)

                marker = folium.CircleMarker(
                    location=[pt.y, pt.x],
                    radius=11 if is_selected else 8,
                    color="rgba(220,0,0,1)" if is_selected else "rgba(220,0,0,0.9)",
                    fill=True,
                    fill_color="rgba(220,0,0,1)" if is_selected else "rgba(220,0,0,0.9)",
                    fill_opacity=0.95 if is_selected else 0.35,
                    opacity=1.0 if is_selected else 0.9,
                    tooltip=f"Hub : {hub_name} (cliquer)",
                )
                marker.add_to(map_obj)

                # Bind clic (toggle géré côté serveur)
                map_obj.get_root().html.add_child(
                    folium.Element(_bind_click(marker.get_name(), hub_name))
                )

        # VUE GLOBALE
        if hub is None or hub == "":
            min_lat, max_lat = float(hubs_lat.min()), float(hubs_lat.max())
            min_lon, max_lon = float(hubs_lon.min()), float(hubs_lon.max())
            m.fit_bounds([[min_lat, min_lon], [max_lat, max_lon]])

            add_hubs_on_top(m, selected_hub=None)
            add_legend(m, mode="global")

            html = m._repr_html_().replace(
                "width:100.0%;height:100.0%;",
                "width:100%;height:100%;"
            )
            return ui.HTML(html)

        # VUE HUB SÉLECTIONNÉ
        data_hq = hq_by_hub[hq_by_hub["city_hub"] == hub].copy()
        data_flows = flows_gdf[flows_gdf["city_hub"] == hub].copy()

        world_merged = world.merge(
            data_hq,
            left_on="name",
            right_on="country_hq",
            how="left",
        )
        world_tooltip = world_merged[world_merged["pct"].notnull()]

        def style(f):
            pct = f["properties"].get("pct", None)
            if pct is None:
                return {"fillOpacity": 0, "color": "#888", "weight": 0.5}
            return {
                "fillColor": COLORMAP(pct),
                "fillOpacity": 0.85,
                "color": "#555",
                "weight": 0.6,
            }

        # 1) Polygones
        folium.GeoJson(
            world_tooltip,
            style_function=style,
            tooltip=folium.GeoJsonTooltip(
                fields=["name", "pct", "n_dc"],
                aliases=["Pays", "% du hub", "Nb DC"],
                localize=True,
            ),
        ).add_to(m)

        # 2) Flux
        folium.GeoJson(
            data_flows,
            style_function=lambda f: {
                "color": "#333",
                "weight": 1 + (f["properties"]["n_dc"] ** 0.5),
                "opacity": 0.7,
            },
        ).add_to(m)

        # 3) Points HQ (départs)
        for _, rr in data_flows.iterrows():
            x, y = rr.geometry.coords[0]
            folium.CircleMarker(
                [y, x],
                radius=5,
                color="#666",
                fill=True,
                fill_color="#666",
                fill_opacity=0.9,
                opacity=1.0,
            ).add_to(m)

        COLORMAP.add_to(m)

        # 4) Recentrage
        if not data_flows.empty:
            xs, ys = [], []
            for _, rr in data_flows.iterrows():
                (x0, y0), (x1, y1) = list(rr.geometry.coords)
                xs.extend([x0, x1])
                ys.extend([y0, y1])
            m.fit_bounds([[min(ys), min(xs)], [max(ys), max(xs)]])

        # 5) Hubs au-dessus + légende
        add_hubs_on_top(m, selected_hub=hub)
        add_legend(m, mode="hub", hub_name=hub)

        html = m._repr_html_().replace(
            "width:100.0%;height:100.0%;",
            "width:100%;height:100%;"
        )
        return ui.HTML(html)

    # ==============================================================
    # 9) TOP 5 ENTREPRISES
    # ==============================================================

    def make_top5_table(hub: str) -> pd.DataFrame:
        """Retourne les 5 entreprises principales du hub avec DC + score share_info."""
        df = entreprise_stats[entreprise_stats["city_hub"] == hub].copy()

        if df.empty:
            return pd.DataFrame(
                columns=["Entreprise", "Pays du siège", "Nombre de DC", "Score moyen share_info (%)"]
            )

        df = df.sort_values("n_dc", ascending=False).head(5)

        if df["share_info_mean"].max() <= 1:
            df["share_info_mean"] = df["share_info_mean"] * 100

        df["share_info_mean"] = df["share_info_mean"].round(1)

        df = df.rename(
            columns={
                "company": "Entreprise",
                "country_hq": "Pays du siège",
                "n_dc": "Nombre de DC",
                "share_info_mean": "Score moyen share_info (%)",
            }
        )

        return df[["Entreprise", "Pays du siège", "Nombre de DC", "Score moyen share_info (%)"]]

    # ==============================================================
    # 10) TREEMAP
    # ==============================================================

    def make_treemap(hub: str) -> ui.HTML:
        """Treemap des parts de pays pour un hub (basé sur % du hub)."""

        df = hq_by_hub[hq_by_hub["city_hub"] == hub].copy()

        if df.empty:
            return ui.HTML("<p>Aucune donnée pour ce hub.</p>")

        df = df[df["pct"].notna()].copy()
        if df.empty:
            return ui.HTML("<p>Aucune donnée exploitable pour ce hub.</p>")

        df["pct"] = df["pct"].round(1)
        df["label_country"] = df["country_hq"] + " (" + df["pct"].astype(str) + "%)"

        fig = px.treemap(
            df,
            path=["label_country"],
            values="pct",
            color="pct",
            color_continuous_scale="Blues",
            title=f"Répartition des entreprises (% par pays) — {hub}",
        )

        fig.update_traces(
            texttemplate="%{label}",
            textfont_size=14,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Part du hub : %{value:.1f}%<br>"
                "Nombre de DC : %{customdata[1]}<extra></extra>"
            ),
            customdata=df[["country_hq", "n_dc"]].to_numpy(),
        )

        fig.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            coloraxis_showscale=False,
        )

        html = fig.to_html(full_html=False, include_plotlyjs="cdn")
        return ui.HTML(html)

    # ==============================================================
    # 11) MODULE SERVER EXPORTÉ
    # ==============================================================

    def module_gestionnaire_dc(input, output, session):

        selected_hub = reactive.Value(None)

        @reactive.effect
        @reactive.event(input.hub_click)
        def _hub_click():
            clicked = input.hub_click()
            if clicked is None or clicked == "":
                return

            current = selected_hub()
            # toggle: re-clic sur le hub actif => retour vue globale
            if current == clicked:
                selected_hub.set(None)
            else:
                selected_hub.set(clicked)

        # --- Boutons
        def _bind_button(btn_id: str, hub_name: str):
            @reactive.effect
            @reactive.event(getattr(input, btn_id))
            def _set_hub():
                selected_hub.set(hub_name)

        for hub_btn, hub_name in [
            ("hq_go_frankfurt", "Frankfurt am Main"),
            ("hq_go_london", "London"),
            ("hq_go_amsterdam", "Amsterdam"),
            ("hq_go_paris", "Paris"),
            ("hq_go_dublin", "Dublin"),
        ]:
            _bind_button(hub_btn, hub_name)

        # --- UI Boutons dynamiques
        @render.ui
        def hub_buttons():
            hub = selected_hub()

            def active(h):
                return "btn-hub-active" if h == hub else ""

            return ui.div(
                {
                    "style": (
                        "position: sticky;"
                        "top: 90px;"
                        "z-index: 5;"
                        "background: var(--card);"
                        "padding: 10px;"
                        "border-radius: 10px;"
                        "box-shadow: 0 4px 12px rgba(0,0,0,0.08);"
                    )
                },
                ui.input_action_button(
                    "hq_go_frankfurt",
                    "🇩🇪 Frankfurt",
                    class_=f"btn btn-outline-primary w-100 mb-2 {active('Frankfurt am Main')}",
                ),
                ui.input_action_button(
                    "hq_go_london",
                    "🇬🇧 London",
                    class_=f"btn btn-outline-primary w-100 mb-2 {active('London')}",
                ),
                ui.input_action_button(
                    "hq_go_amsterdam",
                    "🇳🇱 Amsterdam",
                    class_=f"btn btn-outline-primary w-100 mb-2 {active('Amsterdam')}",
                ),
                ui.input_action_button(
                    "hq_go_paris",
                    "🇫🇷 Paris",
                    class_=f"btn btn-outline-primary w-100 mb-2 {active('Paris')}",
                ),
                ui.input_action_button(
                    "hq_go_dublin",
                    "🇮🇪 Dublin",
                    class_=f"btn btn-outline-primary w-100 {active('Dublin')}",
                ),
            )

        output.hub_buttons = hub_buttons

        # Titre dynamique
        @render.text
        def titre_carte_hq():
            hub = selected_hub()
            if hub is None:
                return "Carte des hubs FLAP-D"
            return f"Carte des pays d’origine des entreprises pour le hub de {hub}"

        output.titre_carte_hq = titre_carte_hq

        # Carte
        @render.ui
        def map_hq_flapd():
            return make_map(selected_hub())

        output.map_hq_flapd = map_hq_flapd

        # Titre TOP 5
        @render.text
        def titre_top5():
            hub = selected_hub()
            if hub is None:
                return "Top 5 entreprises — sélectionner un hub"
            return f"Top 5 entreprises opérant dans le hub de {hub}"

        output.titre_top5 = titre_top5

        # Tableau TOP 5
        @render.data_frame
        def top5_table():
            hub = selected_hub()
            if hub is None:
                return pd.DataFrame(
                    columns=["Entreprise", "Pays du siège", "Nombre de DC", "Score moyen share_info (%)"]
                )
            return make_top5_table(hub)

        output.top5_table = top5_table

        # Treemap
        @render.ui
        def treemap_hq():
            hub = selected_hub()
            if hub is None:
                return ui.HTML("<p>Cliquer sur un hub sur la carte pour afficher le treemap.</p>")
            return make_treemap(hub)

        output.treemap_hq = treemap_hq

        # Commentaire / interprétation de la carte
        @render.ui
        def commentaire_carte_hq():
            hub = selected_hub()

            if hub is None:
                return ui.HTML("Cliquez sur un <strong>hub</strong> pour afficher les <strong>pays sièges</strong> et les <strong>flux</strong> associés.")

            df = hq_by_hub[hq_by_hub["city_hub"] == hub]  # retirez les indications quand aucun hub sélectionnez ca fait trop
            # Pensez à mettre un break
            if df.empty:
                return ui.HTML(f"Aucune donnée disponible pour le hub de <strong>{hub}</strong>.")

            total_pays = df["country_hq"].nunique()
            top = df.sort_values("pct", ascending=False).head(1)
            pays_top = top["country_hq"].iloc[0]
            pct_top = round(top["pct"].iloc[0], 1)

            return ui.HTML(
                f"Pour le hub de <strong>{hub}</strong>, les flux proviennent de <strong>{total_pays}</strong> pays. "
                f"Le pays le plus représenté est <strong>{pays_top}</strong>, qui concentre environ <strong>{pct_top}%</strong> "
                f"des data centers reliés à ce hub. Les <strong>flèches</strong> indiquent le sens de la connexion, "
                f"depuis le <strong>pays siège</strong> vers la <strong>ville du hub</strong>."
            )

        output.commentaire_carte_hq = commentaire_carte_hq

        # Commentaire / interprétation du TOP 5
        @render.ui
        def commentaire_top5_hq():
            hub = selected_hub()

            if hub is None:
                return ui.HTML("Sélectionnez un <strong>hub</strong> pour afficher le <strong>Top 5</strong> des entreprises.")

            df_top5 = make_top5_table(hub)
            if df_top5.empty:
                return ui.HTML(f"Aucune entreprise n’est référencée pour le hub de <strong>{hub}</strong>.")

            entreprise_1 = df_top5.iloc[0]["Entreprise"]
            pays_1 = df_top5.iloc[0]["Pays du siège"]
            n_dc_1 = int(df_top5.iloc[0]["Nombre de DC"])

            return ui.HTML(
                f"Ce tableau présente les <strong>5 entreprises</strong> les plus présentes dans le hub de <strong>{hub}</strong>. "
                f"L’acteur principal est <strong>{entreprise_1}</strong> (<strong>{pays_1}</strong>), avec <strong>{n_dc_1}</strong> data centers "
                f"dans ce hub. Les <strong>scores share_info</strong> permettent de comparer les niveaux de <strong>transparence</strong> entre entreprises."
            )

        output.commentaire_top5_hq = commentaire_top5_hq

        # Commentaire / interprétation du treemap
        @render.ui
        def commentaire_treemap_hq():
            hub = selected_hub()

            if hub is None:
                return ui.HTML("Sélectionnez un <strong>hub</strong> pour afficher la <strong>répartition</strong> des pays dans le treemap.")

            df = hq_by_hub[hq_by_hub["city_hub"] == hub]
            if df.empty:
                return ui.HTML(f"Aucune donnée disponible pour le hub de <strong>{hub}</strong>.")

            total_pays = df["country_hq"].nunique()
            top3 = df.sort_values("pct", ascending=False).head(3)
            parts = [f"{r['country_hq']} (~{r['pct']:.1f}%)" for _, r in top3.iterrows()]
            top_str = ", ".join(parts)

            return ui.HTML(
                f"Le treemap montre la <strong>répartition</strong> des parts de pays dans le hub de <strong>{hub}</strong>. "
                f"Au total, <strong>{total_pays}</strong> pays sont représentés. Les principaux contributeurs sont : <strong>{top_str}</strong>. "
                f"Cliquer sur un pays permet de <strong>zoomer</strong> et d’explorer plus finement sa contribution."
            )

        output.commentaire_treemap_hq = commentaire_treemap_hq

    # IMPORTANT : on exécute le module serveur ici
    module_gestionnaire_dc(input, output, session)
