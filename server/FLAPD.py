# === MODULE SERVEUR FLAP-D ===
from shiny import reactive, render, ui
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster
from branca.colormap import LinearColormap
from branca.colormap import linear
import numpy as np
import random
import pathlib
import sys


# === INITIALISATION ===

sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
print("=== DÉMARRAGE MODULE FLAPD ===")

data_path = (
    pathlib.Path(__file__).resolve().parents[2]
    / "sim-py"
    / "www"
    / "data"
    / "DC_FLAP_D.geojson"
)
print("Chargement GeoJSON :", data_path)
gdf = gpd.read_file(data_path)

# Convert numeric
gdf["capacity_e"] = pd.to_numeric(gdf["capacity_e"], errors="coerce")
gdf["area_m2"] = pd.to_numeric(gdf["area_m2"], errors="coerce")


# === 1) REGROUPEMENT AUTOMATIQUE (VECTORISÉ & CORRIGÉ) ===

hub_centers = {
    "Paris": (48.8566, 2.3522),
    "London": (51.5074, -0.1278),
    "Amsterdam": (52.3676, 4.9041),
    "Frankfurt am Main": (50.1109, 8.6821),
    "Dublin": (53.3498, -6.2603)
}

hub_names = np.array(list(hub_centers.keys()))
hub_coords = np.array(list(hub_centers.values()))  # shape (5,2)

# Points du fichier
pts = gdf[["latitude", "longitude"]].to_numpy()  # shape (N,2)

# Calcul vectorisé correct (shape (N,5))
dlat = pts[:, 0][:, None] - hub_coords[:, 0][None, :]
dlon = pts[:, 1][:, None] - hub_coords[:, 1][None, :]
dists = np.sqrt(dlat**2 + dlon**2)

# Pour chaque point : hub le plus proche
closest_idx = np.argmin(dists, axis=1)

# Assignation
gdf["city_hub_auto"] = hub_names[closest_idx]


# === 2) Fonction anti-superposition ===

def jitter(val, amplitude=0.002):
    return val + random.uniform(-amplitude, amplitude)


# === 3) SERVEUR ===
def carte_flapd_server(input, output, session):

    print("💥 carte_flapd_server activé !")

    selected_ville = reactive.Value("All")

    # === BOUTONS ===
    @reactive.effect
    @reactive.event(input.go_paris)
    def _():
        selected_ville.set("Paris")

    @reactive.effect
    @reactive.event(input.go_london)
    def _():
        selected_ville.set("London")

    @reactive.effect
    @reactive.event(input.go_amsterdam)
    def _():
        selected_ville.set("Amsterdam")

    @reactive.effect
    @reactive.event(input.go_frankfurt)
    def _():
        selected_ville.set("Frankfurt am Main")

    @reactive.effect
    @reactive.event(input.go_dublin)
    def _():
        selected_ville.set("Dublin")

    @reactive.effect
    @reactive.event(input.reset_vue)
    def _():
        selected_ville.set("All")

