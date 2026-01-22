import requests
import pandas as pd

def fetch_oecd_wages(url):
    j = requests.get(url, timeout=60).json()

    data = j.get("data", {})
    dataset = (data.get("dataSets") or j.get("dataSets"))[0]

    structure = j.get("structure") or data.get("structure") or (data.get("structures") or [None])[0]
    if not structure:
        raise KeyError("Nema 'structure' u OECD odgovoru")

    series_dims = structure["dimensions"]["series"]
    obs_dims = structure["dimensions"]["observation"]

    dim_pos = {d["id"]: i for i, d in enumerate(series_dims)}
    geo_id = "LOCATION" if "LOCATION" in dim_pos else "REF_AREA"
    geo_pos = dim_pos[geo_id]

    years = [v["id"] for v in obs_dims[0]["values"]]

    rows = []
    for s_key, s_obj in dataset.get("series", {}).items():
        parts = [int(x) for x in s_key.split(":")]
        iso3 = series_dims[geo_pos]["values"][parts[geo_pos]]["id"]

        for t_idx, obs in s_obj.get("observations", {}).items():
            rows.append((iso3, int(years[int(t_idx)]), obs[0]))

    df = pd.DataFrame(rows, columns=["iso3", "year", "avg_wage"]).dropna()
    df["iso3"] = df["iso3"].astype(str).str.strip()
    df["year"] = df["year"].astype(int)
    df["avg_wage"] = pd.to_numeric(df["avg_wage"], errors="coerce")
    df = df.dropna(subset=["avg_wage"])

    return df.groupby(["iso3", "year"], as_index=False)["avg_wage"].mean()
