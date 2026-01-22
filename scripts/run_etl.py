from src.config import EUROSTAT_CSV_PATH, OECD_URL, DB_URL
from src.eurostat import load_eurostat_hpi
from src.oecd import fetch_oecd_wages
from src.transform import integrate
from src.db import get_engine, init_db
from src.load import save_to_db

def main():
    hpi = load_eurostat_hpi(EUROSTAT_CSV_PATH)
    wages = fetch_oecd_wages(OECD_URL)

    integrated = integrate(hpi, wages)

    engine = get_engine(DB_URL)
    init_db(engine)
    save_to_db(engine, integrated)

    print("ETL uspješno završen")
    print(integrated.head())

if __name__ == "__main__":
    main()
