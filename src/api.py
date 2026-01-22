from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
from typing import Optional
from fastapi.responses import RedirectResponse
from sqlalchemy import create_engine, text

from src.config import DB_URL

engine = create_engine(DB_URL, future=True)

app = FastAPI(
    title="EU Housing Affordability API",
    version="0.1.0",
    description="Integrirani podaci (Eurostat HPI + OECD wages). DEMO tablica se resetira pri svakom pokretanju servera."
)



@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.on_event("startup")
def reset_demo_table():
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS integrated_metrics_demo;"))
        conn.execute(text("""
            CREATE TABLE integrated_metrics_demo AS
            SELECT * FROM integrated_metrics;
        """))


@app.get("/")
def root():
    return {
        "message": "EU Housing Affordability API (DEMO mode)",
        "docs": "/docs",
        "note": "DEMO tablica se resetira na startup (kopira se iz integrated_metrics)."
    }

@app.get("/countries", summary="lista država (ISO3) iz DEMO tablice")
def countries():
    with engine.begin() as conn:
        rows = conn.execute(
            text("SELECT DISTINCT iso3 FROM integrated_metrics_demo ORDER BY iso3")
        ).all()
    return [r[0] for r in rows]

@app.get("/metrics", summary="dohvat metrika po državi i godinama")
def metrics(
    iso3: str = Query(..., min_length=3, max_length=3, description="ISO3 kod države (npr. HRV)"),
    year_from: Optional[int] = Query(None, description="Početna godina"),
    year_to: Optional[int] = Query(None, description="Završna godina"),
    limit: int = Query(5000, ge=1, le=50000)
):
    iso3 = iso3.upper()

    q = "SELECT * FROM integrated_metrics_demo WHERE iso3 = :iso3"
    params = {"iso3": iso3, "limit": limit}

    if year_from is not None:
        q += " AND year >= :yf"
        params["yf"] = year_from
    if year_to is not None:
        q += " AND year <= :yt"
        params["yt"] = year_to

    q += " ORDER BY year LIMIT :limit"

    with engine.begin() as conn:
        rows = conn.execute(text(q), params).mappings().all()

    return list(rows)

@app.get("/summary", summary="sažetak DEMO tablice")
def summary():
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
              COUNT(*) AS n_rows,
              COUNT(DISTINCT iso3) AS n_countries,
              MIN(year) AS min_year,
              MAX(year) AS max_year
            FROM integrated_metrics_demo
        """)).mappings().one()
    return dict(row)

@app.get("/aggregate/by-year", summary="EU prosjeki po godini (HPI, avg_wage, affordability)")
def aggregate_by_year():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
              year,
              AVG(hpi) AS avg_hpi,
              AVG(avg_wage) AS avg_wage,
              AVG(price_to_income_index) AS avg_price_to_income
            FROM integrated_metrics_demo
            GROUP BY year
            ORDER BY year
        """)).mappings().all()
    return list(rows)

