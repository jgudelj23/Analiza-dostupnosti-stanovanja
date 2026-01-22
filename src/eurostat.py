import pandas as pd

def load_eurostat_hpi(csv_path: str) -> pd.DataFrame:

    df = pd.read_csv(csv_path)
    df.columns = [c.strip().lower() for c in df.columns]

    required = {"geo", "time_period", "obs_value"}
    if not required.issubset(df.columns):
        raise ValueError(f"Eurostat CSV nema očekivane stupce {required}. Ima: {df.columns.tolist()}")

    out = df.rename(columns={
        "geo": "iso2",
        "time_period": "year",
        "obs_value": "hpi"
    })[["iso2", "year", "hpi"]].copy()

    out["iso2"] = out["iso2"].astype(str).str.strip()

    out["year"] = pd.to_numeric(out["year"], errors="coerce")
    out["hpi"] = pd.to_numeric(out["hpi"], errors="coerce")

    out = out.dropna(subset=["iso2", "year", "hpi"])
    out["year"] = out["year"].astype(int)


    out = out.groupby(["iso2", "year"], as_index=False)["hpi"].mean()


    return out
