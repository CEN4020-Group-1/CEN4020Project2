from flask import Blueprint, render_template, request, redirect, url_for
from .data_service import (
    get_semesters, get_rooms, get_instructors,
    get_classes_by_room, get_classes_by_instructor,
    build_weekly_grid, build_time_row_grid, percentage_occupied,
    get_open_slots, compare_semesters, get_room_utilization,
    DAY_ORDER, DAY_CODES,
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

@schedule_routes.route("/suggest")
def room_suggest():
    #While I do think this function needs to be its own separate page, I'm not sure if the reused parts are okay.
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    rooms = get_rooms(semester) if semester else []
    return render_template("suggest_filter.html", semesters=semesters, rooms=rooms, selected_semester=semester)


@schedule_routes.route("/suggest/open", methods=["GET"])
def suggest_open_times():
    semester = request.args.get("semester", "")
    room = request.args.get("room", "")
    start_time = request.args.get("start", "")
    end_time = request.args.get("end", "")

    if not semester or not room:
        return redirect(url_for("schedule.room_suggest"))

    semesters = get_semesters()
    semester_label = dict(semesters).get(semester, semester)

    occupied, open_by_day = get_open_slots(
        room, semester,
        start_filter=start_time if start_time else None,
        end_filter=end_time if end_time else None,
    )

    active_days = [d for d in DAY_ORDER if any(d in booked for booked in occupied.values()) or open_by_day[d]]

    return render_template(
        "suggest_open.html",
        room=room,
        semester=semester,
        semester_label=semester_label,
        start_time=start_time,
        end_time=end_time,
        occupied=occupied,
        open_by_day=open_by_day,
        active_days=active_days,
        day_names=DAY_CODES,
        all_slots=sorted(occupied.keys()),
    )


@schedule_routes.route("/compare", methods=["GET"])
def semester_compare():
    semesters = get_semesters()
    sem1 = request.args.get("sem1", "")
    sem2 = request.args.get("sem2", "")

    only_in_sem1, in_both, only_in_sem2 = [], [], []
    compared = False
    sem1_label = sem2_label = ""

    if sem1 and sem2 and sem1 != sem2:
        sem_map = dict(semesters)
        sem1_label = sem_map.get(sem1, sem1)
        sem2_label = sem_map.get(sem2, sem2)
        only_in_sem1, in_both, only_in_sem2 = compare_semesters(sem1, sem2)
        compared = True

    return render_template(
        "compare.html",
        semesters=semesters,
        sem1=sem1,
        sem2=sem2,
        sem1_label=sem1_label,
        sem2_label=sem2_label,
        only_in_sem1=only_in_sem1,
        in_both=in_both,
        only_in_sem2=only_in_sem2,
        compared=compared,
    )


@schedule_routes.route("/utilization", methods=["GET"])
def utilization():
    semesters = get_semesters()
    semester = request.args.get("semester", "")
    semester_label = dict(semesters).get(semester, semester) if semester else ""

    stats = get_room_utilization(semester) if semester else []

    return render_template(
        "utilization.html",
        semesters=semesters,
        selected_semester=semester,
        semester_label=semester_label,
        stats=stats,
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
