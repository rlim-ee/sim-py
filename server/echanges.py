# server/echanges.py
from __future__ import annotations

from shiny import render, ui, reactive, req
from shinywidgets import render_widget
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

import folium
from folium import CircleMarker

# =========================
#      Chemins locaux
# =========================
CSV_RTE  = "www/data/fr_elec_trade_by_neighbor_clean.csv"
CSV_MIX  = "www/data/mix_energie_par_filiere_2014_2024.csv"
CSV_CONS = "www/data/consommation_brute_2014_2024.csv"

# =========================
#      Constantes
# =========================
ALIASES = {
    "Royaume-Uni": "Grande-Bretagne",
    "Grande Bretagne": "Grande-Bretagne",
    "Belgique / Allemagne": "Belgique/Allemagne",
    "Belgique-–-Allemagne": "Belgique/Allemagne",
}

# iso3 -> (label FR, lat, lon)
COUNTRIES = {
    "DEU": ("Allemagne",     51.0, 10.0),
    "ESP": ("Espagne",       40.0, -4.0),
    "ITA": ("Italie",        42.5, 12.5),
    "CHE": ("Suisse",        46.8,  8.2),
    "GBR": ("Royaume-Uni",   54.0, -2.0),
    "IRL": ("Irlande",       53.1, -8.0),
    "BEL": ("Belgique",      50.8,  4.6),
    "NLD": ("Pays-Bas",      52.2,  5.3),
    "FRA": ("France",        46.5,  2.5),
}

FILIERE_ORDER = ["nuc", "hyd", "fos", "eol", "sol", "autre"]
FILIERE_LABEL = {
    "nuc": "Nucléaire",
    "hyd": "Hydraulique",
    "fos": "Fossile",  # ⚠️ ici on inclut le gaz
    "eol": "Éolien",
    "sol": "Solaire",
    "autre": "Autre",
}
FILIERE_COLOR = {
    "nuc":   "#FFE18B",
    "hyd":   "#2071B2",
    "fos":   "#313334",
    "eol":   "#8DCDBF",
    "sol":   "#F4902E",
    "autre": "#14682D",
}
FILIERE_CHOICES = {
    "all": "Toutes filières",
    "nuc": "Nucléaire",
    "hyd": "Hydraulique",
    "fos": "Fossile (incl. gaz)",
    "eol": "Éolien",
    "sol": "Solaire",
    "autre": "Autre",
}

# =========================
#       Helpers
# =========================
def _is_dark(input) -> bool:
    """Essaie de récupérer l’état du switch darkmode côté UI."""
    try:
        dm = getattr(input, "darkmode", None)
        return bool(dm()) if callable(dm) else False
    except Exception:
        return False


def _plotly_theme(is_dark: bool) -> dict:
    """Thème Plotly cohérent (comme dans server/repartition.py)."""
    return {
        "font": "#e5e7eb" if is_dark else "#0f172a",
        "grid": "rgba(203,213,225,.26)" if is_dark else "rgba(15,23,42,.08)",
        "zeroline": "rgba(148,163,184,.60)" if is_dark else "rgba(100,116,139,.60)",
        "paper": "rgba(0,0,0,0)",
        "plot": "rgba(0,0,0,0)",
        # couleurs par défaut pour barres (ici peu utilisé, mais dispo)
        "bar": "#7c8cff" if is_dark else "#5B7CFF",
        "bar_outline": "rgba(255,255,255,.18)" if is_dark else "rgba(0,0,0,.08)",
        # fond de légende
        "legend_bg": "rgba(15,23,42,.92)" if is_dark else "rgba(255,255,255,.94)",
        "legend_border": "rgba(148,163,184,.85)" if is_dark else "rgba(15,23,42,.45)",
    }


