# CEN4020 Project 2
# Bellini College Class Scheduling System

A web-based scheduling system for the Bellini College class scheduling committee. The system consumes class data from Excel spreadsheets across multiple semesters and provides tools to view, manage, and audit the college's class schedule.

## Features

### Implemented User Stories

1. **Excel File Upload & Import** — Upload Excel files and automatically import class data into the system, populating the scheduling database without manual data entry.

2. **Search & Filter** — Search and filter classes by course code, instructor, semester, or department to quickly locate specific classes. *(Planned)*

3. **Room Weekly Timetable** — View the weekly timetable of a specific classroom in a time-slot grid layout, showing room utilization and available time slots at a glance.

4. **Instructor Weekly Schedule** — View the weekly teaching schedule of an instructor with automatic conflict detection, highlighting overlapping class times.

5. **Room & Time Slot Suggestions** — Suggest available rooms and time slots when scheduling a new class. *(Planned)*

6. **Semester Comparison** — Compare schedules across different semesters to analyze course offerings. *(Planned)*

7. **Classroom Utilization Statistics** — Visualize classroom utilization statistics such as percentage of time rooms are occupied. *(Planned)*

8. **Schedule Export** — Export the finalized class schedule to downloadable Excel or CSV format.

### Data

The system processes three Excel files containing Bellini College class schedules:

- `Bellini Classes S25.xlsx` — Spring 2025 (118 classes)
- `Bellini Classes F25.xlsx` — Fall 2025 (153 classes)
- `Bellini Classes S26.xlsx` — Spring 2026 (147 classes)

A data normalization layer handles inconsistent column naming across the files (e.g., `MEETING_DAYS` vs `MEETING DAYS`, `MEETING TIMES1` vs `MEETING TIMES`) and standardizes them into a unified schema.

## Tech Stack

- **Backend**: Python 3, Flask
- **Data Processing**: pandas, openpyxl
- **Database**: Normalized CSV (`data/schedule_database.csv`)
- **Frontend**: HTML, CSS (server-side rendered via Jinja2 templates)

## Project Structure

```
CEN4020Project2/
├── main.py                          # Flask app entry point
├── app/
│   ├── __init__.py                  # App factory, blueprint registration
│   ├── routes.py                    # Home page, upload, schedule export
│   ├── file_routes.py               # File listing, viewing, downloading
│   ├── schedule_routes.py           # Room timetable & instructor schedule views
│   ├── data_service.py              # Data normalization, queries, grid building
│   ├── excel_service.py             # Excel import with normalization & dedup
│   └── export_service.py            # Schedule export (CSV/Excel)
├── templates/
│   ├── home.html                    # Landing page with navigation
│   ├── files.html                   # Uploaded file listing
│   ├── room_select.html             # Semester + room selection form
│   ├── room_timetable.html          # Room weekly timetable grid
│   ├── instructor_select.html       # Semester + instructor selection form
│   └── instructor_schedule.html     # Instructor weekly schedule grid
├── data/
│   └── schedule_database.csv        # Normalized schedule database
├── uploads/                         # Pre-loaded Excel source files
│   ├── Bellini Classes S25.xlsx
│   ├── Bellini Classes F25.xlsx
│   └── Bellini Classes S26.xlsx
└── .gitignore
```

## Setup & Installation

### Prerequisites

- Python 3.9 or higher

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run the Application

```bash
python3 main.py
```

The server starts at **http://127.0.0.1:5001**.

### Populating the Database

The schedule database (`data/schedule_database.csv`) comes pre-populated with all three semester files. To reimport, use the upload feature on the home page or run:

```bash
python3 -c "
from app.data_service import normalize_dataframe, DATA_FILE
import pandas as pd, os

files = ['uploads/Bellini Classes S25.xlsx', 'uploads/Bellini Classes F25.xlsx', 'uploads/Bellini Classes S26.xlsx']
dfs = [normalize_dataframe(pd.read_excel(f)) for f in files]
combined = pd.concat(dfs, ignore_index=True).drop_duplicates(subset=['CRN', 'TERM'], keep='last')
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
combined.to_csv(DATA_FILE, index=False)
print(f'Imported {len(combined)} classes')
"
```

## Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Home page |
| POST | `/upload` | Upload and import an Excel file |
| GET | `/files` | List uploaded Excel files |
| GET | `/view/<filename>` | View an Excel file as an HTML table |
| GET | `/download/<filename>` | Download an uploaded file |
| GET | `/export/<filename>` | Export a specific Excel file |
| GET | `/export/schedule/<format>` | Export schedule database (csv or excel) |
| GET | `/schedule/room` | Room timetable selection page |
| GET | `/schedule/room/<room_name>?semester=<term>` | Room weekly timetable |
| GET | `/schedule/instructor` | Instructor schedule selection page |
| GET | `/schedule/instructor/<name>?semester=<term>` | Instructor weekly schedule |

## Contributors

- **Seyoung Kan** — Stories 1 & 8 (File upload/import, schedule export)
- **Anthony Saade** — Stories 3 & 4 (Room timetable, instructor schedule)
- **Haruto Venkatesan** — Stories 2 & 6 (Search/filter, semester comparison)
- **Jose Wong** — Stories 5 & 7 (Room suggestions, utilization stats)
