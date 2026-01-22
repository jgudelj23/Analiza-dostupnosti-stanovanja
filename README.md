Pri pokretanju potrebno je aktivirati virtualno okruženje sa: .\.venv\Scripts\Activate.ps1 (ako nemate venv potrebno ga je instalirati prije)
Requirements.txt je tu da bi se instalirali svi potrebni paketi za run-anje programa (py -m pip install -r requirements.txt)
Potrebno je pokrenuti ETL (py -m scripts.run_etl) 
i na kraju pokrenuti API (uvicorn src.api:app --reload --port 8000) treba paziti da se nalazite u pravom direktoriju (307 Temporary Redirect jer se automatski redirecta na http://127.0.0.1:8000/docs
)
Može se kliknuti na link u terminalu kad se pokrene API ili ručno unijeti na preglednik za pokretanje Swagger UI: http://127.0.0.1:8000/docs


config.py
-centralno mjesto za konfiguraciju putanja i URL-ova (način prikupljanja + način pohrane)

eurostat.py
-učitava i čisti Eurostat HPI CSV
-uzima bitne stupce (geo, time_period, obs_value)
-pretvara u standardni oblik (država+godina+vrijednost)
-radi čišćenje i agregaciju (npr. ako ima duplikata)


oecd.py
-dohvaća i parsira OECD podatke preko REST API-a (JSON)
-HTTP poziv na OECD_URL koji odgovara linku za JSON 
-parsiranje SDMX-JSON strukture
-vraća tablicu s plaćama po državi i godini(npr.ISO3, year, avg_wage)

transform.py
-integracija Eurostat + OECD u jedan skup
-mapiranje ISO2 u ISO3 da se može spojiti
-merge (po ISO3, year)
-računa izvedene metrike wage_index i price_to_income_index koji kasnije koristim u notebooku za analizu pod imenom "affordability"

db.py
-pomoćne funkcije za bazu
-inicijalizacija engine-a
-helper za spajanje(provjeru tablica)

load.py
-zapis integriranog DataFrame-a u SQLite
-način pohrane integriranog skupa u bazu 

api.py
-spaja se na SQLite
-GET endpointi 
-DEMO logika na startup kopira integrated_metrics u integrated_metrics_demo pa CRUD radi nad tablicom
-FAST API jer jasno demonstrira izradu REST sučelja i intuitivno je


ENDPOINTI
GET / (Root)
Primjer: 
http://127.0.0.1:8000/
Rezultat: vraća JSON s porukom o API-u i linkom na dokumentaciju. Ovo služi kao “landing” endpoint da korisnik odmah vidi što je API i gdje su docs.

GET /countries
Primjer:
http://127.0.0.1:8000/countries
Rezultat: lista ISO3 kodova država (npr. ["AUT","HRV",...]). To je “distinct iso3” iz integrated_metrics_demo.


GET /metrics
Primjer 1 (samo država):
http://127.0.0.1:8000/metrics?iso3=HRV
Rezultat: svi redci za Hrvatsku iz DEMO tablice (po godinama), uključujući hpi, avg_wage, wage_index, price_to_income_index. Vraća više godina jer su podaci vremenska serija.

Primjer 2 (filtriranje po godinama):
http://127.0.0.1:8000/metrics?iso3=HRV&year_from=2018&year_to=2022
Rezultat: samo period 2018–2022. To je isto čitanje iz baze, ali s dodatnim WHERE year >= ... AND year <=

GET /summary
Primjer:
http://127.0.0.1:8000/summary
Rezultat: JSON sa sažetkom DEMO tablice (n_rows, n_countries, min_year, max_year). Ovo služi da pokaže “opseg” integriranog skupa.

GET /aggregate/by-year
Primjer:
http://127.0.0.1:8000/aggregate/by-year
Rezultat: lista godina gdje za svaku godinu se dobije prosjek (EU prosjek): avg_hpi, avg_wage, avg_price_to_income. To radi GROUP BY year nad svim državama, pa se dobije EU agregaciju.

GET /aggregate/rank
Primjer 1:
http://127.0.0.1:8000/aggregate/rank?year=2022&limit=10&order=desc
Rezultat: top 10 država s najvećim price_to_income_index za 2022

Primjer 2:
http://127.0.0.1:8000/aggregate/rank?year=2022&limit=10&order=asc
Rezultat: top 10 država s najmanjim indeksom 

GET /aggregate/country-vs-eu
Primjer 1:
http://127.0.0.1:8000/aggregate/country-vs-eu?iso3=HRV
Rezultat: po godinama se dobije paralelne vrijednosti za državu (c_hpi, c_wage, c_pti) i EU prosjek (eu_hpi, eu_wage, eu_pti). Ovo je “usporedba države s EU prosjekom” za sva tri indikatora.

Primjer 2:
http://127.0.0.1:8000/aggregate/country-vs-eu?iso3=DEU
Rezultat: isti format, ali za Njemačku, pa se može usporediti kako se država ponaša u odnosu na EU prosjek (npr. jesu li plaće iznad prosjeka, a affordability lošija itd.).

GET /compare/country-vs-eu
Primjer 1:
http://127.0.0.1:8000/compare/country-vs-eu?iso3=HRV
Rezultat: slično kao prethodni, ali dodatno vraća affordability_gap (razlika između države i EU prosjeka po godini). Pozitivan gap znači “gore od EU prosjeka” (ako je veći indeks = manje pristupačno), negativan znači “bolje od EU”.

Primjer 2:
http://127.0.0.1:8000/compare/country-vs-eu?iso3=AUT
Rezultat: isti output, pa se može direktno usporediti gap Hrvatske i Austrije kroz godine.

CRUD METODE
-rade na demo tablici