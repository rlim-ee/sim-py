# server/energie/echanges.py — échanges électriques entre la France et ses voisins
#
# Ce module répond à deux questions :
#   1. "Comment se répartit le mix énergétique de chaque pays d'Europe ?" (carte + barplot OWID)
#   2. "Comment évoluent les exports/imports/solde entre la France et chaque pays voisin ?" (courbes RTE)
#
# Il produit trois outputs :
#   - map_elec    → carte Folium avec cercles proportionnels par pays/filière
#   - bar_exports → barplot Plotly du mix par pays (en TWh ou en %)
#   - comp_plot   → courbes temporelles des échanges franco-voisins (données RTE)
#
# Les données viennent de :
#   - www/data/fr_elec_trade_by_neighbor_clean.csv  (échanges RTE)
#   - www/data/mix_energie_par_filiere_2014_2024.csv (mix OWID)
#   - www/data/consommation_brute_2014_2024.csv      (conso OWID)
from __future__ import annotations

from shiny import render, ui, reactive, req
from shinywidgets import render_widget
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

import folium
from folium import CircleMarker

from server._common import (
    is_dark, plotly_theme, cached,
    FILIERE_CODES, FILIERE_LABEL, FILIERE_COLOR,
)


# =========================================================
# Constantes
# =========================================================

# Harmonisation des noms de pays dans les données RTE (orthographes variables)
ALIASES = {
    "Royaume-Uni":         "Grande-Bretagne",
    "Grande Bretagne":     "Grande-Bretagne",
    "Belgique / Allemagne": "Belgique/Allemagne",
    "Belgique-–-Allemagne": "Belgique/Allemagne",
}

# Pays représentés sur la carte du mix OWID : iso3 → (libellé, lat, lon)
COUNTRIES = {
    "DEU": ("Allemagne",    51.0, 10.0),
    "ESP": ("Espagne",      40.0, -4.0),
    "ITA": ("Italie",       42.5, 12.5),
    "CHE": ("Suisse",       46.8,  8.2),
    "GBR": ("Royaume-Uni",  54.0, -2.0),
    "IRL": ("Irlande",      53.1, -8.0),
    "BEL": ("Belgique",     50.8,  4.6),
    "NLD": ("Pays-Bas",     52.2,  5.3),
    "FRA": ("France",       46.5,  2.5),
}

FILIERE_ORDER = FILIERE_CODES

FILIERE_CHOICES = {
    "all":   "Toutes filières",
    "nuc":   "Nucléaire",
    "hyd":   "Hydraulique",
    "fos":   "Fossile (incl. gaz)",
    "eol":   "Éolien",
    "sol":   "Solaire",
    "autre": "Autre",
}


