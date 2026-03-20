from flask import Blueprint, render_template, request, redirect, url_for
from .data_service import (
    get_semesters, get_rooms, get_instructors,
    get_classes_by_room, get_classes_by_instructor,
    build_weekly_grid, build_time_row_grid, DAY_ORDER, DAY_CODES,
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

    active_days = _active_days_from_time_grid(time_grid)

    return render_template(
        "room_timetable.html",
        room=room_name,
        semester=semester,
        semester_label=semester_label,
        time_slots=time_slots,
        time_grid=time_grid,
        active_days=active_days,
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
