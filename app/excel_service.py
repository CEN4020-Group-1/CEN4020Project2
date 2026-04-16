import os
import pandas as pd
from .data_service import DATA_FILE, normalize_dataframe

def import_excel(file):
    df = pd.read_excel(file)
    df = normalize_dataframe(df)

    try:
        existing = pd.read_csv(DATA_FILE)
        df = pd.concat([existing, df], ignore_index=True)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        pass

    if "CRN" in df.columns and "TERM" in df.columns:
        df = df.drop_duplicates(subset=["CRN", "TERM"], keep="last")

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    df.to_csv(DATA_FILE, index=False)
    return {"message": "Data imported", "rows": len(df)}
