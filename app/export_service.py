import io
import pandas as pd
from flask import send_file
from .data_service import DATA_FILE

def export_schedule(format):
    df = pd.read_csv(DATA_FILE)

    if format == "csv":
        output = io.StringIO()
        df.to_csv(output, index=False)
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            as_attachment=True,
            download_name="schedule_export.csv",
            mimetype="text/csv",
        )

    if format == "excel":
        output = io.BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="schedule_export.xlsx",
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
