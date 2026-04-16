import os
from flask import Blueprint, request, jsonify, render_template
from .excel_service import import_excel
from .export_service import export_schedule
from .data_service import get_semesters, get_departments, search_classes, DAY_CODES, TERM_LABELS


main_routes = Blueprint("main", __name__)

@main_routes.route("/")
def home():
    return render_template("home.html")

@main_routes.route("/upload", methods = ["POST"])
def upload():
    file = request.files["file"]
    result = import_excel(file)
    return jsonify(result)

@main_routes.route("/export/schedule/<format>")
def export(format):
    return export_schedule(format)

@main_routes.route("/search")
def search():
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    query = request.args.get("q", "").strip()
    subj = request.args.get("subj", "").strip()
    instructor = request.args.get("instructor", "").strip()

    departments = get_departments(semester if semester else None)
    results = []
    searched = bool(query or subj or instructor or semester)

    if searched:
        df = search_classes(
            semester=semester if semester else None,
            query=query if query else None,
            subj=subj if subj else None,
            instructor=instructor if instructor else None,
        )
        for _, row in df.iterrows():
            term = str(row.get("TERM", ""))
            results.append({
                "subj": row.get("SUBJ", ""),
                "crse_numb": row.get("CRSE_NUMB", ""),
                "crse_title": row.get("CRSE_TITLE", ""),
                "section": row.get("CRSE_SECTION", ""),
                "crn": row.get("CRN", ""),
                "instructor": row.get("INSTRUCTOR", ""),
                "room": row.get("MEETING_ROOM", ""),
                "days": row.get("MEETING_DAYS", ""),
                "times": row.get("MEETING_TIMES", ""),
                "semester": TERM_LABELS.get(term, term),
            })

    return render_template(
        "search.html",
        semesters=semesters,
        departments=departments,
        results=results,
        searched=searched,
        selected_semester=semester,
        selected_subj=subj,
        query=query,
        instructor=instructor,
    )