@app.get("/aggregate/rank", summary="rang država po dostupnosti za godinu")
def rank(year: int, limit: int = 10, order: str = "desc"):
    order_sql = "DESC" if order.lower() == "desc" else "ASC"

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
              iso3,
              year,
              hpi,
              avg_wage,
              price_to_income_index
            FROM integrated_metrics_demo
            WHERE year = :year
            ORDER BY price_to_income_index {order_sql}
            LIMIT :limit
        """), {"year": year, "limit": limit}).mappings().all()

    return list(rows)

@app.get("/aggregate/country-vs-eu", summary="usporedba države i EU prosjeka po godini")
def country_vs_eu(iso3: str):
    iso3 = iso3.upper()
    with engine.begin() as conn:
        rows = conn.execute(text("""
            WITH eu AS (
                SELECT year,
                       AVG(hpi) AS eu_hpi,
                       AVG(avg_wage) AS eu_wage,
                       AVG(price_to_income_index) AS eu_pti
                FROM integrated_metrics_demo
                GROUP BY year
            ),
            c AS (
                SELECT year,
                       hpi AS c_hpi,
                       avg_wage AS c_wage,
                       price_to_income_index AS c_pti
                FROM integrated_metrics_demo
                WHERE iso3 = :iso3
            )
            SELECT
              c.year,
              c.c_hpi, eu.eu_hpi,
              c.c_wage, eu.eu_wage,
              c.c_pti, eu.eu_pti
            FROM c
            JOIN eu ON eu.year = c.year
            ORDER BY c.year
        """), {"iso3": iso3}).mappings().all()
    return list(rows)


@app.get(
    "/compare/country-vs-eu",
    summary="usporedba države i EU prosjeka po godinama (HPI, plaće, affordability)"
)
def compare_country_vs_eu(
    iso3: str = Query(..., min_length=3, max_length=3, description="ISO3 kod države (npr. HRV)")
):
    iso3 = iso3.upper()

    with engine.begin() as conn:
        rows = conn.execute(text("""
            WITH eu AS (
                SELECT
                  year,
                  AVG(hpi) AS eu_avg_hpi,
                  AVG(avg_wage) AS eu_avg_wage,
                  AVG(price_to_income_index) AS eu_avg_affordability
                FROM integrated_metrics_demo
                GROUP BY year
            ),
            c AS (
                SELECT
                  year,
                  hpi AS c_hpi,
                  avg_wage AS c_wage,
                  price_to_income_index AS c_affordability
                FROM integrated_metrics_demo
                WHERE iso3 = :iso3
            )
            SELECT
              c.year,
              c.c_hpi, eu.eu_avg_hpi,
              c.c_wage, eu.eu_avg_wage,
              c.c_affordability, eu.eu_avg_affordability,
              (c.c_affordability - eu.eu_avg_affordability) AS affordability_gap
            FROM c
            JOIN eu ON eu.year = c.year
            ORDER BY c.year
        """), {"iso3": iso3}).mappings().all()

    return list(rows)

class MetricCreate(BaseModel):
    iso3: str
    year: int
    hpi: float
    avg_wage: float
    wage_index: float
    price_to_income_index: float

class MetricUpdate(BaseModel):
    hpi: Optional[float] = None
    avg_wage: Optional[float] = None
    wage_index: Optional[float] = None
    price_to_income_index: Optional[float] = None

@app.post("/demo/metrics", summary="dodaj novi red (POST)")
def create_demo_metric(m: MetricCreate):
    iso3 = m.iso3.upper()

    with engine.begin() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM integrated_metrics_demo WHERE iso3=:iso3 AND year=:year LIMIT 1"),
            {"iso3": iso3, "year": m.year}
        ).first()
        if exists:
            raise HTTPException(status_code=409, detail="Row already exists for iso3+year.")

        conn.execute(text("""
            INSERT INTO integrated_metrics_demo
            (iso3, year, hpi, avg_wage, wage_index, price_to_income_index)
            VALUES (:iso3, :year, :hpi, :avg_wage, :wage_index, :price_to_income_index)
        """), {
            "iso3": iso3,
            "year": m.year,
            "hpi": m.hpi,
            "avg_wage": m.avg_wage,
            "wage_index": m.wage_index,
            "price_to_income_index": m.price_to_income_index
        })

    return {"status": "created", "iso3": iso3, "year": m.year}

@app.put("/demo/metrics/{iso3}/{year}", summary="izmijeni postojeći red")
def update_demo_metric(iso3: str, year: int, patch: MetricUpdate):
    iso3 = iso3.upper()
    data = patch.model_dump(exclude_none=True)

    if not data:
        return {"status": "no_changes"}

    set_clause = ", ".join([f"{k} = :{k}" for k in data.keys()])

    with engine.begin() as conn:
        res = conn.execute(text(f"""
            UPDATE integrated_metrics_demo
            SET {set_clause}
            WHERE iso3 = :iso3 AND year = :year
        """), {"iso3": iso3, "year": year, **data})

    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Row not found in DEMO table for given iso3+year.")

    return {"status": "updated", "iso3": iso3, "year": year, "changes": data}

@app.delete("/demo/metrics/{iso3}/{year}", summary="obriši red")
def delete_demo_metric(iso3: str, year: int):
    iso3 = iso3.upper()

    with engine.begin() as conn:
        res = conn.execute(
            text("DELETE FROM integrated_metrics_demo WHERE iso3=:iso3 AND year=:year"),
            {"iso3": iso3, "year": year}
        )

    if res.rowcount == 0:
        raise HTTPException(status_code=404, detail="Row not found in DEMO table for given iso3+year.")

    return {"status": "deleted", "iso3": iso3, "year": year}
