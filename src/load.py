def save_to_db(engine, df):
    df.to_sql("integrated_metrics", engine, if_exists="replace", index=False)
