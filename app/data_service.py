import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "data", "schedule_database.csv")

COLUMN_MAP = {
    "CRSE LEVL": "CRSE_LEVL",
    "CRSE_LEVL": "CRSE_LEVL",
    "CRSE SECTION": "CRSE_SECTION",
    "CRSE_SECTION": "CRSE_SECTION",
    "CRSE NUMB": "CRSE_NUMB",
    "CRSE_NUMB": "CRSE_NUMB",
    "CRSE TITLE": "CRSE_TITLE",
    "CRSE_TITLE": "CRSE_TITLE",
    "MEETING DAYS": "MEETING_DAYS",
    "MEETING_DAYS": "MEETING_DAYS",
    "MEETING TIMES": "MEETING_TIMES",
    "MEETING TIMES1": "MEETING_TIMES",
    "MEETING_TIMES": "MEETING_TIMES",
    "MEETING ROOM": "MEETING_ROOM",
    "MEETING_ROOM": "MEETING_ROOM",
    "INSTRUCTOR EMAIL": "INSTRUCTOR_EMAIL",
    "INSTRUCTOR_EMAIL": "INSTRUCTOR_EMAIL",
    "Grad Hours": "GRAD_TA_HOURS",
    "TA Hours": "GRAD_TA_HOURS",
    "Graduate TA(s)": "GRAD_TAS",
    "Grad TAS": "GRAD_TAS",
    "Grad TAs": "GRAD_TAS",
    "Grad TA Emails": "GRAD_TA_EMAILS",
    "UG Hours": "UGTA_HOURS",
    "UGTA(s)": "UGTAS",
    "UGTAs": "UGTAS",
    "UGTA Emails": "UGTA_EMAILS",
}

EXCLUDED_ROOMS = {"OFFT OFF", "TBAT TBA", " ", ""}

TERM_LABELS = {
    "202501": "Spring 2025",
    "202508": "Fall 2025",
    "202601": "Spring 2026",
}

DAY_CODES = {
    "M": "Monday",
    "T": "Tuesday",
    "W": "Wednesday",
    "R": "Thursday",
    "F": "Friday",
    "S": "Saturday",
}

DAY_ORDER = ["M", "T", "W", "R", "F", "S"]

#rename columns to standard names and clean up data
def normalize_dataframe(df):
    df = df.rename(columns={c: COLUMN_MAP.get(c, c) for c in df.columns})

    if "TERM" in df.columns:
        df["TERM"] = df["TERM"].astype(str).str.replace(r"\.0$", "", regex=True)

    str_cols = ["MEETING_DAYS", "MEETING_TIMES", "MEETING_ROOM", "INSTRUCTOR"]
    for col in str_cols:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
            df[col] = df[col].replace({"nan": None, "": None})

    return df

#load the normalized schedule CSV, optionally filtered by semester
def load_schedule(semester=None):
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()

    df = pd.read_csv(DATA_FILE)
    if df.empty:
        return df

    if "TERM" in df.columns:
        df["TERM"] = df["TERM"].astype(str).str.replace(r"\.0$", "", regex=True)

    if semester:
        semester = str(semester).replace(".0", "")
        df = df[df["TERM"] == semester]

    return df

#return list of (term_code, label) tuples for all semesters in the data
def get_semesters():
    df = load_schedule()
    if df.empty:
        return []

    terms = sorted(df["TERM"].dropna().unique())
    return [(t, TERM_LABELS.get(t, f"Term {t}")) for t in terms]


#return sorted list of distinct rooms, excluding non-physical locations
def get_rooms(semester=None):
    df = load_schedule(semester)
    if df.empty:
        return []

    rooms = df["MEETING_ROOM"].dropna().unique()
    return sorted(r for r in rooms if r not in EXCLUDED_ROOMS)


#return sorted list of distinct instructor names
def get_instructors(semester=None):
    df = load_schedule(semester)
    if df.empty:
        return []

    instructors = df["INSTRUCTOR"].dropna().unique()
    return sorted(i for i in instructors if i)

    
#return all classes scheduled in a given room
def get_classes_by_room(room, semester=None):
    df = load_schedule(semester)
    if df.empty:
        return df
    return df[df["MEETING_ROOM"] == room]


#return all classes taught by a given instructor
def get_classes_by_instructor(instructor, semester=None):
    df = load_schedule(semester)
    if df.empty:
        return df
    return df[df["INSTRUCTOR"] == instructor]


#parse a meeting days string like 'MW' or 'TR' into a list of day codes
def parse_meeting_days(days_str):
    if not days_str or days_str == "nan":
        return []
    return [ch for ch in days_str if ch in DAY_CODES]

