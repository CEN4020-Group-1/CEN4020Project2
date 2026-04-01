from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from .data_service import (
    get_semesters, get_rooms, get_instructors,
    get_classes_by_room, get_classes_by_instructor,
    build_weekly_grid, build_time_row_grid, percentage_occupied,
    DAY_ORDER, DAY_CODES,
    search_classes, get_departments, format_search_results,
    compare_schedules, get_comparison_details,
    get_available_rooms, get_all_room_utilization,
)

schedule_routes = Blueprint("schedule", __name__, url_prefix="/schedule")


@schedule_routes.route("/room", methods=["GET"])
def room_select():
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    rooms = get_rooms(semester) if semester else []
    return render_template("room_select.html", semesters=semesters, rooms=rooms, selected_semester=semester)


@schedule_routes.route("/room/<path:room_name>")
def room_timetable(room_name):
    semester = request.args.get("semester", "")
    if not semester:
        return redirect(url_for("schedule.room_select"))

    semesters = get_semesters()
    semester_label = dict(semesters).get(semester, semester)

    classes_df = get_classes_by_room(room_name, semester)
    time_slots, time_grid = build_time_row_grid(classes_df)

    percent_occupied = percentage_occupied(time_grid)
    weekday_percent = percentage_occupied(time_grid, weekday = True)

    active_days = _active_days_from_time_grid(time_grid)

    return render_template(
        "room_timetable.html",
        room=room_name,
        semester=semester,
        semester_label=semester_label,
        time_slots=time_slots,
        time_grid=time_grid,
        active_days=active_days,
        percent_occupied=percent_occupied,
        weekday_percent=weekday_percent,
        day_names=DAY_CODES,
        total_classes=len(classes_df),
    )


@schedule_routes.route("/instructor", methods=["GET"])
def instructor_select():
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    instructors = get_instructors(semester) if semester else []
    return render_template("instructor_select.html", semesters=semesters, instructors=instructors, selected_semester=semester)


@schedule_routes.route("/instructor/<path:instructor_name>")
def instructor_schedule(instructor_name):
    semester = request.args.get("semester", "")
    if not semester:
        return redirect(url_for("schedule.instructor_select"))

    semesters = get_semesters()
    semester_label = dict(semesters).get(semester, semester)

    classes_df = get_classes_by_instructor(instructor_name, semester)
    grid = build_weekly_grid(classes_df)
    time_slots, time_grid = build_time_row_grid(classes_df)

    active_days = _active_days_from_time_grid(time_grid)
    conflicts = _detect_time_conflicts(grid)

    return render_template(
        "instructor_schedule.html",
        instructor=instructor_name,
        semester=semester,
        semester_label=semester_label,
        time_slots=time_slots,
        time_grid=time_grid,
        active_days=active_days,
        day_names=DAY_CODES,
        total_classes=len(classes_df),
        conflicts=conflicts,
    )


def _active_days_from_time_grid(time_grid):
    """Determine which days have at least one class across all time slots."""
    active = set()
    for slot_days in time_grid.values():
        for day, classes in slot_days.items():
            if classes:
                active.add(day)
    return [d for d in DAY_ORDER if d in active]


def _detect_time_conflicts(grid):
    """Find overlapping classes on the same day for an instructor."""
    conflicts = []
    for day, classes in grid.items():
        for i in range(len(classes)):
            for j in range(i + 1, len(classes)):
                a = classes[i]
                b = classes[j]
                if _times_overlap(a["start_time"], a["end_time"], b["start_time"], b["end_time"]):
                    conflicts.append({
                        "day": day,
                        "class_a": f"{a['subj']} {a['crse_numb']} ({a['time_display']})",
                        "class_b": f"{b['subj']} {b['crse_numb']} ({b['time_display']})",
                    })
    return conflicts


def _times_overlap(start_a, end_a, start_b, end_b):
    """Check if two time ranges overlap."""
    from .data_service import _time_sort_key
    a_start = _time_sort_key(start_a)
    a_end = _time_sort_key(end_a)
    b_start = _time_sort_key(start_b)
    b_end = _time_sort_key(end_b)
    return a_start < b_end and b_start < a_end


# ============================================================
# FEATURE 2: Search and Filter Classes
# ============================================================

@schedule_routes.route("/search", methods=["GET", "POST"])
def search_classes_route():
    """Search and filter classes by course code, instructor, semester, or department."""
    semesters = get_semesters()
    departments = get_departments()
    results = []
    search_params = {}
    
    if request.method == "POST" or (request.method == "GET" and any(request.args.get(p) for p in ['course_code', 'instructor', 'semester', 'department'])):
        # Get search parameters
        course_code = request.args.get('course_code') or request.form.get('course_code', '').strip()
        instructor = request.args.get('instructor') or request.form.get('instructor', '').strip()
        semester = request.args.get('semester') or request.form.get('semester', '').strip()
        department = request.args.get('department') or request.form.get('department', '').strip()
        
        search_params = {
            'course_code': course_code,
            'instructor': instructor,
            'semester': semester,
            'department': department
        }
        
        # Perform search if any parameter is provided
        if any(search_params.values()):
            classes_df = search_classes(
                course_code=course_code or None,
                instructor=instructor or None,
                semester=semester or None,
                department=department or None
            )
            results = format_search_results(classes_df)
    
    return render_template(
        "search.html",
        semesters=semesters,
        departments=departments,
        results=results,
        search_params=search_params,
        total_results=len(results)
    )