# === CARTE FLAP-D — Version propre et robuste ===

    @output
    @render.ui
    def map_flapd_sites():

        print("🟢 Rendu de map_flapd_sites lancé.")
        city = selected_ville()
        print("🏙️ Ville sélectionnée :", city)

        df = gdf.copy()

        # --- Mode sombre UI ---
        is_dark = False
        try:
            if hasattr(input, "darkmode"):
                is_dark = bool(input.darkmode())
        except:
            pass

        # VUE GLOBALE
        if city == "All":
            tiles = "cartodbdark_matter" if is_dark else "cartodb positron"
            m = folium.Map(location=[51, 5], zoom_start=5, tiles=tiles)

            cluster = MarkerCluster().add_to(m)
            for _, r in df.iterrows():
                popup = f"<b>{r['name']}</b><br>{r['city']}<br>{r['company']}"
                folium.Marker(
                    [r["latitude"], r["longitude"]],
                    popup=popup
                ).add_to(cluster)

            print("✅ Vue globale OK")
            return ui.div(ui.HTML(m._repr_html_()), class_="map-wrap")

        # VUE DÉTAILLÉE (par hub auto-regroupé)

        df = df[df["city_hub_auto"] == city]

        if df.empty:
            return ui.div(f"Aucun DC trouvé pour {city}")

        # ajouter jitter
        df["lat_jit"] = df["latitude"].apply(jitter)
        df["lon_jit"] = df["longitude"].apply(jitter)


        # CAPACITÉ — Nettoyage + bornes

        vals = df["capacity_e"].astype(float).replace([np.inf, -np.inf], np.nan).dropna()

        if len(vals) == 0:
            vmin, vmax = 0, 1
        else:
            vmin = float(vals.min())
            vmax = float(vals.max())

            # valeurs identiques → expansion
            if vmin == vmax:
                vmin -= 0.5
                vmax += 0.5

        # Colormap stable et continue
        pal = linear.Reds_09.scale(vmin, vmax)
        pal.caption = "Puissance (MW)"


        # CARTE FOLIUM

        tiles = "cartodbdark_matter" if is_dark else "cartodb positron"
        m = folium.Map(
            location=[df["latitude"].mean(), df["longitude"].mean()],
            zoom_start=11,
            tiles=tiles
        )


        # SURFACES (pour tailles cercles + légende)

        surf = df["area_m2"].astype(float).replace([np.inf, -np.inf], np.nan).dropna()
        if len(surf) == 0:
            small = med = large = 0
        else:
            small = int(np.percentile(surf, 25))
            med   = int(np.percentile(surf, 50))
            large = int(np.percentile(surf, 75))

 
        # AJOUT DES POINTS

        for _, r in df.iterrows():

            # valeurs sûres
            cap = float(r["capacity_e"]) if pd.notna(r["capacity_e"]) else 0.0
            ar  = float(r["area_m2"])    if pd.notna(r["area_m2"])    else 10.0

            popup = (
                f"<b>{r['name']}</b><br>"
                f"Surface : {ar:,.0f} m²<br>"
                f"Capacité : {cap:.1f} MW<br>"
                f"Entreprise : {r['company']}"
            )

            # tailles cercle
            if len(surf) > 1:
                r_marker = np.interp(ar, (surf.min(), surf.max()), (8, 22))
                r_base   = np.interp(ar, (surf.min(), surf.max()), (50, 250))
            else:
                r_marker = 10
                r_base   = 100

            col = "white" if is_dark else "black"

            folium.CircleMarker(
                [r["lat_jit"], r["lon_jit"]],
                radius=r_marker,
                color=col,
                fill=True,
                fill_color=pal(cap),
                fill_opacity=0.9,
                weight=1,
                popup=popup
            ).add_to(m)

            folium.Circle(
                [r["lat_jit"], r["lon_jit"]],
                radius=r_base,
                color=col,
                fill=False,
                weight=1,
                opacity=0.07
            ).add_to(m)

            folium.Circle(
                [r["lat_jit"], r["lon_jit"]],
                radius=r_base * 1.5,
                color=col,
                fill=False,
                weight=1,
                opacity=0.04
            ).add_to(m)


        # LÉGENDE circulaire

        bg = "rgba(20,20,20,0.85)" if is_dark else "rgba(255,255,255,0.9)"
        txt = "#fff" if is_dark else "#111"
        st  = "#fff" if is_dark else "#000"

        legend = f"""
        <div style="
            position: fixed; bottom: 35px; right: 25px;
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

        print("✅ Vue détaillée OK")
        return ui.div(ui.HTML(m._repr_html_()), class_="map-wrap")



    # === TABLEAU SYNTHÉTIQUE ===

    @output
    @render.ui
    def encarts_villes():

        print("🟢 encarts_villes() rendu — pastilles améliorées")

        hubs = ["Paris", "London", "Amsterdam", "Frankfurt am Main", "Dublin"]
        drapeaux = {
            "Paris": "🇫🇷", "London": "🇬🇧", "Amsterdam": "🇳🇱",
            "Frankfurt am Main": "🇩🇪", "Dublin": "🇮🇪"
        }

        # === 1) Agrégation ===
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

        # === 2) Nouvelles couleurs des pastilles ===
        def dot_color(p):
            if pd.isna(p): return "gray"
            if p < 30: return "#d9534f"       # rouge < 30%
            if p < 60: return "#f0ad4e"       # orange < 60%
            return "#0275d8"                  # bleu ≥ 60%

        def dot(p):
            return f"<span style='color:{dot_color(p)};font-size:18px;margin-left:4px;'>●</span>"

        # === Formatage chiffres ===
        def fmt(x, d=2):
            if pd.isna(x): return "-"
            return f"{x:,.{d}f}".replace(",", " ").replace(".", ",")

        # === 3) Colonnes finales ===
        df["Hub"] = df["city_hub_auto"].apply(lambda x: f"{drapeaux[x]} {x}")
        df["Nombre de DC recensés"] = df["nb_dc"]

        df["Surface moyenne (m²)"] = df.apply(lambda r: f"{fmt(r['surface_moy'],0)} {dot(r['share_area'])}", axis=1)
        df["Surface totale (m²)"] = df["surface_tot"].apply(lambda x: fmt(x, 0))

        df["Puissance moyenne (MW)"] = df.apply(lambda r: f"{fmt(r['puissance_moy'],2)} {dot(r['share_capacity'])}", axis=1)
        df["Puissance médiane (MW)"] = df.apply(lambda r: f"{fmt(r['puissance_med'],2)} {dot(r['share_capacity'])}", axis=1)

        df["PUE moyen"] = df.apply(lambda r: f"{fmt(r['pue_moy'],2)} {dot(r['share_pue'])}", axis=1)

        # === 4) Lignes HTML ===
        rows_html = "".join([
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
            """ for _, r in df.iterrows()
        ])

        # === 5) Table + JS triable ===
        table_html = f"""
        <style>
        th.sortable {{ cursor:pointer; user-select:none; }}
        th.sortable:hover {{ background:#e5ecff !important; }}
        th.sortable .sort-icon {{ margin-left:6px; font-size:12px; opacity:.6 }}
        table.table-synthese td {{ vertical-align:middle; }}
        </style>

        <table id="syntheseTable" class="table-synthese" style="width:100%">
            <thead>
                <tr>
                    <th onclick="sortTable(0)" class="sortable">Hub <span class="sort-icon"></span></th>
                    <th onclick="sortTable(1)" class="sortable">Nombre de DC recensés<span class="sort-icon"></span></th>
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

            document.querySelectorAll("th .sort-icon").forEach(e => e.textContent = "");
            table.rows[0].cells[colIndex].querySelector(".sort-icon").textContent = dir === "asc" ? "▲" : "▼";

            rows.sort(function(a, b) {{
                var A = a.cells[colIndex].innerText.replace(/●/g,"").replace(/\\s/g,"").replace(",",".");
                var B = b.cells[colIndex].innerText.replace(/●/g,"").replace(/\\s/g,"").replace(",",".");
                var nA = parseFloat(A), nB = parseFloat(B);
                if (!isNaN(nA) && !isNaN(nB)) {{
                    return dir === "asc" ? nA - nB : nB - nA;
                }}
                return dir === "asc" ? A.localeCompare(B) : B.localeCompare(A);
            }});
            rows.forEach(r => table.tBodies[0].appendChild(r));
        }}
        </script>

        <div style="text-align:center; margin-top:10px; font-size:14px; color:#555;">
            <b>Légende des pastilles :</b><br>
            <span style='color:#0275d8;font-size:16px'>●</span> Informations complètes (≥ 60%) &nbsp;|&nbsp;
            <span style='color:#f0ad4e;font-size:16px'>●</span> Informations partielles (30–60%) &nbsp;|&nbsp;
            <span style='color:#d9534f;font-size:16px'>●</span> Informations limitées (< 30%)
        </div>
        <div style="text-align:center; margin-top:8px; font-size:13px; color:#666;">
            Données collectées depuis <b>DataCenterMap</b> (avril 2025).
        </div>

        """

        titre = ui.div(
            ui.h4("📊 Synthèse par hub", style="font-weight:700;color:#0B162C;"),
            class_="text-center mt-4 mb-3"
        )

        return ui.div(titre, ui.HTML(table_html), class_="container-fluid")
