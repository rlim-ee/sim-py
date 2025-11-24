# fetch_owid_mix.py
# --------------------------------------------------
# OWID -> 2 CSV (2014–2024) : mix par filière + conso brute
# Compatible colonnes *_electricity et ISO-3 (DEU, ESP, …)
# --------------------------------------------------

import pandas as pd
import numpy as np
import os

URL = "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv"

OUT_MIX  = "www/data/mix_energie_par_filiere_2014_2024.csv"
OUT_CONS = "www/data/consommation_brute_2014_2024.csv"

# --- PAYS (codes ISO-3 dans OWID) ---
COUNTRIES = {
    "DEU": "Allemagne",
    "ESP": "Espagne",
    "ITA": "Italie",
    "CHE": "Suisse",
    "GBR": "Royaume-Uni",
    "IRL": "Irlande",
    "BEL": "Belgique",
    "NLD": "Pays-Bas",
}

# --- Catégories -> libellés FR ---
FILIERES_FR = {
    "nuc": "Nucléaire",
    "hyd": "Hydraulique",
    "fos": "Fossile",
    "eol": "Éolien",
    "sol": "Solaire",
    "autre": "Autre",
}

# --- Colonnes *_electricity regroupées par catégorie ---
ELECTRICITY_COLS = {
    "nuc":  ["nuclear_electricity"],
    "hyd":  ["hydro_electricity"],
    "eol":  ["wind_electricity"],
    "sol":  ["solar_electricity"],
    "fos":  ["coal_electricity", "gas_electricity", "oil_electricity"],
    "autre":["biofuel_electricity",
             "other_renewable_electricity",
             "other_renewable_exc_biofuel_electricity"],
}

# conso brute : d’abord electricity_demand, sinon electricity_generation
PREFERRED_CONS = ["electricity_demand"]
FALLBACK_CONS  = ["electricity_generation"]

def _sum_row(row: pd.Series, cols: list[str]) -> float:
    vals = [row[c] for c in cols if c in row and pd.notna(row[c])]
    return float(np.nansum(vals)) if vals else 0.0

def main():
    os.makedirs("www/data", exist_ok=True)
    print("Téléchargement du fichier OWID…")
    df = pd.read_csv(URL, low_memory=False)

    # Filtre années/pays (ISO-3 !)
    df = df[df["year"].between(2014, 2024)]
    df = df[df["iso_code"].isin(COUNTRIES.keys())].copy()
    if df.empty:
        raise RuntimeError("Aucun enregistrement après filtre ISO-3 — vérifie COUNTRIES et la colonne iso_code.")

    # === Consommation brute (TWh) ===
    cons_cols = [c for c in PREFERRED_CONS if c in df.columns]
    if not cons_cols:
        cons_cols = [c for c in FALLBACK_CONS if c in df.columns]
    if not cons_cols:
        print("⚠️ Ni electricity_demand ni electricity_generation trouvés — conso=0")
        df["electricity_demand"] = 0.0
        cons_cols = ["electricity_demand"]

    conso = (
        df[["iso_code", "year", "country"] + cons_cols]
        .assign(twh=lambda d: d[cons_cols].sum(axis=1))
        [["iso_code", "year", "country", "twh"]]
        .rename(columns={"iso_code": "country_code", "country": "country_fr"})
        .replace({"country_code": COUNTRIES, "country_fr": COUNTRIES})
        .reset_index(drop=True)
    )
    conso.to_csv(OUT_CONS, index=False)
    print(f"✅ {OUT_CONS} écrit ({len(conso)} lignes)")

    # === Production d’électricité par filière (TWh) ===
    # Vérifier les colonnes effectivement présentes
    effective_map: dict[str, list[str]] = {}
    for k, cols in ELECTRICITY_COLS.items():
        present = [c for c in cols if c in df.columns]
        if not present:
            print(f"ℹ️ Avertissement: aucune colonne trouvée pour '{k}' — valeurs=0")
        effective_map[k] = present

    records = []
    for _, row in df.iterrows():
        iso3 = row["iso_code"]
        for filiere, cols in effective_map.items():
            val = _sum_row(row, cols)
            records.append({
                "year": int(row["year"]),
                "country_code": iso3,
                "country_fr": COUNTRIES[iso3],
                "filiere": filiere,
                "filiere_label": FILIERES_FR[filiere],
                "twh": val,
            })

    mix = pd.DataFrame.from_records(records)
    if mix.empty:
        raise RuntimeError("Aucun enregistrement de mix — vérifie les colonnes *_electricity disponibles.")

    mix = (
        mix.groupby(["year","country_code","country_fr","filiere","filiere_label"], as_index=False)["twh"]
           .sum()
    )
    mix.to_csv(OUT_MIX, index=False)
    print(f"✅ {OUT_MIX} écrit ({len(mix)} lignes)")

    # === Contrôle rapide prod vs conso ===
    check = (
        mix.groupby(["country_code","country_fr","year"], as_index=False)["twh"]
           .sum().rename(columns={"twh":"twh_prod_total"})
           .merge(conso.rename(columns={"twh":"twh_conso"}),
                  on=["country_code","year"], how="left")
    )
    check["écart_prod_conso_TWh"] = (check["twh_prod_total"] - check["twh_conso"]).round(2)
    print("\nAperçu écarts production vs consommation :")
    print(check.head(8).to_string(index=False))

if __name__ == "__main__":
    main()
