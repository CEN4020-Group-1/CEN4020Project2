import os
from flask import Blueprint, render_template, render_template_string, send_file
import pandas as pd
from urllib.parse import unquote

file_routes = Blueprint("file_routes", __name__)

#UPLOAD_FOLDER = "uploads"
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


@file_routes.route("/files")
def list_files():
    files = os.listdir(UPLOAD_FOLDER)
    return render_template("files.html", files=files)

@file_routes.route("/view/<filename>")
def view_excel(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(filepath):
        return f"File {filename} not found!", 404
    
    df = pd.read_excel(filepath)
    table_html = df.to_html(classes = "table table-striped")
    
    return render_template_string("""
            <h2>{{ filename }}</h2>
            {{ table|safe }}
            <a href="/files">Back to files list</a>
        """, filename=filename, table=table_html)
    
@file_routes.route("/export/<filename>")
def export_excel(filename):
    import io
    import pandas as pd

    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        return f"File {filename} not found!", 404

    df = pd.read_excel(filepath)

    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"{filename}",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
@file_routes.route("/download/<filename>")
def download_excel(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return f"File {filename} not found!", 404

    return send_file(filepath, as_attachment=True)