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
    max_time =  12 * 60
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
