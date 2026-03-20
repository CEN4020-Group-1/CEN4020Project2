import pandas as pd
from flask import send_file
from .data_service import DATA_FILE

def export_schedule(format):
    df = pd.read_csv(DATA_FILE)

    if format == "csv":
        file = "schedule_export.csv"
        df.to_csv(file, index=False)
        return send_file(file, as_attachment=True)

    if format == "excel":
        file = "schedule_export.xlsx"
        df.to_excel(file, index=False)
        return send_file(file, as_attachment=True)
