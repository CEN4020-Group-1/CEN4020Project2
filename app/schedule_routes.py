from flask import Blueprint, render_template, request, redirect, url_for, jsonify, flash
from .data_service import (
    get_semesters, get_rooms, get_instructors,
    get_classes_by_room, get_classes_by_instructor,
    build_weekly_grid, build_time_row_grid, percentage_occupied,
    DAY_ORDER, DAY_CODES, TERM_LABELS,
    search_classes, get_departments, format_search_results,
    compare_schedules, get_comparison_details,
    load_schedule, parse_meeting_days, parse_meeting_time, _time_sort_key,
    generate_audit_report, get_class_by_crn,
    add_class, update_class, delete_class,
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
                if _is_same_class_instance(a, b):
                    # Duplicate rows for the same CRN should not conflict with themselves.
                    continue
                if _times_overlap(a["start_time"], a["end_time"], b["start_time"], b["end_time"]):
                    if _is_cross_listed_pair(a, b):
                        # Cross-listed UG/GR sections often share a meeting slot and should not be flagged.
                        continue
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


def _is_same_class_instance(class_a, class_b):
    """Return True when two entries represent the same scheduled class (e.g., duplicated row)."""
    crn_a = str(class_a.get("crn", "")).strip()
    crn_b = str(class_b.get("crn", "")).strip()
    return bool(crn_a) and crn_a == crn_b


def _is_cross_listed_pair(class_a, class_b):
    """Return True when two classes appear to be cross-listed UG/GR versions of the same class."""
    title_a = str(class_a.get("crse_title", "")).strip().lower()
    title_b = str(class_b.get("crse_title", "")).strip().lower()
    if not title_a or title_a != title_b:
        return False

    numb_a = _course_number_as_int(class_a.get("crse_numb", ""))
    numb_b = _course_number_as_int(class_b.get("crse_numb", ""))
    if numb_a is None or numb_b is None:
        return False

    # Treat 4xxx as undergraduate band and 5xxx+ as graduate band.
    return (numb_a <= 4999 < numb_b) or (numb_b <= 4999 < numb_a)


def _course_number_as_int(value):
    """Extract an integer course number from values like '4703' or '4703L'."""
    digits = "".join(ch for ch in str(value) if ch.isdigit())
    if not digits:
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _minutes_to_ampm(total_minutes):
    hour_24 = total_minutes // 60
    minute = total_minutes % 60
    period = "AM" if hour_24 < 12 else "PM"
    hour_12 = hour_24 % 12
    if hour_12 == 0:
        hour_12 = 12
    return f"{hour_12:02d}:{minute:02d} {period}"


def _compute_room_vacancies(classes_df, duration_minutes):
    """Compute available time slots for each day in a room schedule."""
    start_of_day = 8 * 60
    end_of_day = 20 * 60
    busy = {day: [] for day in DAY_ORDER}

    for _, row in classes_df.iterrows():
        days = parse_meeting_days(row.get("MEETING_DAYS", ""))
        start, end = parse_meeting_time(row.get("MEETING_TIMES", ""))
        if not days or not start or not end:
            continue

        start_m = _time_sort_key(start)
        end_m = _time_sort_key(end)
        if start_m >= end_m:
            continue

        for day in days:
            if day in busy:
                busy[day].append((start_m, end_m))

    vacancies = {day: [] for day in DAY_ORDER}
    for day in DAY_ORDER:
        intervals = sorted(busy[day])
        cursor = start_of_day

        for start_m, end_m in intervals:
            if start_m - cursor >= duration_minutes:
                vacancies[day].append((cursor, start_m))
            cursor = max(cursor, end_m)

        if end_of_day - cursor >= duration_minutes:
            vacancies[day].append((cursor, end_of_day))

    formatted = {}
    for day, slots in vacancies.items():
        formatted[day] = [
            f"{_minutes_to_ampm(a)} - {_minutes_to_ampm(b)}" for a, b in slots
        ]
    return formatted


@schedule_routes.route("/vacancy", methods=["GET"])
def vacancy_select():
    """Selection page for vacancy search."""
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    selected_room = request.args.get("room", "")
    duration = request.args.get("duration", "")
    rooms = get_rooms(semester) if semester else []
    error = request.args.get("error", "")
    return render_template(
        "VacancySelect.html",
        semesters=semesters,
        rooms=rooms,
        selected_semester=semester,
        selected_room=selected_room,
        duration=duration,
        error=error,
    )


@schedule_routes.route("/vacancy/results", methods=["GET"])
def vacancy_results():
    """Results page for vacancy search by semester, duration, and optional room."""
    semester = (request.args.get("semester", "") or "").strip()
    room = (request.args.get("room", "") or "").strip()
    duration_raw = (request.args.get("duration", "") or "").strip()

    if not semester or not duration_raw:
        return redirect(url_for("schedule.vacancy_select", error="Please select semester and duration."))

    try:
        duration = int(duration_raw)
    except ValueError:
        return redirect(url_for("schedule.vacancy_select", error="Duration must be a number of minutes."))

    if duration <= 0:
        return redirect(url_for("schedule.vacancy_select", error="Duration must be greater than zero."))

    schedule_df = load_schedule(semester)
    rooms = [room] if room else get_rooms(semester)
    vacancy_rows = []

    for room_name in rooms:
        room_df = schedule_df[schedule_df["MEETING_ROOM"] == room_name] if not schedule_df.empty else schedule_df
        day_slots = _compute_room_vacancies(room_df, duration)
        has_any = any(day_slots[d] for d in DAY_ORDER)
        vacancy_rows.append({"room": room_name, "slots": day_slots, "has_any": has_any})

    return render_template(
        "VacancyTable.html",
        semester=semester,
        room_filter=room,
        duration=duration,
        day_names=DAY_CODES,
        day_order=DAY_ORDER,
        vacancy_rows=vacancy_rows,
    )


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
# FEATURE 9: Schedule Audit Report
# ============================================================

@schedule_routes.route("/audit", methods=["GET"])
def audit_select():
    semesters = get_semesters()
    return render_template("audit_select.html", semesters=semesters)


@schedule_routes.route("/audit/results", methods=["GET"])
def audit_results():
    semester = request.args.get("semester", "").strip()
    if not semester:
        return redirect(url_for("schedule.audit_select"))

    semester_label = TERM_LABELS.get(semester, f"Term {semester}")
    issues = generate_audit_report(semester)

    total = sum(len(v) for v in issues.values())

    return render_template(
        "audit_report.html",
        semester=semester,
        semester_label=semester_label,
        issues=issues,
        total_issues=total,
    )


# ============================================================
# FEATURE 10: Detailed Class View
# ============================================================

@schedule_routes.route("/class/<crn>")
def class_detail(crn):
    semester = request.args.get("semester", "").strip()
    class_data, other_sections = get_class_by_crn(crn, semester or None)

    if class_data is None:
        return render_template("class_detail.html", class_data=None, crn=crn, semester=semester)

    semester_label = TERM_LABELS.get(str(class_data.get("TERM", "")), "")

    return render_template(
        "class_detail.html",
        class_data=class_data,
        other_sections=other_sections,
        crn=crn,
        semester=semester,
        semester_label=semester_label,
    )


# ============================================================
# MANDATORY STORY 1: Add / Edit / Delete Classes
# ============================================================

CLASS_FORM_FIELDS = [
    "TERM", "CRN", "SUBJ", "CRSE_NUMB", "CRSE_TITLE", "CRSE_SECTION",
    "CRSE_LEVL", "INSTRUCTOR", "INSTRUCTOR_EMAIL", "MEETING_DAYS",
    "MEETING_TIMES", "MEETING_ROOM", "CAMPUS", "ENROLLMENT",
    "GRAD_TAS", "GRAD_TA_HOURS", "UGTAS", "UGTA_HOURS",
]


def _collect_form_data():
    """Pull class fields from the submitted form."""
    data = {}
    for field in CLASS_FORM_FIELDS:
        if field == "MEETING_DAYS":
            days = request.form.getlist("day_checks")
            data[field] = "".join(days)
        elif field == "MEETING_TIMES":
            start = request.form.get("time_start", "").strip()
            end = request.form.get("time_end", "").strip()
            data[field] = f"{start} - {end}" if start and end else ""
        else:
            data[field] = request.form.get(field, "").strip()
    return data


@schedule_routes.route("/class/add", methods=["GET", "POST"])
def class_add():
    semesters = get_semesters()
    if request.method == "POST":
        data = _collect_form_data()
        row, err = add_class(data)
        if err:
            return render_template("class_form.html", mode="add", semesters=semesters,
                                   day_order=DAY_ORDER, day_names=DAY_CODES,
                                   form_data=data, error=err)
        crn = str(row.get("CRN", "")).replace(".0", "")
        term = str(row.get("TERM", "")).replace(".0", "")
        return redirect(url_for("schedule.class_detail", crn=crn, semester=term))

    return render_template("class_form.html", mode="add", semesters=semesters,
                           day_order=DAY_ORDER, day_names=DAY_CODES,
                           form_data={}, error=None)


@schedule_routes.route("/class/<crn>/edit", methods=["GET", "POST"])
def class_edit(crn):
    semester = request.args.get("semester", "").strip()
    semesters = get_semesters()

    if request.method == "POST":
        semester = request.form.get("semester_hidden", semester)
        data = _collect_form_data()
        _, err = update_class(crn, semester, data)
        if err:
            return render_template("class_form.html", mode="edit", semesters=semesters,
                                   day_order=DAY_ORDER, day_names=DAY_CODES,
                                   form_data=data, error=err, crn=crn, semester=semester)
        return redirect(url_for("schedule.class_detail", crn=crn, semester=semester))

    class_data, _ = get_class_by_crn(crn, semester or None)
    if class_data is None:
        return redirect(url_for("schedule.class_add"))

    form_data = {}
    for field in CLASS_FORM_FIELDS:
        val = class_data.get(field)
        form_data[field] = str(val) if val is not None else ""

    return render_template("class_form.html", mode="edit", semesters=semesters,
                           day_order=DAY_ORDER, day_names=DAY_CODES,
                           form_data=form_data, error=None, crn=crn, semester=semester)


@schedule_routes.route("/class/<crn>/delete", methods=["POST"])
def class_delete(crn):
    semester = request.form.get("semester", "").strip()
    success, err = delete_class(crn, semester)
    return redirect(url_for("schedule.search_classes_route"))
