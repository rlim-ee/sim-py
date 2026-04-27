# server/energie/flapd.py — carte des data centers FLAP-D site par site
#
# Ce module répond à la question : "où se trouvent physiquement les data centers
# dans les cinq hubs européens (Paris, Londres, Amsterdam, Francfort, Dublin) ?"
#
# Il produit deux outputs :
#   - map_flapd_sites  → carte Folium interactive des sites DC
#   - encarts_villes   → tableau de synthèse par hub (surface, puissance, PUE…)
#
# L'utilisateur sélectionne un hub via des boutons (go_paris, go_london…).
# La carte change pour afficher soit tous les DC (vue globale avec clustering),
# soit les DC d'un seul hub (vue détaillée avec cercles colorés selon la puissance).
#
# Le "jitter stable" décale légèrement les points qui se superposent
# (plusieurs DC au même endroit) de manière reproductible.
from __future__ import annotations

from shiny import reactive, render, ui
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import FastMarkerCluster
from branca.colormap import linear
import numpy as np
from pathlib import Path
import sys

from server._common import is_dark, cached, stable_jitter


# Coordonnées géographiques des cinq hubs FLAP-D
# Servent à affecter automatiquement chaque DC au hub le plus proche
HUB_CENTERS = {
    "Paris":     (48.8566, 2.3522),
    "Londres":   (51.5074, -0.1278),
    "Amsterdam": (52.3676, 4.9041),
    "Francfort": (50.1109, 8.6821),
    "Dublin":    (53.3498, -6.2603),
}


# =====================================================================
# Chargement du GeoJSON brut (partagé avec server/donnees/gestionnaire.py)
# =====================================================================
def _load_dc_flapd_raw(app_dir: Path) -> gpd.GeoDataFrame:
    path = app_dir / "www" / "data" / "DC_FLAP_D.geojson"
    if not path.exists():
        raise FileNotFoundError(f"GeoJSON introuvable : {path}")
    return gpd.read_file(path).to_crs("EPSG:4326")


def get_dc_flapd_raw(app_dir: Path) -> gpd.GeoDataFrame:
    """Cache du GeoJSON brut — partageable entre modules sans double lecture."""
    key = f"dc_flapd_raw::{(app_dir / 'www' / 'data' / 'DC_FLAP_D.geojson').resolve()}"
    return cached(key, lambda: _load_dc_flapd_raw(app_dir))


