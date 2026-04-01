# Use Cases — Bellini College Class Scheduling System

---

## Use Case 1: Upload Excel File

**Author**
Scheduling Committee Member

**Primary Actor**
Scheduling Committee Member

**Priority**
High *(suggested: High — this is the foundational step that enables all other features)*

**Status**
Approved

**Description**
This use case allows the scheduling committee member to upload Excel files containing class scheduling data into the Bellini scheduling system.

**Preconditions**
- The system is running.
- The user has access to the upload page.

**Postconditions**
- The uploaded file is stored in the system.
- Class data is imported into the scheduling database.

**Basic Flow**
1. The actor navigates to the upload page.
2. The actor selects an Excel file from their computer.
3. The actor submits the file.
4. The system uploads the file.
5. The system reads and imports the class data.
6. The system confirms that the upload was successful.

**Alternative Flow**

3a. If the selected file is not in the correct format:
→ The system displays an error message and asks the user to choose a different file.

---

## Use Case 2: Search and Filter Classes

**Author**
Scheduling Committee Member

**Primary Actor**
Scheduling Committee Member

**Priority**
High *(suggested: High — quickly locating specific classes is a core day-to-day need for the committee)*

**Status**
Approved

**Description**
This use case allows a scheduling committee member to search for specific classes in the Bellini scheduling system using one or more filter criteria, such as course code, instructor name, semester, or department.

**Preconditions**
- The system is running.
- At least one semester's schedule data has been imported into the system.
- The user has access to the search page.

**Postconditions**
- The system displays a list of classes matching the entered criteria.
- If no matches are found, the system notifies the user that no results were returned.

**Basic Flow**
1. The actor navigates to the Search & Filter Classes page.
2. The actor enters one or more search criteria — such as a course code, instructor name, semester, or department.
3. The actor clicks "Search."
4. The system retrieves all classes that match the provided criteria.
5. The system displays the results, showing details such as course title, section, instructor, room, meeting days and times, semester, and enrollment.

**Alternative Flow**

3a. If no criteria are entered before clicking "Search":
→ The system does not perform a search and prompts the user to enter at least one search value.

5a. If no classes match the entered criteria:
→ The system displays a message indicating that no results were found, and the actor may adjust their search and try again.

---

## Use Case 3: Compare Semester Schedules

**Author**
Scheduling Committee Member

**Primary Actor**
Scheduling Committee Member

**Priority**
Medium *(suggested: Medium — valuable for planning but not required for everyday scheduling tasks)*

**Status**
Approved

**Description**
This use case allows a scheduling committee member to compare course offerings and enrollment data between two different semesters, helping identify which courses were added, removed, or carried over.

**Preconditions**
- The system is running.
- Schedule data for at least two different semesters has been imported into the system.
- The user has access to the comparison page.

**Postconditions**
- The system displays a side-by-side summary of the two selected semesters, including statistics and categorized course lists.
- If the actor selects a specific course, the system displays detailed section-level information for that course in both semesters.

**Basic Flow**
1. The actor navigates to the Compare Schedules page.
2. The actor selects a first semester and a second semester from the available options.
3. The actor clicks "Compare Schedules."
4. The system generates a comparison showing:
   - Courses offered only in the first semester.
   - Courses offered only in the second semester.
   - Courses offered in both semesters.
   - Summary statistics for each semester, including total classes, unique courses, and total enrollment.
5. The system displays the comparison results.
6. *(Optional)* The actor clicks on a specific course to view a detailed breakdown, showing the number of sections, total enrollment, and individual section details for each semester, along with a short summary of what changed.

**Alternative Flow**

2a. If the actor selects the same semester for both fields:
→ The system alerts the user that two different semesters must be chosen, and the comparison is not submitted.

2b. If the actor does not select a semester for one or both fields:
→ The system alerts the user to complete both selections before proceeding.

4a. If one of the selected semesters has no data in the system:
→ The system treats it as having no courses. All courses from the other semester appear as exclusive to that semester, and the empty semester's statistics display as zero.
