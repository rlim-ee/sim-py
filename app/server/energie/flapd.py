# server/energie/flapd.py — MODULE SERVEUR FLAP-D
from __future__ import annotations

from shiny import reactive, render, ui
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from branca.colormap import linear
import numpy as np
import random
from pathlib import Path
import sys


# === DARK MODE DETECTOR (basé sur l'input "darkmode") ===
def _is_dark(input) -> bool:
    """Retourne True si le dark mode est actif côté UI (sécurisé)."""
    try:
        dm = getattr(input, "darkmode", None)
        return bool(dm()) if callable(dm) else False
    except Exception:
        return False


# === 2) Fonction anti-superposition ===
def jitter(val, amplitude=0.002):
    return val + random.uniform(-amplitude, amplitude)


# === Centres des hubs ===
HUB_CENTERS = {
    "Paris": (48.8566, 2.3522),
    "London": (51.5074, -0.1278),
    "Amsterdam": (52.3676, 4.9041),
    "Frankfurt am Main": (50.1109, 8.6821),
    "Dublin": (53.3498, -6.2603),
}


def _prepare_gdf(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Nettoyage + hub auto (vectorisé)"""
    gdf = gdf.copy()

    # conversions robustes
    gdf["capacity_e"] = pd.to_numeric(gdf.get("capacity_e"), errors="coerce")
    gdf["area_m2"] = pd.to_numeric(gdf.get("area_m2"), errors="coerce")

    # hub auto vectorisé
    hub_names = np.array(list(HUB_CENTERS.keys()))
    hub_coords = np.array(list(HUB_CENTERS.values()))  # (n,2) lat/lon

    pts = gdf[["latitude", "longitude"]].to_numpy()
    dlat = pts[:, 0][:, None] - hub_coords[:, 0][None, :]
    dlon = pts[:, 1][:, None] - hub_coords[:, 1][None, :]
    dists = np.sqrt(dlat**2 + dlon**2)

    closest_idx = np.argmin(dists, axis=1)
    gdf["city_hub_auto"] = hub_names[closest_idx]

    return gdf


def carte_flapd_server(input, output, session, gdf: gpd.GeoDataFrame):
    selected_ville = reactive.Value("All")

    # === BOUTONS ===
    @reactive.effect
    @reactive.event(input.go_paris)
    def _go_paris():
        selected_ville.set("Paris")

    @reactive.effect
    @reactive.event(input.go_london)
    def _go_london():
        selected_ville.set("London")

    @reactive.effect
    @reactive.event(input.go_amsterdam)
    def _go_amsterdam():
        selected_ville.set("Amsterdam")

    @reactive.effect
    @reactive.event(input.go_frankfurt)
    def _go_frankfurt():
        selected_ville.set("Frankfurt am Main")

    @reactive.effect
    @reactive.event(input.go_dublin)
    def _go_dublin():
        selected_ville.set("Dublin")

    @reactive.effect
    @reactive.event(input.reset_vue)
    def _reset():
        selected_ville.set("All")

    # === CARTE FLAP-D ===
    @output
    @render.ui
    def map_flapd_sites():
        city = selected_ville()
        df = gdf.copy()
        is_dark = _is_dark(input)

        tiles = "cartodbdark_matter" if is_dark else "cartodbpositron"

        # ====== VUE GLOBALE ======
        if city == "All":
            m = folium.Map(location=[51, 5], zoom_start=5, tiles=tiles)
            cluster = MarkerCluster().add_to(m)

            for _, r in df.iterrows():
                popup = f"<b>{r.get('name','')}</b><br>{r.get('city','')}<br>{r.get('company','')}"
                folium.Marker([r["latitude"], r["longitude"]], popup=popup).add_to(cluster)

            return ui.div(ui.HTML(m._repr_html_()), class_="map-wrap")

        # ====== VUE PAR HUB ======
        df = df[df["city_hub_auto"] == city].copy()
        if df.empty:
            return ui.div(f"Aucun DC trouvé pour {city}")

        df["lat_jit"] = df["latitude"].apply(jitter)
        df["lon_jit"] = df["longitude"].apply(jitter)

        # palette puissance
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

        # percentiles surface
        surf = df["area_m2"].astype(float).dropna()
        if len(surf) == 0:
            small = med = large = 0
        else:
            small = int(np.percentile(surf, 25))
            med = int(np.percentile(surf, 50))
            large = int(np.percentile(surf, 75))

        # === Points ===
        for _, r in df.iterrows():
            cap = float(r["capacity_e"]) if pd.notna(r["capacity_e"]) else 0.0
            ar = float(r["area_m2"]) if pd.notna(r["area_m2"]) else 10.0

            popup = (
                f"<b>{r.get('name','')}</b><br>"
                f"Surface : {ar:,.0f} m²<br>"
                f"Capacité : {cap:.1f} MW<br>"
                f"Entreprise : {r.get('company','')}"
            )

            if len(surf) > 1:
                r_marker = float(np.interp(ar, (surf.min(), surf.max()), (8, 22)))
                r_base = float(np.interp(ar, (surf.min(), surf.max()), (50, 250)))
            else:
                r_marker, r_base = 10.0, 100.0

            col = "white" if is_dark else "black"

            folium.CircleMarker(
                [r["lat_jit"], r["lon_jit"]],
                radius=r_marker,
                color=col,
                fill=True,
                fill_color=pal(cap),
                fill_opacity=0.9,
                weight=1,
                popup=popup,
            ).add_to(m)

            folium.Circle(
                [r["lat_jit"], r["lon_jit"]],
                radius=r_base,
                color=col,
                fill=False,
                opacity=0.07,
            ).add_to(m)

            folium.Circle(
                [r["lat_jit"], r["lon_jit"]],
                radius=r_base * 1.5,
                color=col,
                fill=False,
                opacity=0.04,
            ).add_to(m)

        # === LÉGENDE ADAPTÉE DARK/MODE CLAIR ===
        bg = "rgba(20,20,20,0.85)" if is_dark else "rgba(255,255,255,0.9)"
        txt = "#fff" if is_dark else "#111"
        st = "#fff" if is_dark else "#000"

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

        return ui.div(ui.HTML(m._repr_html_()), class_="map-wrap")

    # === TABLEAU SYNTHÉTIQUE ===
    @output
    @render.ui
    def encarts_villes():
        hubs = ["Paris", "London", "Amsterdam", "Frankfurt am Main", "Dublin"]
        drapeaux = {
            "Paris": "🇫🇷",
            "London": "🇬🇧",
            "Amsterdam": "🇳🇱",
            "Frankfurt am Main": "🇩🇪",
            "Dublin": "🇮🇪",
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
            if pd.isna(p):
                return "gray"
            if p < 30:
                return "#d9534f"
            if p < 60:
                return "#f0ad4e"
            return "#0275d8"

        def dot(p):
            return f"<span style='color:{dot_color(p)};font-size:18px;margin-left:4px;'>●</span>"

        def fmt(x, d=2):
            if pd.isna(x):
                return "-"
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

        titre = ui.h4("📊 Synthèse par hub", class_="titre-synthese")

        return ui.div(
            ui.div(titre, class_="text-center mt-3"),
            ui.HTML(table_html),
            class_="container-fluid mt-3",
        )


# === WRAPPER attendu par server/__init__.py ===
def server(input, output, session, app_dir: Path):
    # logs safe
    try:
        sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
    except Exception:
        pass

    print("=== DÉMARRAGE MODULE FLAPD ===")

    data_path = app_dir / "www" / "data" / "DC_FLAP_D.geojson"
    print("Chargement GeoJSON :", data_path)

    gdf = gpd.read_file(data_path)
    gdf = _prepare_gdf(gdf)

    return carte_flapd_server(input, output, session, gdf)