#parse a time string like '11:00 AM - 01:45 PM' into (start, end) strings
def parse_meeting_time(time_str):
    if not time_str or time_str == "nan":
        return None, None

    parts = time_str.split(" - ")
    if len(parts) != 2:
        return None, None

    return parts[0].strip(), parts[1].strip()

def build_weekly_grid(classes_df):
    """
    Build a weekly schedule grid from a DataFrame of classes.

    Returns a dict: {day_code: [list of class dicts sorted by start time]}
    Each class dict has: subj, crse_numb, crse_title, section, instructor,
                         room, start_time, end_time, time_display
    """
    grid = {day: [] for day in DAY_ORDER}

    for _, row in classes_df.iterrows():
        days = parse_meeting_days(row.get("MEETING_DAYS", ""))
        start_time, end_time = parse_meeting_time(row.get("MEETING_TIMES", ""))

        if not days or not start_time:
            continue

        entry = {
            "subj": row.get("SUBJ", ""),
            "crse_numb": row.get("CRSE_NUMB", ""),
            "crse_title": row.get("CRSE_TITLE", ""),
            "section": row.get("CRSE_SECTION", ""),
            "instructor": row.get("INSTRUCTOR", ""),
            "room": row.get("MEETING_ROOM", ""),
            "start_time": start_time,
            "end_time": end_time,
            "time_display": f"{start_time} - {end_time}",
            "crn": row.get("CRN", ""),
        }

        for day in days:
            if day in grid:
                grid[day].append(entry)

    for day in grid:
        grid[day].sort(key=lambda x: _time_sort_key(x["start_time"]))

    return grid

def build_time_row_grid(classes_df):
    """
    Build a 2D grid indexed by time slot (rows) and day (columns).

    Returns (time_slots, time_grid):
      - time_slots: sorted list of unique time_display strings
      - time_grid: {time_display: {day_code: [list of class dicts]}}
    """
    time_grid = {}

    for _, row in classes_df.iterrows():
        days = parse_meeting_days(row.get("MEETING_DAYS", ""))
        start_time, end_time = parse_meeting_time(row.get("MEETING_TIMES", ""))

        if not days or not start_time:
            continue

        time_display = f"{start_time} - {end_time}"

        entry = {
            "subj": row.get("SUBJ", ""),
            "crse_numb": row.get("CRSE_NUMB", ""),
            "crse_title": row.get("CRSE_TITLE", ""),
            "section": row.get("CRSE_SECTION", ""),
            "instructor": row.get("INSTRUCTOR", ""),
            "room": row.get("MEETING_ROOM", ""),
            "start_time": start_time,
            "end_time": end_time,
            "time_display": time_display,
            "crn": row.get("CRN", ""),
        }

        if time_display not in time_grid:
            time_grid[time_display] = {day: [] for day in DAY_ORDER}

        for day in days:
            if day in time_grid[time_display]:
                time_grid[time_display][day].append(entry)

    time_slots = sorted(time_grid.keys(), key=lambda t: _time_sort_key(t.split(" - ")[0]))

    return time_slots, time_grid

def percentage_occupied(time_grid, weekday = False):
    """
    Calculates the percentage of time that a room is occupied across a week

    Assuming classes can be held from 8 AM to 8 PM
    Also assuming that percentage utilization cares about days where no class uses them
    weekday as a bool will inidcate that the function should only count Monday - Thursday
    """
    max_time =  16 * 60
    max_time *= 4 if weekday else 6

    total_occupied = 0

    for period in time_grid:

        start_time = _time_sort_key(period.split(" - ")[0])
        end_time = _time_sort_key(period.split(" - ")[1])

        class_days = 0
        for day in time_grid[period]:
            if weekday and (day == "F" or day == "S"):
                continue
            if len(time_grid[period][day]) != 0:
                class_days += 1

        total_occupied += (end_time - start_time) * class_days

    percent = (total_occupied / max_time) * 100

    return "{:.2f}".format(round(percent, 2))

#convert '11:00 AM' to a sortable value (minutes since midnight)
def _time_sort_key(time_str):
    try:
        parts = time_str.split()
        hm = parts[0].split(":")
        hour = int(hm[0])
        minute = int(hm[1])
        period = parts[1].upper()

        if period == "PM" and hour != 12:
            hour += 12
        elif period == "AM" and hour == 12:
            hour = 0

        return hour * 60 + minute
    except (IndexError, ValueError):
        return 9999


# ============================================================
# FEATURE 2: Search and Filter Classes
# ============================================================