def _prep_trade(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["frontiere"] = df["frontiere"].astype(str).map(lambda s: ALIASES.get(s, s))
    df = df[df["frontiere"].str.lower() != "toutes les frontières"]
    return df


def _filter_period(df: pd.DataFrame, start: str, end: str) -> pd.DataFrame:
    start, end = pd.to_datetime(start), pd.to_datetime(end)
    return df[(df["date"] >= start) & (df["date"] <= end)].copy()


def _agg_period(df_sub: pd.DataFrame, how: str) -> pd.DataFrame:
    df_sub = df_sub.copy()
    freq = "Y" if how == "Annuel" else "M"
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
    # rappel : importations sont négatives dans ton CSV
    piv["Solde"] = piv["Exportations"] + piv["Importations"]
    return piv


# =========================
#         SERVER
# =========================
def server(input, output, session, app_dir: Path):
    # --- chargement des données ---
    df_trade = _prep_trade(pd.read_csv(CSV_RTE))
    neighbors = sorted(df_trade["frontiere"].unique().tolist())

    mix = pd.read_csv(CSV_MIX)
    conso = pd.read_csv(CSV_CONS)

    keep_iso3 = set(COUNTRIES.keys())
    mix = mix[mix["country_code"].isin(keep_iso3) & mix["year"].between(2014, 2024)].copy()
    conso = conso[conso["country_code"].isin(keep_iso3) & conso["year"].between(2014, 2024)].copy()

    # ========= Réactifs pour la carte/graphique OWID =========

    # année pour la carte + barplot (avec bouton “Appliquer”)
    @reactive.calc
    @reactive.event(input.ech_apply)
    def r_mix_year():
        try:
            y = int(input.ech_mix_year())
        except Exception:
            y = 2024
        return max(2014, min(2024, y))

    # filière choisie
    @reactive.calc
    def r_mix_filiere():
        # "all" si tout
        val = input.ech_mix_filiere()
        return val or "all"

    # barplot en % ?
    @reactive.calc
    def r_plot_mode_pct():
        return bool(input.ech_plot_mode())

    # ========= Carte (mix OWID) =========
    @output
    @render.ui
    @reactive.event(input.ech_apply)
    def map_elec():
        year = r_mix_year()
        filiere = r_mix_filiere()
        dark = _is_dark(input)

        # pivot production (année x pays x filière)
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

        # consommation du même millésime (pour le tooltip)
        conso_y = (
            conso[conso["year"] == year]
            .set_index("country_code")["twh"]
            .to_dict()
        )

        # valeur de base = production de la filière OU production totale
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

            # prod totale (pour le tooltip)
            total_prod = float(pivot.loc[iso3, FILIERE_ORDER].sum())
            # conso (pour le tooltip)
            total_conso = float(conso_y.get(iso3, 0.0))

            # production de la filière sélectionnée
            if filiere == "all":
                prod_filiere = total_prod
                # gris clair pour différencier du bleu hydraulique
                color = "#9C9CA1"
                filiere_label = "Toutes filières"
            else:
                prod_filiere = float(pivot.loc[iso3, filiere])
                color = FILIERE_COLOR.get(filiere, "#777")
                filiere_label = FILIERE_LABEL.get(filiere, filiere)

            base = bases.get(iso3, 0.0)
            if max_base <= 0:
                radius = MIN_R
            else:
                ratio = base / max_base
                radius = MIN_R + ratio * (MAX_R - MIN_R)

            # tooltip
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

        # on garde le wrapper .map-wrap du CSS
        return ui.HTML(f"<div class='map-wrap'>{m._repr_html_()}</div>")

    # ========= Barplot (mix OWID) + ligne de conso =========
    @output
    @render_widget
    @reactive.event(input.ech_apply)
    def bar_exports():
        year = r_mix_year()
        as_pct = r_plot_mode_pct()
        dark = _is_dark(input)
        th = _plotly_theme(dark)

        # pivot prod
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

        # conso pour l’année
        conso_y = (
            conso[conso["year"] == year]
            .set_index("country_fr")["twh"]
            .to_dict()
        )

        # ====== cas % : barres en % ======
        if as_pct:
            totals = pivot.sum(axis=1).replace(0, 1)
            data = (pivot.div(totals, axis=0) * 100).round(1)
            ylab = "Part du mix (%)"

            long = (
                data.reset_index()
                .melt(id_vars="country_fr", var_name="filiere", value_name="val")
                .replace({"filiere": FILIERE_LABEL})
            )
            color_map = {FILIERE_LABEL[k]: v for k, v in FILIERE_COLOR.items()}

            fig = px.bar(
                long,
                x="country_fr",
                y="val",
                color="filiere",
                category_orders={"filiere": [FILIERE_LABEL[f] for f in FILIERE_ORDER]},
                labels={"country_fr": "Pays", "val": ylab, "filiere": "Filière"},
                title=f"Mix énergétique — {year}",
            )

            fig.update_traces(
                marker=dict(line=dict(color=th["bar_outline"], width=1)),
                hovertemplate="%{x} — %{y:.1f}% (%{legendgroup})<extra></extra>",
            )

            fig.update_layout(
                barmode="stack",
                title_x=0.5,
                margin=dict(l=10, r=10, t=56, b=30),
                plot_bgcolor=th["plot"],
                paper_bgcolor=th["paper"],
                legend_title_text="Filière",
                font=dict(
                    family="Poppins, Arial, sans-serif",
                    color=th["font"],
                ),
                legend=dict(
                    bgcolor=th["legend_bg"],
                    bordercolor=th["legend_border"],
                    borderwidth=1,
                ),
            )
            fig.update_yaxes(
                title_text=ylab,
                gridcolor=th["grid"],
                zeroline=True,
                zerolinecolor=th["zeroline"],
                zerolinewidth=1.6,
                tickfont=dict(color=th["font"]),
                title_font=dict(color=th["font"]),
            )
            fig.update_xaxes(
                title_text="Pays",
                tickfont=dict(color=th["font"]),
                title_font=dict(color=th["font"]),
            )

            # recolorer les barres
            for tr in fig.data:
                tr.marker.color = color_map.get(tr.name, tr.marker.color)

            return fig

        # ====== cas TWh : barres + ligne conso ======
        data = pivot.round(2)
        long = (
            data.reset_index()
            .melt(id_vars="country_fr", var_name="filiere", value_name="val")
            .replace({"filiere": FILIERE_LABEL})
        )
        color_map = {FILIERE_LABEL[k]: v for k, v in FILIERE_COLOR.items()}

        fig = px.bar(
            long,
            x="country_fr",
            y="val",
            color="filiere",
            category_orders={"filiere": [FILIERE_LABEL[f] for f in FILIERE_ORDER]},
            labels={"country_fr": "Pays", "val": "TWh", "filiere": "Filière"},
            title=f"Mix énergétique — {year}",
        )

        fig.update_traces(
            marker=dict(line=dict(color=th["bar_outline"], width=1)),
            hovertemplate="%{x} — %{y:.1f} TWh (%{legendgroup})<extra></extra>",
        )

        fig.update_layout(
            barmode="stack",
            title_x=0.5,
            margin=dict(l=10, r=10, t=56, b=30),
            plot_bgcolor=th["plot"],
            paper_bgcolor=th["paper"],
            legend_title_text="Filière",
            font=dict(
                family="Poppins, Arial, sans-serif",
                color=th["font"],
            ),
            legend=dict(
                bgcolor=th["legend_bg"],
                bordercolor=th["legend_border"],
                borderwidth=1,
            ),
        )
        fig.update_yaxes(
            title_text="TWh",
            gridcolor=th["grid"],
            zeroline=True,
            zerolinecolor=th["zeroline"],
            zerolinewidth=1.6,
            tickfont=dict(color=th["font"]),
            title_font=dict(color=th["font"]),
        )
        fig.update_xaxes(
            title_text="Pays",
            tickfont=dict(color=th["font"]),
            title_font=dict(color=th["font"]),
        )

        # ligne de conso brute annuelle (même axe Y)
        pays_ordre = data.index.tolist()
        conso_line_x = []
        conso_line_y = []
        for p in pays_ordre:
            conso_line_x.append(p)
            conso_line_y.append(float(conso_y.get(p, 0.0)))

        fig.add_trace(
            go.Scatter(
                x=conso_line_x,
                y=conso_line_y,
                mode="lines+markers",
                name="Consommation brute (TWh)",
                line=dict(
                    color="#DC2626" if not dark else "#F97316",
                    width=3,
                ),
                marker=dict(size=7),
                hovertemplate="Consommation: %{y:.1f} TWh<extra></extra>",
            )
        )

        # recolorer les barres
        for tr in fig.data:
            if tr.type == "bar":
                tr.marker.color = color_map.get(tr.name, tr.marker.color)

        return fig

    # ========= Partie comparaison (RTE) =========
    @reactive.effect
    def _seed_checkboxes():
        if df_trade.empty:
            return
        ex_tot = (
            df_trade[df_trade["type"] == "Exportations"]
            .groupby("frontiere")["valeur"].sum()
            .sort_values(ascending=False)
        )
        default_sel = [p for p in ex_tot.index[:2] if p in neighbors] or neighbors[:1]
        ui.update_checkbox_group("ech_countries", choices=neighbors, selected=default_sel)

    @reactive.effect
    def _toggle_btn():
        enabled = len(input.ech_countries() or []) >= 1
        session.send_input_message("ech_compare_go", {"disabled": (not enabled)})

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
    @reactive.event(input.ech_compare_go)
    def comp_plot():
        dark = _is_dark(input)
        th = _plotly_theme(dark)

        s, e = r_cmp_period()
        metric = r_cmp_metric()
        how = r_cmp_agg()
        try:
            roll = max(1, min(6, int(input.ech_roll() or 1)))
        except Exception:
            roll = 1

        keep = input.ech_countries() or []
        if not keep:
            req(False)

        sub = _filter_period(df_trade, s, e)
        agg = _agg_period(sub, how=how)

        data = (
            agg[agg["frontiere"].isin(keep)][["periode", "frontiere", metric]]
            .sort_values(["frontiere", "periode"])
        )
        data["periode"] = pd.to_datetime(data["periode"]).astype("datetime64[ms]")
        data[metric] = data.groupby("frontiere")[metric].transform(
            lambda s: s.rolling(roll, min_periods=1).mean()
        )

        title_cible = ", ".join(keep) if len(keep) <= 6 else f"{len(keep)} pays"
        fig = px.line(
            data,
            x="periode",
            y=metric,
            color="frontiere",
            labels={"periode": "Période", metric: f"{metric} (TWh)"},
            title=f"{metric} — comparaison ({title_cible})",
            color_discrete_map={
                "Suisse": "#DC2626",             # rouge
                "Belgique/Allemagne": "#000000", # noir
                "Italie": "#1D4ED8",            # bleu
                "Espagne": "#FACC15",           # jaune
                "Royaume-Uni": "#7C3AED",       # violet
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
            plot_bgcolor=th["plot"],
            paper_bgcolor=th["paper"],
            font=dict(
                color=th["font"],
                family="Poppins, Arial, sans-serif",
            ),
            legend=dict(
                bgcolor=th["legend_bg"],
                bordercolor=th["legend_border"],
                borderwidth=1,
            ),
        )

        fig.update_yaxes(
            title_text=f"{metric} (TWh)",
            gridcolor=th["grid"],
            zeroline=True,
            zerolinewidth=2.5,   # ligne 0 mise en valeur
            zerolinecolor=th["zeroline"],
            tickfont=dict(color=th["font"]),
            title_font=dict(color=th["font"]),
        )

        fig.update_xaxes(
            type="date",
            tickformat="%Y-%m" if how == "Mensuel" else "%Y",
            tickfont=dict(color=th["font"]),
            title_font=dict(color=th["font"]),
            title_text="Période",
        )

        return fig