# =========================================================
# Fonctions de préparation des données RTE
# =========================================================
def _prep_trade(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie le CSV des échanges : conversion de dates et harmonisation des noms."""
    df = df.copy()
    df["date"]      = pd.to_datetime(df["date"])
    df["frontiere"] = df["frontiere"].astype(str).map(lambda s: ALIASES.get(s, s))
    df = df[df["frontiere"].str.lower() != "toutes les frontières"]
    return df


def _filter_period(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    """Filtre le dataframe sur une plage de dates."""
    start, end = pd.to_datetime(start), pd.to_datetime(end)
    return df[(df["date"] >= start) & (df["date"] <= end)].copy()


def _agg_period(df_sub: pd.DataFrame, how: str) -> pd.DataFrame:
    """
    Agrège les échanges par période (mensuelle ou annuelle) et par frontière.
    Calcule le solde = Exportations + Importations (les imports sont négatifs dans les données).
    """
    df_sub = df_sub.copy()
    freq   = "Y" if how == "Annuel" else "M"
    df_sub["periode"] = (
        df_sub["date"]
        .dt.to_period(freq)
        .dt.to_timestamp()
        .astype("datetime64[ms]")
    )
    piv = (
        df_sub.pivot_table(
            index=["periode", "frontiere"],
            columns="type",
            values="valeur",
            aggfunc="sum",
        )
        .fillna(0)
        .reset_index()
    )
    for c in ("Exportations", "Importations"):
        if c not in piv.columns:
            piv[c] = 0.0
    piv["Solde"] = piv["Exportations"] + piv["Importations"]
    return piv


# =========================================================
# Chargement global des trois fichiers de données
# =========================================================
def _load_all(app_dir: Path) -> dict:
    data_dir = app_dir / "www" / "data"
    df_trade = _prep_trade(pd.read_csv(data_dir / "fr_elec_trade_by_neighbor_clean.csv"))
    mix      = pd.read_csv(data_dir / "mix_energie_par_filiere_2014_2024.csv")
    conso    = pd.read_csv(data_dir / "consommation_brute_2014_2024.csv")

    keep_iso3 = set(COUNTRIES.keys())
    mix   = mix[mix["country_code"].isin(keep_iso3) & mix["year"].between(2014, 2024)].copy()
    conso = conso[conso["country_code"].isin(keep_iso3) & conso["year"].between(2014, 2024)].copy()

    return {
        "df_trade":  df_trade,
        "mix":       mix,
        "conso":     conso,
        "neighbors": sorted(df_trade["frontiere"].unique().tolist()),
    }


# =========================================================
# Construction de la carte Folium du mix par pays
# =========================================================
def _build_map_elec_html(mix: pd.DataFrame, conso: pd.DataFrame, year: int, filiere: str, dark: bool) -> str:
    """
    Carte avec un cercle par pays. Le rayon reflète la production (ou la production
    de la filière sélectionnée), la couleur correspond à la filière.
    """
    pivot = (
        mix[mix["year"] == year]
        .pivot_table(
            index="country_code",
            columns="filiere",
            values="twh",
            aggfunc="sum",
        )
        .reindex(columns=FILIERE_ORDER, fill_value=0.0)
        .fillna(0.0)
    )

    conso_y = (
        conso[conso["year"] == year]
        .set_index("country_code")["twh"]
        .to_dict()
    )

    # Calcul de la valeur servant à déterminer le rayon de chaque cercle
    bases = {}
    for iso3 in COUNTRIES.keys():
        if iso3 not in pivot.index:
            continue
        if filiere == "all":
            base = float(pivot.loc[iso3, FILIERE_ORDER].sum())
        else:
            base = float(pivot.loc[iso3, filiere])
        bases[iso3] = max(0.0, base)

    max_base = max(bases.values()) if bases else 1.0

    MIN_R = 1
    MAX_R = 42

    tiles = "cartodbdark_matter" if dark else "CartoDB positron"

    m = folium.Map(
        location=[50.5, 6.0],
        zoom_start=4.0,
        tiles=tiles,
        control_scale=True,
        width="100%",
        height="100%",
    )

    for iso3, (name_fr, lat, lon) in COUNTRIES.items():
        if iso3 not in pivot.index:
            continue

        total_prod  = float(pivot.loc[iso3, FILIERE_ORDER].sum())
        total_conso = float(conso_y.get(iso3, 0.0))

        if filiere == "all":
            prod_filiere  = total_prod
            color         = "#9C9CA1"
            filiere_label = "Toutes filières"
        else:
            prod_filiere  = float(pivot.loc[iso3, filiere])
            color         = FILIERE_COLOR.get(filiere, "#777")
            filiere_label = FILIERE_LABEL.get(filiere, filiere)

        base = bases.get(iso3, 0.0)
        if max_base <= 0:
            radius = MIN_R
        else:
            ratio  = base / max_base
            radius = MIN_R + ratio * (MAX_R - MIN_R)

        lines = [
            f"<strong>{name_fr}</strong> — {year}",
            f"Production totale : {total_prod:.1f} TWh",
            f"Consommation totale : {total_conso:.1f} TWh",
            f"Production ({filiere_label}) : {prod_filiere:.1f} TWh",
            "<hr style='margin:6px 0'/>",
            "<em>Note : la catégorie « Fossile » inclut ici le gaz naturel.</em>",
        ]

        CircleMarker(
            location=(lat, lon),
            radius=radius,
            color=color,
            weight=1.4,
            fill=True,
            fill_color=color,
            fill_opacity=0.72,
            tooltip="<br>".join(lines),
        ).add_to(m)

    return f"<div class='map-wrap'>{m._repr_html_()}</div>"


# =========================================================
# Fonctions serveur Shiny
# =========================================================
def server(input, output, session, app_dir: Path):
    key    = f"echanges::{Path(app_dir).resolve()}"
    bundle = cached(key, lambda: _load_all(app_dir))
    df_trade  = bundle["df_trade"]
    mix       = bundle["mix"]
    conso     = bundle["conso"]
    neighbors = bundle["neighbors"]

    # --- Valeurs réactives calculées ---
    # @reactive.calc mémoïse le résultat : si l'input n'a pas changé,
    # le recalcul ne s'effectue pas (performances).

    @reactive.calc
    def r_mix_year():
        try:
            y = int(input.ech_mix_year())
        except Exception:
            y = 2024
        return max(2014, min(2024, y))

    @reactive.calc
    def r_mix_filiere():
        val = input.ech_mix_filiere()
        return val or "all"

    @reactive.calc
    def r_plot_mode_pct():
        return bool(input.ech_plot_mode())

    # --- Carte du mix (OWID) ---
    # Cache par (année, filière, thème) pour éviter de reconstruire la carte Folium
    # à chaque interaction non pertinente.
    _map_elec_cache: dict[tuple[int, str, bool], str] = {}

    @output
    @render.ui
    def map_elec():
        year    = r_mix_year()
        filiere = r_mix_filiere()
        dark    = is_dark(input)

        ck   = (year, filiere, dark)
        html = _map_elec_cache.get(ck)
        if html is None:
            html = _build_map_elec_html(mix, conso, year, filiere, dark)
            _map_elec_cache[ck] = html
        return ui.HTML(html)

    # --- Barplot du mix par pays (OWID) ---
    # Deux modes : valeurs absolues (TWh) ou part du mix (%).
    # En mode TWh, une ligne rouge de consommation brute est superposée.
    @output
    @render_widget
    def bar_exports():
        year   = r_mix_year()
        as_pct = r_plot_mode_pct()
        dark   = is_dark(input)
        th     = plotly_theme(dark)

        pivot = (
            mix[mix["year"] == year]
            .pivot_table(
                index="country_fr",
                columns="filiere",
                values="twh",
                aggfunc="sum",
            )
            .reindex(columns=FILIERE_ORDER, fill_value=0.0)
            .fillna(0.0)
        )

        conso_y = (
            conso[conso["year"] == year]
            .set_index("country_fr")["twh"]
            .to_dict()
        )

        if as_pct:
            # Barres empilées en pourcentage du total national
            totals = pivot.sum(axis=1).replace(0, 1)
            data   = (pivot.div(totals, axis=0) * 100).round(1)
            ylab   = "Part du mix (%)"

            long = (
                data.reset_index()
                .melt(id_vars="country_fr", var_name="filiere", value_name="val")
                .replace({"filiere": FILIERE_LABEL})
            )
            color_map = {FILIERE_LABEL[k]: v for k, v in FILIERE_COLOR.items()}

            fig = px.bar(
                long,
                x="country_fr", y="val", color="filiere",
                category_orders={"filiere": [FILIERE_LABEL[f] for f in FILIERE_ORDER]},
                labels={"country_fr": "Pays", "val": ylab, "filiere": "Filière"},
                title=f"Mix énergétique — {year}",
            )

            fig.update_traces(
                marker=dict(line=dict(color=th["bar_outline"], width=1)),
                hovertemplate="%{x} — %{y:.1f}% (%{legendgroup})<extra></extra>",
            )

            fig.update_layout(
                barmode="stack", title_x=0.5,
                margin=dict(l=10, r=10, t=56, b=30),
                plot_bgcolor=th["plot"], paper_bgcolor=th["paper"],
                legend_title_text="Filière",
                font=dict(family="Poppins, Arial, sans-serif", color=th["font"]),
                legend=dict(bgcolor=th["legend_bg"], bordercolor=th["legend_border"], borderwidth=1),
            )
            fig.update_yaxes(
                title_text=ylab, gridcolor=th["grid"],
                zeroline=True, zerolinecolor=th["zeroline"], zerolinewidth=1.6,
                tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
            )
            fig.update_xaxes(
                title_text="Pays",
                tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
            )

            for tr in fig.data:
                tr.marker.color = color_map.get(tr.name, tr.marker.color)

            return fig

        # Mode TWh : barres par filière + ligne de consommation brute
        data = pivot.round(2)
        long = (
            data.reset_index()
            .melt(id_vars="country_fr", var_name="filiere", value_name="val")
            .replace({"filiere": FILIERE_LABEL})
        )
        color_map = {FILIERE_LABEL[k]: v for k, v in FILIERE_COLOR.items()}

        fig = px.bar(
            long,
            x="country_fr", y="val", color="filiere",
            category_orders={"filiere": [FILIERE_LABEL[f] for f in FILIERE_ORDER]},
            labels={"country_fr": "Pays", "val": "TWh", "filiere": "Filière"},
            title=f"Mix énergétique — {year}",
        )

        fig.update_traces(
            marker=dict(line=dict(color=th["bar_outline"], width=1)),
            hovertemplate="%{x} — %{y:.1f} TWh (%{legendgroup})<extra></extra>",
        )

        fig.update_layout(
            barmode="stack", title_x=0.5,
            margin=dict(l=10, r=10, t=56, b=30),
            plot_bgcolor=th["plot"], paper_bgcolor=th["paper"],
            legend_title_text="Filière",
            font=dict(family="Poppins, Arial, sans-serif", color=th["font"]),
            legend=dict(bgcolor=th["legend_bg"], bordercolor=th["legend_border"], borderwidth=1),
        )
        fig.update_yaxes(
            title_text="TWh", gridcolor=th["grid"],
            zeroline=True, zerolinecolor=th["zeroline"], zerolinewidth=1.6,
            tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
        )
        fig.update_xaxes(
            title_text="Pays",
            tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
        )

        # Ligne de consommation brute superposée pour comparer production vs conso
        pays_ordre = data.index.tolist()
        conso_line_x, conso_line_y = [], []
        for p in pays_ordre:
            conso_line_x.append(p)
            conso_line_y.append(float(conso_y.get(p, 0.0)))

        fig.add_trace(
            go.Scatter(
                x=conso_line_x, y=conso_line_y,
                mode="lines+markers",
                name="Consommation brute (TWh)",
                line=dict(color="#DC2626" if not dark else "#F97316", width=3),
                marker=dict(size=7),
                hovertemplate="Consommation: %{y:.1f} TWh<extra></extra>",
            )
        )

        for tr in fig.data:
            if tr.type == "bar":
                tr.marker.color = color_map.get(tr.name, tr.marker.color)

        return fig

    # --- Courbes comparatives Franco-Voisins (données RTE) ---
    # Les cases à cocher sont initialisées au premier rendu avec les deux frontières
    # ayant le plus grand volume d'exportations (pré-sélection pertinente par défaut).
    _seeded = reactive.Value(False)

    @reactive.effect
    def _seed_checkboxes():
        if _seeded.get() or df_trade.empty:
            return
        ex_tot = (
            df_trade[df_trade["type"] == "Exportations"]
            .groupby("frontiere")["valeur"].sum()
            .sort_values(ascending=False)
        )
        default_sel = [p for p in ex_tot.index[:2] if p in neighbors] or neighbors[:1]
        ui.update_checkbox_group("ech_countries", choices=neighbors, selected=default_sel)
        _seeded.set(True)

    @reactive.calc
    def r_cmp_period():
        start, end = input.ech_cmp_period() or (
            str(df_trade["date"].min().date()), str(df_trade["date"].max().date())
        )
        return (start, end)

    @reactive.calc
    def r_cmp_metric():
        return input.ech_cmp_metric() or "Solde"

    @reactive.calc
    def r_cmp_agg():
        return input.ech_cmp_agg() or "Mensuel"

    @output
    @render_widget
    def comp_plot():
        dark   = is_dark(input)
        th     = plotly_theme(dark)

        s, e   = r_cmp_period()
        metric = r_cmp_metric()
        how    = r_cmp_agg()
        try:
            roll = max(1, min(6, int(input.ech_roll() or 1)))
        except Exception:
            roll = 1

        keep = input.ech_countries() or []
        if not keep:
            req(False)  # interrompt le rendu si aucune frontière n'est sélectionnée

        sub  = _filter_period(df_trade, s, e)
        agg  = _agg_period(sub, how=how)

        data = (
            agg[agg["frontiere"].isin(keep)][["periode", "frontiere", metric]]
            .sort_values(["frontiere", "periode"])
        )
        data["periode"] = pd.to_datetime(data["periode"]).astype("datetime64[ms]")

        # Lissage glissant optionnel (réduit le bruit sur les données mensuelles)
        data[metric] = data.groupby("frontiere")[metric].transform(
            lambda s: s.rolling(roll, min_periods=1).mean()
        )

        title_cible = ", ".join(keep) if len(keep) <= 6 else f"{len(keep)} pays"
        fig = px.line(
            data,
            x="periode", y=metric, color="frontiere",
            labels={"periode": "Période", metric: f"{metric} (TWh)"},
            title=f"{metric} — comparaison ({title_cible})",
            color_discrete_map={
                "Suisse":              "#DC2626",
                "Belgique/Allemagne":  "#000000",
                "Italie":              "#1D4ED8",
                "Espagne":             "#FACC15",
                "Royaume-Uni":         "#7C3AED",
            },
        )

        fig.update_traces(
            mode="lines+markers",
            line=dict(width=2.3),
            marker=dict(size=6),
            hovertemplate="%{x|%Y-%m-%d} — %{y:.1f} TWh (%{legendgroup})<extra></extra>",
        )

        fig.update_layout(
            title_x=0.5,
            margin=dict(l=10, r=16, t=54, b=20),
            plot_bgcolor=th["plot"], paper_bgcolor=th["paper"],
            font=dict(color=th["font"], family="Poppins, Arial, sans-serif"),
            legend=dict(bgcolor=th["legend_bg"], bordercolor=th["legend_border"], borderwidth=1),
        )

        fig.update_yaxes(
            title_text=f"{metric} (TWh)", gridcolor=th["grid"],
            zeroline=True, zerolinewidth=2.5, zerolinecolor=th["zeroline"],
            tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
        )

        fig.update_xaxes(
            type="date",
            tickformat="%Y-%m" if how == "Mensuel" else "%Y",
            tickfont=dict(color=th["font"]), title_font=dict(color=th["font"]),
            title_text="Période",
        )

        return fig