def search_classes(course_code=None, instructor=None, semester=None, department=None):
    """
    Search and filter classes by course code, instructor, semester, or department.
    
    Args:
        course_code: Partial or full course number (e.g., '4703' or 'COP4703')
        instructor: Instructor name (partial match)
        semester: Term code (e.g., '202501')
        department: Department/subject code (e.g., 'COP', 'ENG')
    
    Returns:
        DataFrame of matching classes
    """
    df = load_schedule(semester)
    if df.empty:
        return df
    
    # Filter by course code (SUBJ + CRSE_NUMB combination)
    if course_code:
        course_code_upper = str(course_code).upper()
        # Try to match as "SUBJ CRSE_NUMB" or just the number part
        course_code_parts = course_code_upper.split()
        if len(course_code_parts) >= 2:
            # Full format like "COP 4703"
            subj = course_code_parts[0]
            numb = course_code_parts[1] if len(course_code_parts) > 1 else ""
            mask = (df['SUBJ'].astype(str).str.upper() == subj) & (df['CRSE_NUMB'].astype(str) == numb)
        elif course_code_upper.isdigit():
            # Just the number
            mask = df['CRSE_NUMB'].astype(str) == course_code_upper
        else:
            # Check if it contains letters and numbers (like COP4703)
            letters = ''.join(c for c in course_code_upper if c.isalpha())
            numbers = ''.join(c for c in course_code_upper if c.isdigit())
            if letters and numbers:
                mask = (df['SUBJ'].astype(str).str.upper() == letters) & (df['CRSE_NUMB'].astype(str) == numbers)
            else:
                mask = df['CRSE_NUMB'].astype(str).str.contains(course_code_upper, case=False, na=False)
        df = df[mask]
    
    # Filter by instructor name
    if instructor:
        instructor_upper = str(instructor).upper()
        mask = df['INSTRUCTOR'].astype(str).str.contains(instructor_upper, case=False, na=False)
        df = df[mask]
    
    # Filter by department/subject
    if department:
        department_upper = str(department).upper()
        mask = df['SUBJ'].astype(str).str.upper() == department_upper
        df = df[mask]
    
    return df.reset_index(drop=True)


def get_departments():
    """Return a sorted list of unique department/subject codes."""
    df = load_schedule()
    if df.empty:
        return []
    
    departments = df['SUBJ'].dropna().unique()
    return sorted(d for d in departments if d)


def format_search_results(classes_df):
    """Format search results as a list of dictionaries with relevant class info."""
    results = []
    
    for _, row in classes_df.iterrows():
        result = {
            'crn': row.get('CRN', ''),
            'term': row.get('TERM', ''),
            'department': row.get('SUBJ', ''),
            'course_number': row.get('CRSE_NUMB', ''),
            'course_title': row.get('CRSE_TITLE', ''),
            'section': row.get('CRSE_SECTION', ''),
            'instructor': row.get('INSTRUCTOR', ''),
            'meeting_days': row.get('MEETING_DAYS', ''),
            'meeting_times': row.get('MEETING_TIMES', ''),
            'meeting_room': row.get('MEETING_ROOM', ''),
            'enrollment': row.get('ENROLLMENT', ''),
            'course_code': f"{row.get('SUBJ', '')} {row.get('CRSE_NUMB', '')}",
        }
        results.append(result)
    
    return results


# ============================================================
# FEATURE 6: Compare Schedules Across Semesters
# ============================================================

def compare_schedules(semester1, semester2):
    """
    Compare course offerings and enrollment between two semesters.
    
    Args:
        semester1: First term code (e.g., '202501')
        semester2: Second term code (e.g., '202508')
    
    Returns:
        Dictionary with comparison data
    """
    df1 = load_schedule(semester1)
    df2 = load_schedule(semester2)
    
    sem1_label = dict(get_semesters()).get(semester1, semester1)
    sem2_label = dict(get_semesters()).get(semester2, semester2)
    
    # Get unique courses in each semester
    courses1 = set((df1['SUBJ'].astype(str) + df1['CRSE_NUMB'].astype(str)).unique()) if not df1.empty else set()
    courses2 = set((df2['SUBJ'].astype(str) + df2['CRSE_NUMB'].astype(str)).unique()) if not df2.empty else set()
    
    # Categorize courses
    only_in_sem1 = courses1 - courses2
    only_in_sem2 = courses2 - courses1
    in_both = courses1 & courses2
    
    return {
        'semester1': semester1,
        'semester1_label': sem1_label,
        'semester2': semester2,
        'semester2_label': sem2_label,
        'df1': df1,
        'df2': df2,
        'only_in_sem1': sorted(only_in_sem1),
        'only_in_sem2': sorted(only_in_sem2),
        'in_both': sorted(in_both),
        'stats': {
            'total_classes_sem1': len(df1) if not df1.empty else 0,
            'total_classes_sem2': len(df2) if not df2.empty else 0,
            'total_courses_sem1': len(courses1),
            'total_courses_sem2': len(courses2),
            'enrollment_sem1': int(pd.to_numeric(df1['ENROLLMENT'], errors='coerce').sum()) if not df1.empty and 'ENROLLMENT' in df1.columns else 0,
            'enrollment_sem2': int(pd.to_numeric(df2['ENROLLMENT'], errors='coerce').sum()) if not df2.empty and 'ENROLLMENT' in df2.columns else 0,
        }
    }