def _prepare_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Enrichit le GeoDataFrame brut avec :
    - l'affectation au hub le plus proche (city_hub_auto)
    - un décalage de position stable pour éviter la superposition des points
    """
    gdf = gdf.copy()

    gdf["capacity_e"] = pd.to_numeric(gdf.get("capacity_e"), errors="coerce")
    gdf["area_m2"]    = pd.to_numeric(gdf.get("area_m2"),    errors="coerce")

    # Affectation vectorisée au hub le plus proche (distance euclidienne en degrés)
    hub_names  = np.array(list(HUB_CENTERS.keys()))
    hub_coords = np.array(list(HUB_CENTERS.values()))

    pts  = gdf[["latitude", "longitude"]].to_numpy()
    dlat = pts[:, 0][:, None] - hub_coords[:, 0][None, :]
    dlon = pts[:, 1][:, None] - hub_coords[:, 1][None, :]
    dists = np.sqrt(dlat**2 + dlon**2)

    closest_idx = np.argmin(dists, axis=1)
    gdf["city_hub_auto"] = hub_names[closest_idx]

    # Jitter stable : même nom → même décalage (reproductible d'un rechargement à l'autre)
    seed_col = gdf["name"] if "name" in gdf.columns else gdf.index.astype(str)
    gdf["lat_jit"] = gdf["latitude"]  + seed_col.map(lambda s: stable_jitter(s))
    gdf["lon_jit"] = gdf["longitude"] + seed_col.map(lambda s: stable_jitter(f"lon::{s}"))

    return gdf


def _get_prepared_gdf(app_dir: Path) -> gpd.GeoDataFrame:
    """Cache de la version préparée (hub auto + jitter stable)."""
    key = f"flapd::prepared::{Path(app_dir).resolve()}"
    return cached(key, lambda: _prepare_gdf(get_dc_flapd_raw(app_dir)))


# =====================================================================
# Construction des cartes Folium
# =====================================================================
def _build_map_all(df: pd.DataFrame, dark: bool) -> str:
    """
    Vue globale : tous les DC regroupés en clusters cliquables.
    FastMarkerCluster regroupe automatiquement les marqueurs proches
    pour éviter une carte illisible avec des centaines de points.
    """
    tiles = "cartodbdark_matter" if dark else "cartodbpositron"
    m = folium.Map(location=[51, 5], zoom_start=5, tiles=tiles)

    coords = df[["latitude", "longitude"]].to_numpy().tolist()
    FastMarkerCluster(data=coords).add_to(m)

    return m._repr_html_()


def _build_map_hub(df: pd.DataFrame, dark: bool) -> str:
    """
    Vue par hub : cercles colorés selon la puissance électrique (MW),
    et de taille proportionnelle à la surface (m²).
    Un pop-up s'affiche au clic sur chaque DC.
    """
    tiles = "cartodbdark_matter" if dark else "cartodbpositron"

    # Gamme de couleur : blanc/rose → rouge foncé selon la puissance
    vals = df["capacity_e"].astype(float).dropna()
    if len(vals) == 0:
        vmin, vmax = 0.0, 1.0
    else:
        vmin, vmax = float(vals.min()), float(vals.max())
        if vmin == vmax:
            vmin -= 0.5
            vmax += 0.5

    pal = linear.Reds_09.scale(vmin, vmax)
    pal.caption = "Puissance (MW)"

    m = folium.Map(
        location=[df["latitude"].mean(), df["longitude"].mean()],
        zoom_start=11,
        tiles=tiles,
    )

    surf = df["area_m2"].astype(float).dropna()
    if len(surf) == 0:
        small = med = large = 0
    else:
        small = int(np.percentile(surf, 25))
        med   = int(np.percentile(surf, 50))
        large = int(np.percentile(surf, 75))

    surf_min = float(surf.min()) if len(surf) else 0.0
    surf_max = float(surf.max()) if len(surf) else 1.0
    col = "white" if dark else "black"

    for _, r in df.iterrows():
        cap = float(r["capacity_e"]) if pd.notna(r["capacity_e"]) else 0.0
        ar  = float(r["area_m2"])    if pd.notna(r["area_m2"])    else 10.0

        popup = (
            f"<b>{r.get('name','')}</b><br>"
            f"Surface : {ar:,.0f} m²<br>"
            f"Capacité : {cap:.1f} MW<br>"
            f"Entreprise : {r.get('company','')}"
        )

        if len(surf) > 1:
            r_marker = float(np.interp(ar, (surf_min, surf_max), (8, 22)))
            r_base   = float(np.interp(ar, (surf_min, surf_max), (50, 250)))
        else:
            r_marker, r_base = 10.0, 100.0

        # Cercle principal : couleur = puissance, taille = surface
        folium.CircleMarker(
            [r["lat_jit"], r["lon_jit"]],
            radius=r_marker,
            color=col, fill=True, fill_color=pal(cap),
            fill_opacity=0.9, weight=1,
            popup=popup,
        ).add_to(m)

        # Halo transparent pour visualiser l'emprise au sol approximative
        folium.Circle(
            [r["lat_jit"], r["lon_jit"]],
            radius=r_base,
            color=col, fill=False, opacity=0.07,
        ).add_to(m)

    # Légende des surfaces (quartiles) injectée comme HTML dans la carte
    bg  = "rgba(20,20,20,0.85)" if dark else "rgba(255,255,255,0.9)"
    txt = "#fff" if dark else "#111"
    st  = "#fff" if dark else "#000"

    legend = f"""
    <div style="position: fixed; bottom: 35px; right: 25px;
        background: {bg}; color:{txt};
        padding:12px; border-radius:10px;
        z-index:9999; font-size:13px;">
        <b>Surfaces typiques (m²)</b><br>
        <svg width="170" height="110">
            <circle cx="25" cy="20" r="6" stroke="{st}" fill="none"/>
            <text x="50" y="24" fill="{txt}" font-size="12">≈ {small:,} m²</text>
            <circle cx="25" cy="50" r="10" stroke="{st}" fill="none"/>
            <text x="50" y="54" fill="{txt}" font-size="12">≈ {med:,} m²</text>
            <circle cx="25" cy="85" r="14" stroke="{st}" fill="none"/>
            <text x="50" y="89" fill="{txt}" font-size="12">≈ {large:,} m²</text>
        </svg>
    </div>
    """

    m.get_root().html.add_child(folium.Element(legend))
    pal.add_to(m)

    return m._repr_html_()


# =====================================================================
# Logique serveur de la carte FLAP-D
# =====================================================================
def carte_flapd_server(input, output, session, gdf: gpd.GeoDataFrame):
    # La ville sélectionnée par les boutons : "All" = vue globale
    selected_ville = reactive.Value("All")

    # Chaque bouton de hub change la valeur réactive selected_ville,
    # ce qui déclenche automatiquement le re-rendu de map_flapd_sites.
    @reactive.effect
    @reactive.event(input.go_paris)
    def _go_paris():
        selected_ville.set("Paris")

    @reactive.effect
    @reactive.event(input.go_london)
    def _go_london():
        selected_ville.set("Londres")

    @reactive.effect
    @reactive.event(input.go_amsterdam)
    def _go_amsterdam():
        selected_ville.set("Amsterdam")

    @reactive.effect
    @reactive.event(input.go_frankfurt)
    def _go_frankfurt():
        selected_ville.set("Francfort")

    @reactive.effect
    @reactive.event(input.go_dublin)
    def _go_dublin():
        selected_ville.set("Dublin")

    @reactive.effect
    @reactive.event(input.reset_vue)
    def _reset():
        selected_ville.set("All")

    # Cache local par (ville, thème) pour ne pas reconstruire la carte Folium
    # à chaque fois que l'utilisateur revient sur le même hub.
    _map_cache: dict[tuple[str, bool], str] = {}

    @output
    @render.ui
    def map_flapd_sites():
        city = selected_ville()
        dark = is_dark(input)

        ck = (city, dark)
        html = _map_cache.get(ck)
        if html is not None:
            return ui.div(ui.HTML(html), class_="map-wrap")

        if city == "All":
            html = _build_map_all(gdf, dark)
            _map_cache[ck] = html
            return ui.div(ui.HTML(html), class_="map-wrap")

        df = gdf[gdf["city_hub_auto"] == city]
        if df.empty:
            return ui.div(f"Aucun DC trouvé pour {city}")

        html = _build_map_hub(df, dark)
        _map_cache[ck] = html
        return ui.div(ui.HTML(html), class_="map-wrap")

    # Tableau de synthèse par hub : surface, puissance, PUE
    # Les pastilles de couleur indiquent la complétude des données (bleu = bonne couverture)
    @output
    @render.ui
    def encarts_villes():
        hubs = ["Paris", "Londres", "Amsterdam", "Francfort", "Dublin"]
        drapeaux = {
            "Paris": "🇫🇷", "Londres": "🇬🇧", "Amsterdam": "🇳🇱",
            "Francfort": "🇩🇪", "Dublin": "🇮🇪",
        }

        df = (
            gdf[gdf["city_hub_auto"].isin(hubs)]
            .groupby("city_hub_auto")
            .agg(
                nb_dc=("name", "count"),
                surface_moy=("area_m2", "mean"),
                surface_tot=("area_m2", "sum"),
                puissance_moy=("capacity_e", "mean"),
                puissance_med=("capacity_e", "median"),
                pue_moy=("PUE", "mean"),
                share_area=("area_m2", lambda x: x.notna().mean() * 100),
                share_capacity=("capacity_e", lambda x: x.notna().mean() * 100),
                share_pue=("PUE", lambda x: x.notna().mean() * 100),
            )
            .reset_index()
        )

        def dot_color(p):
            if pd.isna(p):   return "gray"
            if p < 30:       return "#d9534f"
            if p < 60:       return "#f0ad4e"
            return "#0275d8"

        def dot(p):
            return f"<span style='color:{dot_color(p)};font-size:18px;margin-left:4px;'>●</span>"

        def fmt(x, d=2):
            if pd.isna(x): return "-"
            return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")

        df["Hub"] = df["city_hub_auto"].apply(lambda x: f"{drapeaux.get(x,'')} {x}")
        df["Nombre de DC recensés"] = df["nb_dc"]

        df["Surface moyenne (m²)"] = df.apply(
            lambda r: f"{fmt(r['surface_moy'],0)} {dot(r['share_area'])}", axis=1
        )
        df["Surface totale (m²)"] = df["surface_tot"].apply(lambda x: fmt(x, 0))

        df["Puissance moyenne (MW)"] = df.apply(
            lambda r: f"{fmt(r['puissance_moy'],2)} {dot(r['share_capacity'])}", axis=1
        )
        df["Puissance médiane (MW)"] = df.apply(
            lambda r: f"{fmt(r['puissance_med'],2)} {dot(r['share_capacity'])}", axis=1
        )
        df["PUE moyen"] = df.apply(
            lambda r: f"{fmt(r['pue_moy'],2)} {dot(r['share_pue'])}", axis=1
        )

        rows_html = "".join(
            [
                f"""
            <tr>
                <td>{r['Hub']}</td>
                <td>{r['Nombre de DC recensés']}</td>
                <td>{r['Surface moyenne (m²)']}</td>
                <td>{r['Surface totale (m²)']}</td>
                <td>{r['Puissance moyenne (MW)']}</td>
                <td>{r['Puissance médiane (MW)']}</td>
                <td>{r['PUE moyen']}</td>
            </tr>
            """
                for _, r in df.iterrows()
            ]
        )

        # Le tableau intègre du JavaScript pour pouvoir être trié au clic
        table_html = f"""
        <style>
        th.sortable {{
            cursor: pointer;
            user-select: none;
        }}
        th.sortable:hover {{
            background: rgba(148,163,184,0.26) !important;
        }}
        th.sortable .sort-icon {{
            margin-left: 6px;
            font-size: 12px;
            opacity: .7;
        }}
        table.table-synthese td {{
            vertical-align: middle;
        }}
        </style>

        <table id="syntheseTable" class="table-synthese" style="width:100%">
            <thead>
                <tr>
                    <th onclick="sortTable(0)" class="sortable">Hub <span class="sort-icon"></span></th>
                    <th onclick="sortTable(1)" class="sortable">Nombre de DC recensés <span class="sort-icon"></span></th>
                    <th onclick="sortTable(2)" class="sortable">Surface moyenne (m²) <span class="sort-icon"></span></th>
                    <th onclick="sortTable(3)" class="sortable">Surface totale (m²) <span class="sort-icon"></span></th>
                    <th onclick="sortTable(4)" class="sortable">Puissance moyenne (MW) <span class="sort-icon"></span></th>
                    <th onclick="sortTable(5)" class="sortable">Puissance médiane (MW) <span class="sort-icon"></span></th>
                    <th onclick="sortTable(6)" class="sortable">PUE moyen <span class="sort-icon"></span></th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <script>
        var sortDirections = {{}};
        function sortTable(colIndex) {{
            var table = document.getElementById("syntheseTable");
            var rows = Array.from(table.rows).slice(1);
            var dir = sortDirections[colIndex] === "asc" ? "desc" : "asc";
            sortDirections[colIndex] = dir;

            document.querySelectorAll("#syntheseTable th .sort-icon").forEach(function(el) {{
                el.textContent = "";
            }});
            var iconCell = table.tHead.rows[0].cells[colIndex].querySelector(".sort-icon");
            if (iconCell) {{
                iconCell.textContent = dir === "asc" ? "▲" : "▼";
            }}

            rows.sort(function(a, b) {{
                var A = a.cells[colIndex].innerText
                    .replace(/●/g,"")
                    .replace(/\\s/g,"")
                    .replace(/,/g,".")
                    .trim();
                var B = b.cells[colIndex].innerText
                    .replace(/●/g,"")
                    .replace(/\\s/g,"")
                    .replace(/,/g,".")
                    .trim();

                var nA = parseFloat(A), nB = parseFloat(B);
                if (!isNaN(nA) && !isNaN(nB)) {{
                    return dir === "asc" ? nA - nB : nB - nA;
                }}
                return dir === "asc" ? A.localeCompare(B) : B.localeCompare(A);
            }});

            rows.forEach(function(r) {{
                table.tBodies[0].appendChild(r);
            }});
        }}
        </script>

        <div style="text-align:center; margin-top:10px; font-size:14px; color:#555;">
            <b>Légende des pastilles :</b><br>
            <span style='color:#0275d8;font-size:16px'>●</span> Informations complètes (≥ 60%) &nbsp;|&nbsp;
            <span style='color:#f0ad4e;font-size:16px'>●</span> Informations partielles (30–60%) &nbsp;|&nbsp;
            <span style='color:#d9534f;font-size:16px'>●</span> Informations limitées (&lt; 30%)
        </div>

        <div style="text-align:center; margin-top:8px; font-size:13px; color:#666;">
            Données collectées depuis
            <a href="https://www.datacentermap.com/" target="_blank" rel="noopener noreferrer">
              <b>DataCenterMap</b>
            </a> (avril 2025).
        </div>
        """

        titre = ui.h4(ui.HTML("<i class='fa-solid fa-chart-column interp-inline-icon me-2'></i>Synthèse par hub"), class_="titre-synthese")

        return ui.div(
            ui.div(titre, class_="text-center mt-3"),
            ui.HTML(table_html),
            class_="container-fluid mt-3",
        )


# =====================================================================
# Wrapper attendu par server/energie/__init__.py
# =====================================================================
def server(input, output, session, app_dir: Path):
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    gdf = _get_prepared_gdf(app_dir)

    return carte_flapd_server(input, output, session, gdf)
