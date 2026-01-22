from sqlalchemy import create_engine, text

def get_engine(db_url):
    return create_engine(db_url)

def init_db(engine):
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS integrated_metrics (
            iso3 TEXT,
            year INTEGER,
            hpi REAL,
            avg_wage REAL,
            wage_index REAL,    
            price_to_income_index REAL,
            PRIMARY KEY (iso3, year)
        )
        """))