# ============================================================
# FEATURE 5: Room & Time Slot Suggestions
# ============================================================

def get_available_rooms(semester, days, start_time, end_time):
    """
    Find rooms that are free during the specified days and time range.

    Args:
        semester: Term code (e.g., '202501')
        days: List of day codes (e.g., ['M', 'W'])
        start_time: Start time string (e.g., '10:00 AM')
        end_time: End time string (e.g., '11:15 AM')

    Returns:
        List of available room names sorted alphabetically
    """
    all_rooms = set(get_rooms(semester))
    if not all_rooms:
        return []

    df = load_schedule(semester)
    if df.empty:
        return sorted(all_rooms)

    requested_start = _time_sort_key(start_time)
    requested_end = _time_sort_key(end_time)

    occupied_rooms = set()
    for _, row in df.iterrows():
        room = row.get("MEETING_ROOM")
        if not room or room in EXCLUDED_ROOMS:
            continue

        meeting_days = parse_meeting_days(row.get("MEETING_DAYS", ""))
        row_start, row_end = parse_meeting_time(row.get("MEETING_TIMES", ""))

        if not row_start or not row_end:
            continue

        # Check if any requested day overlaps with the class days
        if not any(d in meeting_days for d in days):
            continue

        row_start_key = _time_sort_key(row_start)
        row_end_key = _time_sort_key(row_end)

        if requested_start < row_end_key and row_start_key < requested_end:
            occupied_rooms.add(room)

    return sorted(all_rooms - occupied_rooms)


# ============================================================
# FEATURE 7: Classroom Utilization Statistics
# ============================================================

def get_all_room_utilization(semester=None):
    """
    Compute utilization percentage for every room in a semester.

    Args:
        semester: Term code, or None for all semesters combined

    Returns:
        List of dicts sorted by full-week utilization descending:
            room, total_classes, full_week_pct, weekday_pct
    """
    rooms = get_rooms(semester)
    results = []

    for room in rooms:
        classes_df = get_classes_by_room(room, semester)
        _, time_grid = build_time_row_grid(classes_df)

        full_pct = float(percentage_occupied(time_grid))
        weekday_pct = float(percentage_occupied(time_grid, weekday=True))

        results.append({
            "room": room,
            "total_classes": len(classes_df),
            "full_week_pct": full_pct,
            "weekday_pct": weekday_pct,
        })

    results.sort(key=lambda x: x["full_week_pct"], reverse=True)
    return results


def get_comparison_details(semester1, semester2, course_code):
    """Get detailed comparison of a specific course across two semesters."""
    df1 = load_schedule(semester1)
    df2 = load_schedule(semester2)
    
    # Parse course code
    course_parts = course_code.upper().split()
    if len(course_parts) >= 2:
        subj, numb = course_parts[0], course_parts[1]
    else:
        letters = ''.join(c for c in course_code.upper() if c.isalpha())
        numbers = ''.join(c for c in course_code.upper() if c.isdigit())
        subj, numb = letters, numbers
    
    # Filter by course
    if not df1.empty:
        course1_df = df1[(df1['SUBJ'].astype(str).str.upper() == subj) & (df1['CRSE_NUMB'].astype(str) == numb)]
    else:
        course1_df = pd.DataFrame()
    
    if not df2.empty:
        course2_df = df2[(df2['SUBJ'].astype(str).str.upper() == subj) & (df2['CRSE_NUMB'].astype(str) == numb)]
    else:
        course2_df = pd.DataFrame()
    
    return {
        'course_code': course_code,
        'semester1_sections': format_search_results(course1_df),
        'semester2_sections': format_search_results(course2_df),
        'sem1_total_enrollment': int(pd.to_numeric(course1_df['ENROLLMENT'], errors='coerce').sum()) if not course1_df.empty and 'ENROLLMENT' in course1_df.columns else 0,
        'sem2_total_enrollment': int(pd.to_numeric(course2_df['ENROLLMENT'], errors='coerce').sum()) if not course2_df.empty and 'ENROLLMENT' in course2_df.columns else 0,
        'sem1_section_count': len(course1_df),
        'sem2_section_count': len(course2_df),
    }
