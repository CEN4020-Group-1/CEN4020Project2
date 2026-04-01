"""
Tests for the Bellini College Class Scheduling System.

Covers all 8 implemented features:
  1. Excel File Upload & Import
  2. Search & Filter Classes
  3. Room Weekly Timetable
  4. Instructor Weekly Schedule
  5. Room & Time Slot Suggestions  (new)
  6. Semester Comparison
  7. Classroom Utilization Statistics  (new)
  8. Schedule Export (CSV / Excel)
"""

import os
import io
import sys
import pytest

# Make sure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import create_app
from app.data_service import (
    load_schedule,
    get_semesters,
    get_rooms,
    get_instructors,
    get_classes_by_room,
    get_classes_by_instructor,
    build_weekly_grid,
    build_time_row_grid,
    percentage_occupied,
    search_classes,
    get_departments,
    format_search_results,
    compare_schedules,
    get_comparison_details,
    get_available_rooms,
    get_all_room_utilization,
    _time_sort_key,
    parse_meeting_days,
    parse_meeting_time,
    normalize_dataframe,
    DAY_ORDER,
    DAY_CODES,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create a Flask test client."""
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Helper / data-service unit tests
# ---------------------------------------------------------------------------

class TestHelpers:
    def test_time_sort_key_am(self):
        assert _time_sort_key("08:00 AM") == 8 * 60

    def test_time_sort_key_pm(self):
        assert _time_sort_key("01:30 PM") == 13 * 60 + 30

    def test_time_sort_key_noon(self):
        assert _time_sort_key("12:00 PM") == 12 * 60

    def test_time_sort_key_midnight_am(self):
        assert _time_sort_key("12:00 AM") == 0

    def test_time_sort_key_invalid(self):
        assert _time_sort_key("") == 9999

    def test_parse_meeting_days(self):
        assert parse_meeting_days("MWF") == ["M", "W", "F"]
        assert parse_meeting_days("TR") == ["T", "R"]
        assert parse_meeting_days("") == []
        assert parse_meeting_days(None) == []

    def test_parse_meeting_time(self):
        start, end = parse_meeting_time("09:30 AM - 10:45 AM")
        assert start == "09:30 AM"
        assert end == "10:45 AM"

    def test_parse_meeting_time_invalid(self):
        start, end = parse_meeting_time(None)
        assert start is None and end is None


# ---------------------------------------------------------------------------
# Data service integration tests (require data/schedule_database.csv)
# ---------------------------------------------------------------------------

class TestDataService:
    def test_load_schedule_returns_dataframe(self):
        df = load_schedule()
        assert not df.empty, "schedule_database.csv should not be empty"

    def test_get_semesters_returns_list(self):
        sems = get_semesters()
        assert isinstance(sems, list)
        assert len(sems) >= 1

    def test_get_rooms_not_empty(self):
        rooms = get_rooms()
        assert len(rooms) > 0

    def test_get_instructors_not_empty(self):
        instructors = get_instructors()
        assert len(instructors) > 0

    def test_get_departments_not_empty(self):
        depts = get_departments()
        assert len(depts) > 0

    def test_get_classes_by_room(self):
        rooms = get_rooms()
        if rooms:
            df = get_classes_by_room(rooms[0])
            assert "MEETING_ROOM" in df.columns

    def test_get_classes_by_instructor(self):
        instructors = get_instructors()
        if instructors:
            df = get_classes_by_instructor(instructors[0])
            assert "INSTRUCTOR" in df.columns

    def test_build_weekly_grid(self):
        df = load_schedule()
        if not df.empty:
            grid = build_weekly_grid(df.head(20))
            assert isinstance(grid, dict)
            for day in DAY_ORDER:
                assert day in grid

    def test_build_time_row_grid(self):
        df = load_schedule()
        if not df.empty:
            slots, grid = build_time_row_grid(df.head(20))
            assert isinstance(slots, list)
            assert isinstance(grid, dict)

    def test_percentage_occupied(self):
        df = load_schedule()
        if not df.empty:
            _, time_grid = build_time_row_grid(df.head(20))
            pct = percentage_occupied(time_grid)
            assert float(pct) >= 0

    def test_normalize_dataframe(self):
        import pandas as pd
        raw = pd.DataFrame({
            "MEETING DAYS": ["MWF"],
            "MEETING TIMES1": ["09:00 AM - 09:50 AM"],
            "TERM": ["202501.0"],
        })
        result = normalize_dataframe(raw)
        assert "MEETING_DAYS" in result.columns
        assert "MEETING_TIMES" in result.columns
        assert result["TERM"].iloc[0] == "202501"


# ---------------------------------------------------------------------------
# Feature 2: Search & Filter
# ---------------------------------------------------------------------------

class TestSearchAndFilter:
    def test_search_by_department(self):
        depts = get_departments()
        if depts:
            results = search_classes(department=depts[0])
            assert len(results) > 0

    def test_search_by_semester(self):
        sems = get_semesters()
        if sems:
            results = search_classes(semester=sems[0][0])
            assert len(results) > 0

    def test_search_no_results(self):
        results = search_classes(course_code="ZZZNONE9999")
        assert len(results) == 0

    def test_format_search_results(self):
        df = load_schedule()
        if not df.empty:
            formatted = format_search_results(df.head(5))
            assert len(formatted) == 5
            assert "course_code" in formatted[0]


# ---------------------------------------------------------------------------
# Feature 5: Room & Time Slot Suggestions
# ---------------------------------------------------------------------------

class TestRoomSuggestions:
    def test_get_available_rooms_returns_list(self):
        sems = get_semesters()
        if not sems:
            pytest.skip("No semester data available")
        semester = sems[0][0]
        rooms = get_available_rooms(semester, ["M", "W"], "08:00 AM", "09:00 AM")
        assert isinstance(rooms, list)

    def test_available_rooms_are_sorted(self):
        sems = get_semesters()
        if not sems:
            pytest.skip("No semester data available")
        semester = sems[0][0]
        rooms = get_available_rooms(semester, ["M"], "02:00 AM", "03:00 AM")
        assert rooms == sorted(rooms)

    def test_no_available_rooms_at_impossible_time(self):
        # Very early morning – virtually no classes should be scheduled
        sems = get_semesters()
        if not sems:
            pytest.skip("No semester data available")
        semester = sems[0][0]
        # This should succeed without error even if the list is empty
        rooms = get_available_rooms(semester, ["M", "T", "W", "R", "F"], "12:00 AM", "01:00 AM")
        assert isinstance(rooms, list)


# ---------------------------------------------------------------------------
# Feature 6: Semester Comparison
# ---------------------------------------------------------------------------

class TestSemesterComparison:
    def test_compare_schedules(self):
        sems = get_semesters()
        if len(sems) < 2:
            pytest.skip("Need at least two semesters to compare")
        data = compare_schedules(sems[0][0], sems[1][0])
        assert "only_in_sem1" in data
        assert "only_in_sem2" in data
        assert "in_both" in data
        assert "stats" in data

    def test_compare_stats_non_negative(self):
        sems = get_semesters()
        if len(sems) < 2:
            pytest.skip("Need at least two semesters to compare")
        data = compare_schedules(sems[0][0], sems[1][0])
        stats = data["stats"]
        assert stats["total_classes_sem1"] >= 0
        assert stats["total_classes_sem2"] >= 0


# ---------------------------------------------------------------------------
# Feature 7: Classroom Utilization Statistics
# ---------------------------------------------------------------------------

class TestUtilizationStats:
    def test_get_all_room_utilization_returns_list(self):
        stats = get_all_room_utilization()
        assert isinstance(stats, list)

    def test_utilization_has_required_keys(self):
        stats = get_all_room_utilization()
        if stats:
            row = stats[0]
            assert "room" in row
            assert "total_classes" in row
            assert "full_week_pct" in row
            assert "weekday_pct" in row

    def test_utilization_sorted_descending(self):
        stats = get_all_room_utilization()
        if len(stats) >= 2:
            pcts = [r["full_week_pct"] for r in stats]
            assert pcts == sorted(pcts, reverse=True)

    def test_utilization_by_semester(self):
        sems = get_semesters()
        if not sems:
            pytest.skip("No semester data available")
        stats = get_all_room_utilization(sems[0][0])
        assert isinstance(stats, list)


# ---------------------------------------------------------------------------
# Flask route smoke tests (HTTP responses)
# ---------------------------------------------------------------------------

class TestRoutes:
    """Smoke-test every route to confirm it returns a 200 (or redirect 302)."""

    def test_home(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_files_list(self, client):
        r = client.get("/files")
        assert r.status_code == 200

    # Feature 3: Room timetable
    def test_room_select(self, client):
        r = client.get("/schedule/room")
        assert r.status_code == 200

    def test_room_timetable(self, client):
        sems = get_semesters()
        rooms = get_rooms(sems[0][0]) if sems else []
        if not rooms:
            pytest.skip("No room data available")
        url = f"/schedule/room/{rooms[0]}?semester={sems[0][0]}"
        r = client.get(url)
        assert r.status_code == 200

    # Feature 4: Instructor schedule
    def test_instructor_select(self, client):
        r = client.get("/schedule/instructor")
        assert r.status_code == 200

    def test_instructor_schedule(self, client):
        sems = get_semesters()
        instructors = get_instructors(sems[0][0]) if sems else []
        if not instructors:
            pytest.skip("No instructor data available")
        from urllib.parse import quote
        url = f"/schedule/instructor/{quote(instructors[0])}?semester={sems[0][0]}"
        r = client.get(url)
        assert r.status_code == 200

    # Feature 2: Search
    def test_search_get(self, client):
        r = client.get("/schedule/search")
        assert r.status_code == 200

    def test_search_post(self, client):
        depts = get_departments()
        data = {"department": depts[0] if depts else ""}
        r = client.post("/schedule/search", data=data)
        assert r.status_code == 200

    # Feature 5: Suggestions
    def test_suggestions_get(self, client):
        r = client.get("/schedule/suggestions")
        assert r.status_code == 200

    def test_suggestions_post(self, client):
        sems = get_semesters()
        if not sems:
            pytest.skip("No semester data available")
        data = {
            "semester": sems[0][0],
            "days": ["M", "W"],
            "start_time": "09:00 AM",
            "end_time": "10:00 AM",
        }
        r = client.post("/schedule/suggestions", data=data)
        assert r.status_code == 200
        assert b"Available Rooms" in r.data

    # Feature 6: Comparison
    def test_comparison_select(self, client):
        r = client.get("/schedule/comparison")
        assert r.status_code == 200

    def test_comparison_view(self, client):
        sems = get_semesters()
        if len(sems) < 2:
            pytest.skip("Need at least two semesters")
        url = f"/schedule/comparison/{sems[0][0]}/{sems[1][0]}"
        r = client.get(url)
        assert r.status_code == 200

    # Feature 7: Utilization
    def test_utilization_all(self, client):
        r = client.get("/schedule/utilization")
        assert r.status_code == 200

    def test_utilization_by_semester(self, client):
        sems = get_semesters()
        if not sems:
            pytest.skip("No semester data available")
        r = client.get(f"/schedule/utilization?semester={sems[0][0]}")
        assert r.status_code == 200

    # Feature 8: Export
    def test_export_csv(self, client):
        r = client.get("/export/schedule/csv")
        assert r.status_code == 200
        assert b"," in r.data  # CSV has commas

    def test_export_excel(self, client):
        r = client.get("/export/schedule/excel")
        assert r.status_code == 200