# ============================================================
# FEATURE 6: Compare Schedules Across Semesters
# ============================================================

@schedule_routes.route("/comparison", methods=["GET", "POST"])
def comparison_select():
    """Select two semesters to compare."""
    semesters = get_semesters()
    
    if request.method == "POST" or (request.method == "GET" and request.args.get('semester1') and request.args.get('semester2')):
        semester1 = request.args.get('semester1') or request.form.get('semester1', '').strip()
        semester2 = request.args.get('semester2') or request.form.get('semester2', '').strip()
        
        if semester1 and semester2 and semester1 != semester2:
            return redirect(url_for("schedule.comparison_view", semester1=semester1, semester2=semester2))
    
    return render_template("comparison_select.html", semesters=semesters)


@schedule_routes.route("/comparison/<semester1>/<semester2>")
def comparison_view(semester1, semester2):
    """View comparison of course offerings between two semesters."""
    semesters = get_semesters()
    
    # Validate semesters exist
    semester_codes = [s[0] for s in semesters]
    if semester1 not in semester_codes or semester2 not in semester_codes:
        return redirect(url_for("schedule.comparison_select"))
    
    comparison_data = compare_schedules(semester1, semester2)
    
    # Calculate statistics
    stats = comparison_data['stats']
    stats['only_in_1'] = len(comparison_data['only_in_sem1'])
    stats['only_in_2'] = len(comparison_data['only_in_sem2'])
    stats['in_both'] = len(comparison_data['in_both'])
    
    return render_template(
        "comparison.html",
        semesters=semesters,
        semester1=semester1,
        semester2=semester2,
        semester1_label=comparison_data['semester1_label'],
        semester2_label=comparison_data['semester2_label'],
        only_in_sem1=comparison_data['only_in_sem1'],
        only_in_sem2=comparison_data['only_in_sem2'],
        in_both=comparison_data['in_both'],
        stats=stats
    )


@schedule_routes.route("/comparison/details/<semester1>/<semester2>/<course_code>")
def comparison_details(semester1, semester2, course_code):
    """View detailed comparison of a specific course across two semesters."""
    semesters = get_semesters()
    
    details = get_comparison_details(semester1, semester2, course_code)
    
    return render_template(
        "comparison_details.html",
        semesters=semesters,
        semester1=semester1,
        semester2=semester2,
        semester1_label=dict(semesters).get(semester1, semester1),
        semester2_label=dict(semesters).get(semester2, semester2),
        course_code=course_code,
        semester1_sections=details['semester1_sections'],
        semester2_sections=details['semester2_sections'],
        sem1_total_enrollment=details['sem1_total_enrollment'],
        sem2_total_enrollment=details['sem2_total_enrollment'],
        sem1_section_count=details['sem1_section_count'],
        sem2_section_count=details['sem2_section_count']
    )


# ============================================================
# FEATURE 5: Room & Time Slot Suggestions
# ============================================================

# Common time slots used in college scheduling
COMMON_TIME_SLOTS = [
    ("08:00 AM", "08:50 AM"),
    ("08:00 AM", "09:15 AM"),
    ("09:00 AM", "09:50 AM"),
    ("09:30 AM", "10:45 AM"),
    ("10:00 AM", "10:50 AM"),
    ("11:00 AM", "11:50 AM"),
    ("11:00 AM", "12:15 PM"),
    ("12:00 PM", "12:50 PM"),
    ("12:30 PM", "01:45 PM"),
    ("01:00 PM", "01:50 PM"),
    ("02:00 PM", "02:50 PM"),
    ("02:00 PM", "03:15 PM"),
    ("03:00 PM", "03:50 PM"),
    ("03:30 PM", "04:45 PM"),
    ("04:00 PM", "04:50 PM"),
    ("05:00 PM", "05:50 PM"),
    ("05:00 PM", "06:15 PM"),
    ("06:00 PM", "07:15 PM"),
    ("06:30 PM", "07:45 PM"),
    ("07:00 PM", "08:00 PM"),
]


@schedule_routes.route("/suggestions", methods=["GET", "POST"])
def room_suggestions():
    """Suggest available rooms for a given semester, days, and time range."""
    semesters = get_semesters()
    available_rooms = []
    search_params = {}
    searched = False

    if request.method == "POST":
        semester = request.form.get("semester", "").strip()
        days = request.form.getlist("days")
        start_time = request.form.get("start_time", "").strip()
        end_time = request.form.get("end_time", "").strip()

        search_params = {
            "semester": semester,
            "days": days,
            "start_time": start_time,
            "end_time": end_time,
        }

        if semester and days and start_time and end_time:
            available_rooms = get_available_rooms(semester, days, start_time, end_time)
            searched = True

    return render_template(
        "suggestions.html",
        semesters=semesters,
        day_codes=DAY_CODES,
        day_order=DAY_ORDER,
        time_slots=COMMON_TIME_SLOTS,
        available_rooms=available_rooms,
        search_params=search_params,
        searched=searched,
    )


# ============================================================
# FEATURE 7: Classroom Utilization Statistics
# ============================================================

@schedule_routes.route("/utilization")
def utilization_stats():
    """Display classroom utilization statistics for a selected semester."""
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    semester_label = dict(semesters).get(semester, "All Semesters") if semester else "All Semesters"

    stats = get_all_room_utilization(semester if semester else None)

    return render_template(
        "utilization.html",
        semesters=semesters,
        selected_semester=semester,
        semester_label=semester_label,
        stats=stats,
    )
