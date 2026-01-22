import pandas as pd

ISO2_TO_ISO3 = {
  "AT":"AUT","BE":"BEL","BG":"BGR","HR":"HRV","CY":"CYP","CZ":"CZE","DK":"DNK",
  "EE":"EST","FI":"FIN","FR":"FRA","DE":"DEU","GR":"GRC","HU":"HUN","IE":"IRL",
  "IT":"ITA","LV":"LVA","LT":"LTU","LU":"LUX","MT":"MLT","NL":"NLD","PL":"POL",
  "PT":"PRT","RO":"ROU","SK":"SVK","SI":"SVN","ES":"ESP","SE":"SWE"
}

def integrate(hpi, wages):
   
    hpi["iso3"] = hpi["iso2"].map(ISO2_TO_ISO3)
    hpi = hpi.dropna(subset=["iso3"])


    df = hpi.merge(wages, on=["iso3", "year"], how="inner")
    df = df.sort_values(["iso3", "year"])

 
    def add_index(g):
        base_year = 2015 if (g["year"] == 2015).any() else g["year"].min()
        base = g.loc[g["year"] == base_year, "avg_wage"].iloc[0]

        g["wage_index"] = (g["avg_wage"] / base) * 100
        g["price_to_income_index"] = (g["hpi"] / g["wage_index"]) * 100
        return g

    df = df.groupby("iso3", group_keys=False).apply(add_index).reset_index(drop=True)

    return df[["iso3", "year", "hpi", "avg_wage", "wage_index", "price_to_income_index"]]
